"""Database repository for CRUD operations."""
import logging
from datetime import date
from typing import List, Optional, Dict
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from .models import StockFilterScore, MarketDailySummary, ProphetForecast, SessionLocal, engine
from config.constants import STOCK_NAMES

logger = logging.getLogger(__name__)


class DatabaseRepository:
    """Repository pattern for database operations."""

    def __init__(self):
        self.session_factory = SessionLocal
        self.engine = engine  # Added: Required for pandas to_sql() operations

    def save_filter_scores(self, df: pd.DataFrame, trade_date: date) -> bool:
        """
        Save stock filter scores to database.

        Args:
            df: DataFrame with columns matching StockFilterScore model
            trade_date: Trade date for these scores

        Returns:
            bool: True if successful, False otherwise
        """
        session = self.session_factory()
        try:
            logger.info(f"Saving {len(df)} filter scores for {trade_date}")
            logger.debug(f"DataFrame columns: {df.columns.tolist()}")

            # Delete existing records for this date (if any)
            session.query(StockFilterScore).filter(
                StockFilterScore.score_date == trade_date
            ).delete()

            # Convert DataFrame to model objects
            records = []
            for idx, row in df.iterrows():
                try:
                    record = StockFilterScore(
                        stock_code=row['stock_code'],
                        stock_name=row.get('stock_name', ''),  # Optional, defaults to empty if not present
                        score_date=trade_date,
                        foreign_net_buy=int(row['foreign_net_buy']),
                        institutional_net_buy=int(row['institutional_net_buy']),
                        vol_avg_multiple=float(row['volume_ratio']),
                        price_volatility=float(row['price_volatility']),
                        scaler_score=float(row['final_score']),
                        is_selected=bool(row['is_selected'])
                    )
                    records.append(record)
                except KeyError as e:
                    logger.error(f"Missing column in row {idx}: {e}")
                    logger.error(f"Available columns: {row.index.tolist()}")
                    raise

            # Bulk insert
            session.bulk_save_objects(records)
            session.commit()

            logger.info(f"Successfully saved {len(records)} filter scores")
            return True

        except SQLAlchemyError as e:
            logger.error(f"Database error while saving filter scores: {e}")
            session.rollback()
            return False

        finally:
            session.close()

    def get_filter_scores(self, trade_date: date) -> Optional[pd.DataFrame]:
        """
        Retrieve filter scores for a specific date.

        Args:
            trade_date: Trade date to retrieve

        Returns:
            DataFrame or None if no data found
        """
        session = self.session_factory()
        try:
            records = session.query(StockFilterScore).filter(
                StockFilterScore.score_date == trade_date
            ).all()

            if not records:
                logger.warning(f"No filter scores found for {trade_date}")
                return None

            # Convert to DataFrame
            data = [{
                'stock_code': r.stock_code,
                'stock_name': r.stock_name,
                'score_date': r.score_date,
                'foreign_net_buy': r.foreign_net_buy,
                'institutional_net_buy': r.institutional_net_buy,
                'volume_ratio': float(r.vol_avg_multiple),
                'price_volatility': float(r.price_volatility),
                'final_score': float(r.scaler_score),
                'is_selected': r.is_selected
            } for r in records]

            df = pd.DataFrame(data)
            logger.info(f"Retrieved {len(df)} filter scores for {trade_date}")

            return df

        except SQLAlchemyError as e:
            logger.error(f"Database error while retrieving filter scores: {e}")
            return None

        finally:
            session.close()

    def get_selected_stocks(self, trade_date: date) -> List[str]:
        """
        Get list of selected stock codes for a specific date.

        Args:
            trade_date: Trade date

        Returns:
            List of stock codes (empty list if none found)
        """
        session = self.session_factory()
        try:
            records = session.query(StockFilterScore.stock_code).filter(
                StockFilterScore.score_date == trade_date,
                StockFilterScore.is_selected == True
            ).all()

            stock_codes = [r.stock_code for r in records]
            logger.info(f"Retrieved {len(stock_codes)} selected stocks for {trade_date}")

            return stock_codes

        except SQLAlchemyError as e:
            logger.error(f"Database error while retrieving selected stocks: {e}")
            return []

        finally:
            session.close()

    def get_latest_filter_date(self) -> Optional[date]:
        """
        Get the most recent trade date with filter scores.

        Returns:
            date or None if no data exists
        """
        session = self.session_factory()
        try:
            result = session.query(StockFilterScore.score_date).order_by(
                StockFilterScore.score_date.desc()
            ).first()

            if result:
                latest_date = result[0]
                logger.info(f"Latest filter date: {latest_date}")
                return latest_date
            else:
                logger.warning("No filter scores found in database")
                return None

        except SQLAlchemyError as e:
            logger.error(f"Database error while retrieving latest date: {e}")
            return None

        finally:
            session.close()

    def save_quantitative_features(self,
                                   stock_code: str,
                                   trade_date: date,
                                   morning_return: float,
                                   close_position: float) -> bool:
        """
        Save quantitative features (morning_return, close_position) to stock_filter_score table.

        Args:
            stock_code: 6-digit stock code
            trade_date: Trade date
            morning_return: Morning return percentage (09:00 → 10:00)
            close_position: Close position in day's range (0.0 ~ 1.0)

        Returns:
            True if successful, False otherwise
        """
        session = self.session_factory()
        try:
            # Update existing record (created by filter stage)
            record = session.query(StockFilterScore).filter(
                StockFilterScore.stock_code == stock_code,
                StockFilterScore.score_date == trade_date
            ).first()

            if record:
                record.morning_return = morning_return
                record.close_position = close_position
                session.commit()
                logger.debug(f"Updated quantitative features for {stock_code}")
                return True
            else:
                logger.warning(f"No filter score record found for {stock_code} on {trade_date}")
                return False

        except SQLAlchemyError as e:
            logger.error(f"Error saving quantitative features for {stock_code}: {e}")
            session.rollback()
            return False

        finally:
            session.close()

    def save_sentiment_analysis(self,
                                stock_code: str,
                                analysis_date: date,
                                sentiment_score: float,
                                news_count: int) -> bool:
        """
        Save sentiment analysis results to news_analysis table.

        Args:
            stock_code: 6-digit stock code
            analysis_date: Analysis date
            sentiment_score: Sentiment score (-1.0 ~ 1.0)
            news_count: Number of news articles analyzed

        Returns:
            True if successful, False otherwise
        """
        try:
            import pandas as pd
            df = pd.DataFrame([{
                'stock_code': stock_code,
                'analysis_date': analysis_date,
                'sentiment_score': sentiment_score,
                'news_count': news_count
            }])

            # Use engine from session_factory
            df.to_sql('news_analysis', self.engine, if_exists='append', index=False)
            logger.debug(f"Saved sentiment analysis for {stock_code}: {sentiment_score:.2f}")
            return True

        except Exception as e:
            logger.error(f"Error saving sentiment analysis for {stock_code}: {e}")
            return False

    def save_market_summary(
        self,
        summary_data: Dict[str, any],
        summary_date: date
    ) -> bool:
        """
        Save market daily summary to market_daily_summary table.

        Args:
            summary_data: Dict with market summary data
            summary_date: Summary date

        Returns:
            True if successful, False otherwise
        """
        session = self.session_factory()
        try:
            logger.info(f"Saving market summary for {summary_date}")

            # Delete existing record for this date (if any)
            session.query(MarketDailySummary).filter(
                MarketDailySummary.summary_date == summary_date
            ).delete()

            # Create new record with all available fields
            record = MarketDailySummary(
                summary_date=summary_date,
                kospi_index=summary_data.get('kospi_index'),
                kospi_change_rate=summary_data.get('kospi_change_rate'),
                kospi_volume=summary_data.get('kospi_volume'),
                total_stocks=summary_data.get('total_stocks'),
                rising_stocks=summary_data.get('rising_stocks'),
                falling_stocks=summary_data.get('falling_stocks'),
                unchanged_stocks=summary_data.get('unchanged_stocks'),
                total_foreign_net_buy=summary_data.get('total_foreign_net_buy'),
                total_institutional_net_buy=summary_data.get('total_institutional_net_buy'),
                market_sentiment_score=summary_data.get('market_sentiment_score')
            )

            session.add(record)
            session.commit()

            logger.info(f"Successfully saved market summary: KOSPI={summary_data.get('kospi_index'):.2f}")
            return True

        except SQLAlchemyError as e:
            logger.error(f"Database error while saving market summary: {e}")
            session.rollback()
            return False

        finally:
            session.close()

    # Deprecated: kept for backward compatibility
    def save_kospi_index(self, kospi_data: Dict[str, float], trade_date: date) -> bool:
        """Deprecated: Use save_market_summary instead."""
        return self.save_market_summary(kospi_data, trade_date)

    def save_prophet_forecast_detailed(self, forecast_data: Dict, trade_date: date) -> bool:
        """
        Save detailed Prophet forecast results with D+1~D+5 values to prophet_forecast table.

        Args:
            forecast_data: Dict with all Prophet forecast values including detailed D+1~D+5 predictions
            trade_date: Trade date

        Returns:
            True if successful, False otherwise
        """
        session = self.session_factory()
        try:
            stock_code = forecast_data['stock_code']
            logger.debug(f"Saving detailed Prophet forecast for {stock_code}")

            # Delete existing record for this stock and date (if any)
            session.query(ProphetForecast).filter(
                ProphetForecast.stock_code == stock_code,
                ProphetForecast.forecast_date == trade_date  # Fixed: use forecast_date column name
            ).delete()

            # Helper function to clamp numeric values to DB column limits
            def clamp_value(value, max_val, min_val=None):
                """Clamp value to prevent numeric overflow in DB"""
                if value is None:
                    return None
                if min_val is not None:
                    value = max(min_val, value)
                return min(max_val, value)

            # Clamp values to DB column limits to prevent overflow
            # NUMERIC(12, 2) → max = 9,999,999,999.99
            # NUMERIC(10, 6) → max = 9,999.999999
            # NUMERIC(10, 4) → max = 999,999.9999

            price_trend_val = clamp_value(forecast_data.get('prophet_price_trend', 0.0), 9999.0, -9999.0)
            volume_trend_val = clamp_value(forecast_data.get('prophet_volume_trend', 0.0), 9999.0, -9999.0)
            uncertainty_val = clamp_value(forecast_data.get('prophet_price_uncertainty', 0.0), 999999.0, 0.0)

            # Create new record with all detailed values
            record = ProphetForecast(
                stock_code=stock_code,
                stock_name=forecast_data.get('stock_name', stock_code),  # Added: stock_name required by DB schema
                forecast_date=trade_date,  # Fixed: use forecast_date column name
                # Aggregated trends - fixed column names to match DB schema with clamping
                price_trend=price_trend_val,
                volume_trend=volume_trend_val,
                price_uncertainty=uncertainty_val,
                # Detailed predictions (D+1 to D+5) - fixed column names to match DB schema
                # Clamp to NUMERIC(12, 2) max = 9,999,999,999.99
                yhat_d1=clamp_value(forecast_data.get('yhat_price_d1'), 9999999999.99, 0.0),
                yhat_d2=clamp_value(forecast_data.get('yhat_price_d2'), 9999999999.99, 0.0),
                yhat_d3=clamp_value(forecast_data.get('yhat_price_d3'), 9999999999.99, 0.0),
                yhat_d4=clamp_value(forecast_data.get('yhat_price_d4'), 9999999999.99, 0.0),
                yhat_d5=clamp_value(forecast_data.get('yhat_price_d5'), 9999999999.99, 0.0),
                yhat_lower_d1=clamp_value(forecast_data.get('yhat_price_lower_d1'), 9999999999.99, 0.0),
                yhat_lower_d2=clamp_value(forecast_data.get('yhat_price_lower_d2'), 9999999999.99, 0.0),
                yhat_lower_d3=clamp_value(forecast_data.get('yhat_price_lower_d3'), 9999999999.99, 0.0),
                yhat_lower_d4=clamp_value(forecast_data.get('yhat_price_lower_d4'), 9999999999.99, 0.0),
                yhat_lower_d5=clamp_value(forecast_data.get('yhat_price_lower_d5'), 9999999999.99, 0.0),
                yhat_upper_d1=clamp_value(forecast_data.get('yhat_price_upper_d1'), 9999999999.99, 0.0),
                yhat_upper_d2=clamp_value(forecast_data.get('yhat_price_upper_d2'), 9999999999.99, 0.0),
                yhat_upper_d3=clamp_value(forecast_data.get('yhat_price_upper_d3'), 9999999999.99, 0.0),
                yhat_upper_d4=clamp_value(forecast_data.get('yhat_price_upper_d4'), 9999999999.99, 0.0),
                yhat_upper_d5=clamp_value(forecast_data.get('yhat_price_upper_d5'), 9999999999.99, 0.0)
            )

            session.add(record)
            session.commit()

            logger.debug(f"Successfully saved detailed Prophet forecast for {stock_code}")
            return True

        except SQLAlchemyError as e:
            logger.error(f"Database error while saving Prophet forecast: {e}")
            session.rollback()
            return False

        finally:
            session.close()

    def save_prophet_forecast(self,
                             stock_code: str,
                             forecast_date: date,
                             prophet_price_trend: float,
                             prophet_volume_trend: float,
                             prophet_price_uncertainty: float,
                             conn) -> bool:
        """
        [Deprecated] Save Prophet forecast results to prophet_forecast table.
        Use save_prophet_forecast_detailed() for new implementations.

        Args:
            stock_code: 6-digit stock code
            forecast_date: Forecast base date
            prophet_price_trend: Price trend slope
            prophet_volume_trend: Volume trend slope
            prophet_price_uncertainty: Price uncertainty (CI width)
            conn: Database connection

        Returns:
            True if successful, False otherwise
        """
        try:
            import pandas as pd
            df = pd.DataFrame([{
                'stock_code': stock_code,
                'forecast_date': forecast_date,
                'price_trend': prophet_price_trend,
                'volume_trend': prophet_volume_trend,
                'price_uncertainty': prophet_price_uncertainty
            }])

            df.to_sql('prophet_forecast', conn, if_exists='append', index=False)
            logger.debug(f"Saved Prophet forecast for {stock_code}")
            return True

        except Exception as e:
            logger.error(f"Error saving Prophet forecast for {stock_code}: {e}")
            return False

    def save_ai_decisions(self,
                         decisions: dict,
                         trade_date: date,
                         conn=None) -> bool:
        """
        Save Gemini AI trading decisions to ai_trade_decision table.

        Args:
            decisions: Dict with buy_top3 and sell_top3 lists
            trade_date: Trade date
            conn: Database connection (optional, uses engine if None)

        Returns:
            True if successful, False otherwise
        """
        try:
            import pandas as pd
            records = []

            # Buy decisions
            for idx, item in enumerate(decisions.get('buy_top3', [])):
                stock_code = item['stock_code']
                records.append({
                    'stock_code': stock_code,
                    'stock_name': STOCK_NAMES.get(stock_code, 'Unknown'),  # Lookup from constants
                    'decision_date': trade_date,  # Changed from trade_date
                    'decision': 'BUY',  # Changed from decision_type
                    'reason': item.get('reason', ''),
                    'rank': idx + 1
                })

            # Sell decisions
            for idx, item in enumerate(decisions.get('sell_top3', [])):
                stock_code = item['stock_code']
                records.append({
                    'stock_code': stock_code,
                    'stock_name': STOCK_NAMES.get(stock_code, 'Unknown'),  # Lookup from constants
                    'decision_date': trade_date,  # Changed from trade_date
                    'decision': 'SELL',  # Changed from decision_type
                    'reason': item.get('reason', ''),
                    'rank': idx + 1
                })

            if records:
                df = pd.DataFrame(records)
                # Use engine if conn not provided
                db_conn = conn if conn is not None else self.engine
                df.to_sql('ai_trade_decision', db_conn, if_exists='append', index=False)
                logger.info(f"Saved {len(records)} AI trading decisions")
                return True
            else:
                logger.warning("No AI decisions to save")
                return False

        except Exception as e:
            logger.error(f"Error saving AI decisions: {e}")
            return False

    def save_safety_filter_results(self,
                                   filter_results: list,
                                   filter_date: date,
                                   conn=None) -> bool:
        """
        Save safety filter results to safety_filter_result table.

        Args:
            filter_results: List of filter result dicts
            filter_date: Filter date
            conn: Database connection (optional, uses engine if None)

        Returns:
            True if successful, False otherwise
        """
        try:
            import pandas as pd
            import json

            records = []
            for result in filter_results:
                records.append({
                    'stock_code': result['stock_code'],
                    'stock_name': result.get('stock_name', ''),
                    'filter_date': filter_date,
                    'passed': result['passed'],
                    'failure_reason': result.get('failure_reason'),
                    'max_quantity': result.get('max_quantity'),
                    'current_price': result.get('current_price'),
                    'filter_checks': json.dumps(result.get('filter_checks', {}))
                })

            if records:
                df = pd.DataFrame(records)
                # Use engine if conn not provided
                db_conn = conn if conn is not None else self.engine
                df.to_sql('safety_filter_result', db_conn, if_exists='append', index=False)
                logger.info(f"Saved {len(records)} safety filter results")
                return True
            else:
                logger.warning("No safety filter results to save")
                return False

        except Exception as e:
            logger.error(f"Error saving safety filter results: {e}")
            return False

    def get_user_order_amount(self, user_id: int = 1) -> int:
        """
        Get user's configured order_amount from user_trade_config table.

        Args:
            user_id: User ID (default: 1 for MVP)

        Returns:
            order_amount in won (default: 1,000,000)
        """
        try:
            with self.session_factory() as session:
                query = text("""
                    SELECT order_amount
                    FROM user_trade_config
                    WHERE user_id = :user_id
                """)

                result = session.execute(query, {'user_id': user_id}).fetchone()

                if result:
                    return result[0]
                else:
                    logger.warning(f"No trade config found for user_id={user_id}, using default 1,000,000")
                    return 1_000_000  # Default 1M won

        except Exception as e:
            logger.error(f"Failed to fetch user order_amount: {e}")
            return 1_000_000  # Fallback to default
