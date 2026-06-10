"""Pipeline orchestrator for complete AI trading pipeline."""
import logging
import asyncio
import pandas as pd
from datetime import date
from typing import Optional, Dict, List

from collectors import KISClient
from collectors.dart_client import DARTAPIClient
from analysis import StockFilter, QuantitativeAnalyzer, SentimentAnalyzer, TimeSeriesAnalyzer
from ai import TradingDecisionGenerator
from filters import SafetyFilter
from execution import TradeExecutor
from database import DatabaseRepository
from config.constants import KOSPI_100

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Orchestrates Stage 1 pipeline execution.

    Workflow:
    1. Fetch KOSPI 100 stock data from KIS API
    2. Calculate weighted scores using StandardScaler
    3. Select top 30 stocks (+ holdings)
    4. Save results to database
    """

    def __init__(self, api_server_url: str = "http://api-server:8080"):
        # Stage 1: Filtering
        self.kis_client = KISClient()  # Single shared instance for OAuth token caching
        self.stock_filter = StockFilter()

        # Stage 2: Analysis - pass kis_client to share OAuth token cache
        self.dart_client = DARTAPIClient()  # DART API client for financial data
        self.quant_analyzer = QuantitativeAnalyzer(kis_client=self.kis_client)
        self.sentiment_analyzer = SentimentAnalyzer()
        self.ts_analyzer = TimeSeriesAnalyzer(kis_client=self.kis_client)

        # Stage 4: AI Decision
        self.decision_generator = TradingDecisionGenerator()

        # Stage 5: Safety Filter
        self.safety_filter = SafetyFilter()

        # Stage 6: Trade Execution
        self.trade_executor = TradeExecutor(api_base_url=api_server_url)

        # Database
        self.db_repo = DatabaseRepository()

        logger.info("PipelineOrchestrator initialized with full pipeline")

    async def run_stage1_filtering(
        self,
        trade_date: Optional[date] = None,
        holdings: Optional[List[str]] = None
    ) -> Dict:
        """
        Execute Stage 1: Stock filtering pipeline.

        Args:
            trade_date: Trade date (defaults to today)
            holdings: Optional list of holdings to always include

        Returns:
            Dict with execution results:
                - success: bool
                - trade_date: date
                - total_stocks: int
                - selected_stocks: int
                - selected_codes: List[str]
                - error: Optional error message
        """
        if trade_date is None:
            trade_date = date.today()

        logger.info(f"Starting Stage 1 filtering for {trade_date}")

        try:
            # Step 0: Check if market is open (avoid unnecessary API calls on holidays)
            logger.info("⏳ Checking market status...")
            is_open = await self.kis_client.is_market_open(trade_date=trade_date)

            if not is_open:
                logger.warning(f"⚠️ Market is closed on {trade_date} (holiday or non-trading day)")
                return {
                    'success': False,
                    'trade_date': trade_date.isoformat(),
                    'error': '오늘은 휴장일입니다',
                    'is_holiday': True
                }

            # Step 0-1: Fetch holdings from KIS API (to always include in final 30)
            logger.info("Fetching holdings from KIS API...")
            api_holdings = await self.kis_client.get_holdings()

            # Merge with parameter holdings (if provided)
            if holdings and api_holdings:
                holdings = list(set(holdings + api_holdings))  # Remove duplicates
            elif api_holdings:
                holdings = api_holdings
            # If neither exists, holdings remains None

            if holdings:
                logger.info(f"Found {len(holdings)} holdings to always include: {holdings}")
            else:
                logger.info("No holdings found, will use only Top 30 filtered stocks")

            # Step 1: Fetch KOSPI 100 data from KIS API
            logger.info(f"Fetching data for {len(KOSPI_100)} KOSPI 100 stocks")
            stock_data_df = await self.kis_client.fetch_stock_data_parallel(KOSPI_100)

            if stock_data_df.empty:
                error_msg = "Failed to fetch stock data from KIS API"
                logger.error(error_msg)
                return {
                    'success': False,
                    'trade_date': trade_date.isoformat(),
                    'error': error_msg
                }

            logger.info(f"Fetched data for {len(stock_data_df)} stocks")

            # Step 2: Calculate scores and filter top 30
            logger.info("Calculating scores and filtering top 30 stocks")
            filtered_df = self.stock_filter.process(stock_data_df, holdings=holdings)

            # Step 3: Save results to database
            logger.info("Saving results to database")
            save_success = self.db_repo.save_filter_scores(filtered_df, trade_date)

            if not save_success:
                error_msg = "Failed to save results to database"
                logger.error(error_msg)
                return {
                    'success': False,
                    'trade_date': trade_date.isoformat(),
                    'error': error_msg
                }

            # Step 4: Save market summary (KOSPI index + market statistics)
            logger.info("Fetching and saving market summary data")
            try:
                # Get KOSPI index data (pass trade_date in YYYYMMDD format)
                kospi_data = await self.kis_client.get_kospi_index(trade_date.strftime('%Y%m%d'))

                # Calculate market statistics from stock_data_df
                market_summary = {
                    'kospi_index': kospi_data.get('kospi_index'),  # Fixed: was 'index'
                    'kospi_change_rate': kospi_data.get('kospi_change_rate'),  # Fixed: was 'change_rate'
                    'kospi_volume': kospi_data.get('kospi_volume'),  # Fixed: was 'volume'
                    'total_stocks': len(stock_data_df),
                    'rising_stocks': len(stock_data_df[stock_data_df['price_change_rate'] > 0]) if 'price_change_rate' in stock_data_df.columns else None,
                    'falling_stocks': len(stock_data_df[stock_data_df['price_change_rate'] < 0]) if 'price_change_rate' in stock_data_df.columns else None,
                    'unchanged_stocks': len(stock_data_df[stock_data_df['price_change_rate'] == 0]) if 'price_change_rate' in stock_data_df.columns else None,
                    'total_foreign_net_buy': int(stock_data_df['foreign_net_buy'].sum()) if 'foreign_net_buy' in stock_data_df.columns else None,
                    'total_institutional_net_buy': int(stock_data_df['institution_net_buy'].sum()) if 'institution_net_buy' in stock_data_df.columns else None,
                    'market_sentiment_score': None  # Will be updated in Stage 2-2
                }

                market_save_success = self.db_repo.save_market_summary(market_summary, trade_date)
                if not market_save_success:
                    logger.warning("Failed to save market summary (non-critical)")
                else:
                    logger.info(f"Market summary saved: KOSPI={market_summary['kospi_index']:.2f}")
            except Exception as e:
                logger.warning(f"Failed to save market summary: {e} (non-critical)")

            # Extract selected stocks
            selected_df = filtered_df[filtered_df['is_selected'] == True]
            selected_codes = selected_df['stock_code'].tolist()

            logger.info(f"Stage 1 filtering completed successfully: {len(selected_codes)} stocks selected")

            return {
                'success': True,
                'trade_date': trade_date.isoformat(),
                'total_stocks': len(filtered_df),
                'selected_stocks': len(selected_codes),
                'selected_codes': selected_codes,
                'stock_data_df': stock_data_df,  # Pass full Stage 1 data for reuse in Stage 2
                'score_stats': {
                    'min': float(filtered_df['final_score'].min()),
                    'max': float(filtered_df['final_score'].max()),
                    'mean': float(filtered_df['final_score'].mean())
                }
            }

        except Exception as e:
            error_msg = f"Pipeline execution failed: {str(e)}"
            logger.exception(error_msg)
            return {
                'success': False,
                'trade_date': trade_date.isoformat(),
                'error': error_msg
            }

    def run_stage1_sync(
        self,
        trade_date: Optional[date] = None,
        holdings: Optional[List[str]] = None
    ) -> Dict:
        """
        Synchronous wrapper for run_stage1_filtering (for scheduler).

        Args:
            trade_date: Trade date (defaults to today)
            holdings: Optional list of holdings to always include

        Returns:
            Dict with execution results
        """
        return asyncio.run(self.run_stage1_filtering(trade_date, holdings))

    async def run_complete_pipeline(
        self,
        trade_date: Optional[date] = None,
        holdings: Optional[List[str]] = None,
        conn=None
    ) -> Dict:
        """
        Execute complete AI trading pipeline (Stages 1-6).

        Workflow:
        1. Stock Filtering (KOSPI 100 → Top 30)
        2. 3-Way Analysis (Quantitative, Sentiment, Time-Series)
        3. Chart Generation (skipped for now, add later)
        4. Gemini AI Decision (TOP3 buy/sell)
        5. Safety Filter (Feature-based validation)
        6. Trade Execution (KIS API via Spring Boot)

        Args:
            trade_date: Trade date (defaults to today)
            holdings: Optional list of holdings to always include
            conn: Database connection for saving results

        Returns:
            Dict with complete execution results
        """
        if trade_date is None:
            trade_date = date.today()

        logger.info(f"=== Starting Complete Pipeline for {trade_date} ===")

        pipeline_result = {
            'success': False,
            'trade_date': trade_date.isoformat(),
            'stages': {}
        }

        try:
            # Stage 1: Filtering
            logger.info("[Stage 1] Stock Filtering")
            stage1_result = await self.run_stage1_filtering(trade_date, holdings)

            if not stage1_result['success']:
                pipeline_result['stages']['stage1_filtering'] = stage1_result
                pipeline_result['error'] = "Stage 1 filtering failed"
                return pipeline_result

            # Extract DataFrame for Stage 2 (internal use only, not in API response)
            selected_codes = stage1_result['selected_codes']
            stock_data_df = stage1_result.pop('stock_data_df')  # Remove from dict before adding to response

            # Now add stage1_result to response (without DataFrame)
            pipeline_result['stages']['stage1_filtering'] = stage1_result
            logger.info(f"[Stage 1] Selected {len(selected_codes)} stocks")

            # Stage 2: 3-Way Analysis
            logger.info("[Stage 2] 3-Way Analysis")

            # Stage 2-1: Quantitative Analysis (with Stage 1 data reuse)
            logger.info("[Stage 2-1] Quantitative Analysis")

            # Step 1: Collect DART financial data for selected stocks
            logger.info("[Stage 2-1-A] DART financial data collection")
            dart_base_date = self._calculate_latest_dart_quarter(trade_date)
            logger.info(f"Using DART base_date: {dart_base_date}")

            dart_financials_df = self.dart_client.collect_financials_for_stocks(
                stock_codes=selected_codes,
                base_date=dart_base_date
            )

            # Save DART data to stock_financial table
            if not dart_financials_df.empty:
                dart_save_success = self.dart_client.save_to_database(dart_financials_df)
                logger.info(f"[Stage 2-1-A] Saved {len(dart_financials_df)} DART financial records")
            else:
                logger.warning("[Stage 2-1-A] No DART data collected")

            # Step 2: Collect KIS quantitative features (reuse Stage 1 data)
            logger.info("[Stage 2-1-B] KIS quantitative features")
            selected_stage1_data = stock_data_df[stock_data_df['stock_code'].isin(selected_codes)]
            quant_df = await self.quant_analyzer.analyze_stocks(selected_codes, trade_date, stage1_data=selected_stage1_data)

            # Save quantitative features to database (iterate through each stock)
            logger.info("[Stage 2-1-B] Saving quantitative features to database")
            quant_saved_count = 0
            for _, row in quant_df.iterrows():
                if self.db_repo.save_quantitative_features(
                    stock_code=row['stock_code'],
                    trade_date=trade_date,
                    morning_return=row['morning_return'],
                    close_position=row['close_position']
                ):
                    quant_saved_count += 1
            logger.info(f"[Stage 2-1-B] Saved {quant_saved_count} quantitative records")

            logger.info(f"[Stage 2-1] Quantitative analysis complete: {len(quant_df)} stocks")

            # Stage 2-2: Sentiment Analysis
            logger.info("[Stage 2-2] Sentiment Analysis")
            sentiment_df = await self.sentiment_analyzer.analyze_stocks(selected_codes)
            logger.info(f"[Stage 2-2] Sentiment analysis complete: {len(sentiment_df)} stocks")

            # Save sentiment results to database
            logger.info("Saving sentiment analysis results to database")
            sentiment_saved_count = 0
            for _, row in sentiment_df.iterrows():
                if self.db_repo.save_sentiment_analysis(
                    stock_code=row['stock_code'],
                    analysis_date=trade_date,
                    sentiment_score=row['sentiment_score'],
                    news_count=0  # News collection returns 0 articles currently
                ):
                    sentiment_saved_count += 1
            logger.info(f"Saved {sentiment_saved_count} sentiment records to news_analysis table")

            # Stage 2-3: Time-Series Analysis
            logger.info("[Stage 2-3] Time-Series Analysis")
            ts_df = await self.ts_analyzer.analyze_stocks(selected_codes)
            logger.info(f"[Stage 2-3] Time-series analysis complete: {len(ts_df)} stocks")

            # Save time-series results to database
            logger.info("Saving time-series forecast results to database")
            ts_saved_count = 0
            for _, row in ts_df.iterrows():
                forecast_data = row.to_dict()
                if self.db_repo.save_prophet_forecast_detailed(forecast_data, trade_date):
                    ts_saved_count += 1
            logger.info(f"Saved {ts_saved_count} time-series records to prophet_forecast table")

            # Merge all features (for logging purposes)
            features_df = quant_df.merge(sentiment_df, on='stock_code', how='left')
            features_df = features_df.merge(ts_df, on='stock_code', how='left')

            logger.info(f"[Stage 2] Analysis complete: {len(features_df)} stocks with {len(features_df.columns)-1} features")
            pipeline_result['stages']['stage2_analysis'] = {
                'features_count': len(features_df.columns) - 1,  # Exclude stock_code
                'stocks_count': len(features_df)
            }

            # Stage 4: Gemini AI Decision
            logger.info("[Stage 4] Gemini AI Decision")
            gemini_decisions = self.decision_generator.generate_decisions(
                quant_features=quant_df,
                sentiment_features=sentiment_df,
                timeseries_features=ts_df
            )

            # Save to DB
            self.db_repo.save_ai_decisions(gemini_decisions, trade_date)

            logger.info(f"[Stage 4] Gemini decisions: {len(gemini_decisions.get('buy_top3', []))} buys, {len(gemini_decisions.get('sell_top3', []))} sells")
            pipeline_result['stages']['stage4_gemini'] = gemini_decisions

            # Stage 5: Safety Filter
            logger.info("[Stage 5] Safety Filter")

            # Fetch order_amount from user_trade_config (user_id=1 for MVP)
            order_amount = self.db_repo.get_user_order_amount(user_id=1)
            logger.info(f"[Stage 5] User order amount: {order_amount:,}원")

            # Fetch current stock prices for buy candidates
            buy_stock_codes = [item['stock_code'] for item in gemini_decisions.get('buy_top3', [])]
            stock_prices = {}
            if buy_stock_codes:
                for stock_code in buy_stock_codes:
                    price_data = await self.kis_client.get_current_price(stock_code)
                    stock_prices[stock_code] = price_data['current_price']
                logger.info(f"[Stage 5] Fetched prices for {len(stock_prices)} buy candidates")

            # Apply safety filter with investment limit check
            filtered_decisions = self.safety_filter.filter_decisions(
                gemini_decisions,
                features_df,
                stock_prices=stock_prices,
                order_amount=order_amount
            )

            # Save filter results to DB
            self.db_repo.save_safety_filter_results(filtered_decisions['filter_results'], trade_date)

            buy_passed = len(filtered_decisions['buy_top3'])
            sell_passed = len(filtered_decisions['sell_top3'])
            logger.info(f"[Stage 5] Safety filter passed: {buy_passed} buys, {sell_passed} sells")
            pipeline_result['stages']['stage5_safety_filter'] = {
                'buy_passed': buy_passed,
                'sell_passed': sell_passed,
                'filter_results': filtered_decisions['filter_results']
            }

            # Stage 6: Trade Execution
            logger.info("[Stage 6] Trade Execution")
            execution_results = await self.trade_executor.execute_trades(filtered_decisions)

            logger.info(f"[Stage 6] Execution status: {execution_results['status']}")
            pipeline_result['stages']['stage6_execution'] = execution_results

            # Final success
            pipeline_result['success'] = True
            logger.info("=== Complete Pipeline Finished Successfully ===")

            return pipeline_result

        except Exception as e:
            error_msg = f"Pipeline execution failed at stage: {str(e)}"
            logger.exception(error_msg)
            pipeline_result['error'] = error_msg
            return pipeline_result

    def run_complete_pipeline_sync(
        self,
        trade_date: Optional[date] = None,
        holdings: Optional[List[str]] = None,
        conn=None
    ) -> Dict:
        """
        Synchronous wrapper for run_complete_pipeline (for scheduler).

        Args:
            trade_date: Trade date (defaults to today)
            holdings: Optional list of holdings to always include
            conn: Database connection

        Returns:
            Dict with complete execution results
        """
        return asyncio.run(self.run_complete_pipeline(trade_date, holdings, conn))

    def _calculate_latest_dart_quarter(self, today: date) -> date:
        """
        Calculate latest available DART quarter based on current date.

        DART disclosure timeline: ~45 days after quarter end
        - Q1 (3/31): Available from mid-May
        - Q2 (6/30): Available from mid-August
        - Q3 (9/30): Available from mid-November
        - Q4 (12/31): Available from early March (next year)

        Args:
            today: Current date

        Returns:
            Latest available quarter end date
        """
        year = today.year
        month = today.month

        # Consider 45-day disclosure delay
        if month >= 11:  # November onwards
            return date(year, 9, 30)  # Q3
        elif month >= 8:  # August onwards
            return date(year, 6, 30)  # Q2
        elif month >= 5:  # May onwards
            return date(year, 3, 31)  # Q1
        else:  # January-April
            return date(year - 1, 12, 31)  # Previous year Q4
