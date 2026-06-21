"""Time-Series Analysis Module - Stage 2-3

Uses Prophet for 120-day training → D+1 to D+5 forecasting.
No database storage (daily fit, no model persistence).

Output: 3 features per stock
- prophet_price_trend: Linear slope of D+1~D+5 price predictions
- prophet_volume_trend: Linear slope of D+1~D+5 buy ratio predictions
- prophet_price_uncertainty: Average confidence interval width
"""
import pandas as pd
import numpy as np
from typing import List, Dict
from datetime import datetime
import logging

from collectors.kis_client import KISClient
from models.prophet_trainer import ProphetForecaster

logger = logging.getLogger(__name__)

# Prophet 학습에 필요한 최소 거래일 수. 기간 조회(period)가 이보다 적게 반환하면
# 검증된 일봉 조회(get_daily_ohlcv, FHKST01010400)로 폴백한다.
MIN_TRADING_DAYS = 60


class TimeSeriesAnalyzer:
    """Time-series forecasting using Prophet for stock analysis."""

    def __init__(self, kis_client: 'KISClient' = None, lookback_days: int = 120):
        """
        Initialize time-series analyzer.

        Args:
            kis_client: Optional KISClient instance (shares OAuth token cache if provided)
            lookback_days: Training period for Prophet (default: 120 trading days)
        """
        from collectors.kis_client import KISClient
        self.kis_client = kis_client if kis_client is not None else KISClient()
        self.prophet = ProphetForecaster(lookback_days=lookback_days, forecast_days=5)
        self.lookback_days = lookback_days

        logger.info(f"TimeSeriesAnalyzer initialized (lookback={lookback_days} days)")

    async def analyze_stocks(self, stock_codes: List[str]) -> pd.DataFrame:
        """
        Perform time-series analysis for filtered stocks.

        Args:
            stock_codes: List of stock codes (30 filtered stocks)

        Returns:
            DataFrame with columns: stock_code, prophet_price_trend,
                                   prophet_volume_trend, prophet_price_uncertainty
        """
        logger.info(f"Starting time-series analysis for {len(stock_codes)} stocks")

        results = []

        for stock_code in stock_codes:
            try:
                # Analyze single stock
                features = await self._analyze_single_stock(stock_code)
                results.append(features)

                logger.debug(f"{stock_code}: price_trend={features['prophet_price_trend']:.4f}, "
                           f"volume_trend={features['prophet_volume_trend']:.4f}, "
                           f"uncertainty={features['prophet_price_uncertainty']:.2f}")

            except Exception as e:
                logger.error(f"Time-series analysis failed for {stock_code}: {e}")
                # Fallback to neutral values
                results.append({
                    'stock_code': stock_code,
                    'prophet_price_trend': 0.0,
                    'prophet_volume_trend': 0.0,
                    'prophet_price_uncertainty': 0.0
                })

        df = pd.DataFrame(results)
        logger.info(f"Time-series analysis complete: {len(df)} stocks")

        return df

    async def _analyze_single_stock(self, stock_code: str) -> Dict:
        """
        Analyze single stock with Prophet forecasting.

        Args:
            stock_code: Stock code

        Returns:
            dict: {stock_code, prophet_price_trend, prophet_volume_trend, prophet_price_uncertainty,
                   plus detailed D+1~D+5 values for web display}
        """
        # 0. Fetch 120-day OHLCV ONCE (period endpoint) and reuse for price series.
        #    Avoids the previous double-fetch (price + buy-ratio each called get_daily_ohlcv).
        ohlcv_df = await self._fetch_lookback_ohlcv(stock_code)

        # 1. Prepare price series from the single OHLCV fetch
        price_series = self._build_price_series(stock_code, ohlcv_df)

        # 2. Prepare buy-ratio series from real buy/sell execution volume (separate endpoint)
        volume_series = await self._prepare_buy_ratio_series(stock_code, ohlcv_df)

        # 3. Forecast price
        price_forecast = self.prophet.train_and_forecast(price_series)
        prophet_price_trend = self.prophet.calculate_trend_slope(price_forecast['yhat'])
        prophet_price_uncertainty = self.prophet.calculate_uncertainty(
            price_forecast['yhat_lower'],
            price_forecast['yhat_upper']
        )

        # 4. Forecast volume (buy ratio)
        volume_forecast = self.prophet.train_and_forecast(volume_series)
        prophet_volume_trend = self.prophet.calculate_trend_slope(volume_forecast['yhat'])

        # 5. Extract detailed D+1~D+5 values for web display
        result = {
            'stock_code': stock_code,
            'prophet_price_trend': prophet_price_trend,
            'prophet_volume_trend': prophet_volume_trend,
            'prophet_price_uncertainty': prophet_price_uncertainty
        }

        # Add detailed price predictions (D+1 to D+5)
        if len(price_forecast['yhat']) >= 5:
            for i in range(5):
                result[f'yhat_price_d{i+1}'] = float(price_forecast['yhat'][i])
                result[f'yhat_price_lower_d{i+1}'] = float(price_forecast['yhat_lower'][i])
                result[f'yhat_price_upper_d{i+1}'] = float(price_forecast['yhat_upper'][i])

        # Add detailed volume predictions (D+1 to D+5)
        if len(volume_forecast['yhat']) >= 5:
            for i in range(5):
                result[f'yhat_volume_d{i+1}'] = float(volume_forecast['yhat'][i])
                result[f'yhat_volume_lower_d{i+1}'] = float(volume_forecast['yhat_lower'][i])
                result[f'yhat_volume_upper_d{i+1}'] = float(volume_forecast['yhat_upper'][i])

        return result

    async def _fetch_lookback_ohlcv(self, stock_code: str) -> pd.DataFrame:
        """
        Prophet 학습용 일봉을 견고한 폴백 체인으로 확보한다.

        우선순위(primary → fallback):
        1. get_daily_ohlcv_period(FHKST03010100): 최근 ~100거래일 (장기 학습 선호).
        2. 위가 실패하거나 MIN_TRADING_DAYS(60) 미만이면
           get_daily_ohlcv(FHKST01010400)로 폴백. 6/12 실행에서 Stage 1이 이 호출로
           30건을 정상 수신했으므로(검증됨), 기간 조회가 500을 내도 학습용 실데이터를
           확보할 수 있다. ~30일 윈도우도 폴백으로서 허용한다(정확성 > 120일 고수).

        둘 중 더 많은 거래일을 반환하는 쪽을 채택한다. 이렇게 하면 기간 조회가
        부분 성공(예: 40건)이고 일봉 조회가 30건이어도 더 긴 계열을 쓴다.

        Args:
            stock_code: Stock code

        Returns:
            OHLCV DataFrame (oldest first). 두 경로 모두 실패 시 빈 DataFrame.
        """
        period_df = pd.DataFrame()
        try:
            period_df = await self.kis_client.get_daily_ohlcv_period(
                stock_code, days=self.lookback_days
            )
        except Exception as e:
            logger.warning(f"Period OHLCV fetch raised for {stock_code}: {e}")
            period_df = pd.DataFrame()

        period_rows = 0 if period_df is None or period_df.empty else len(period_df)

        # 기간 조회가 충분하면 그대로 사용
        if period_rows >= MIN_TRADING_DAYS:
            logger.debug(f"Lookback OHLCV (period): {period_rows} days for {stock_code}")
            return period_df

        # 폴백: 검증된 일봉 조회 (FHKST01010400). 최대 100건까지 시도.
        logger.warning(
            f"Period OHLCV insufficient for {stock_code} "
            f"({period_rows} rows < {MIN_TRADING_DAYS}); falling back to get_daily_ohlcv"
        )
        fallback_df = pd.DataFrame()
        try:
            fallback_df = await self.kis_client.get_daily_ohlcv(stock_code, days=100)
        except Exception as e:
            logger.warning(f"Fallback get_daily_ohlcv raised for {stock_code}: {e}")
            fallback_df = pd.DataFrame()

        fallback_rows = 0 if fallback_df is None or fallback_df.empty else len(fallback_df)

        # 두 경로 중 더 긴 실데이터 계열을 채택
        if fallback_rows == 0 and period_rows == 0:
            logger.warning(f"No OHLCV from either path for {stock_code}")
            return pd.DataFrame()

        if fallback_rows >= period_rows:
            logger.debug(f"Lookback OHLCV (fallback daily): {fallback_rows} days for {stock_code}")
            return fallback_df

        logger.debug(f"Lookback OHLCV (period, short): {period_rows} days for {stock_code}")
        return period_df

    def _build_price_series(self, stock_code: str, ohlcv_df: pd.DataFrame) -> pd.DataFrame:
        """
        이미 받아온 OHLCV로부터 Prophet 가격 계열('ds'/'y')을 만든다.

        Args:
            stock_code: Stock code
            ohlcv_df: _fetch_lookback_ohlcv가 반환한 OHLCV DataFrame

        Returns:
            DataFrame with columns 'ds' (date) and 'y' (close price)
        """
        try:
            if ohlcv_df is None or ohlcv_df.empty:
                logger.warning(f"No OHLCV data for price series: {stock_code}")
                return pd.DataFrame(columns=['ds', 'y'])

            # 전처리(중복 제거·정렬·percentile 이상값 제거)는 prepare_series_for_prophet 내부에서 수행
            price_series = self.prophet.prepare_series_for_prophet(
                dates=pd.to_datetime(ohlcv_df['trade_date'], format='%Y%m%d'),
                values=ohlcv_df['close']
            )

            logger.debug(f"Price series prepared: {len(price_series)} days for {stock_code}")
            return price_series

        except Exception as e:
            logger.error(f"Price series build failed for {stock_code}: {e}")
            return pd.DataFrame(columns=['ds', 'y'])

    async def _prepare_price_series(self, stock_code: str) -> pd.DataFrame:
        """
        Prepare price series for Prophet training (standalone path).

        주의: _analyze_single_stock는 중복 호출을 피하기 위해 _fetch_lookback_ohlcv +
        _build_price_series 경로를 사용한다. 본 메서드는 가격 계열만 단독으로 필요한
        호출자를 위한 하위 호환 진입점이며, 내부적으로 동일한 120거래일 기간 조회를 쓴다.

        Args:
            stock_code: Stock code

        Returns:
            DataFrame with columns 'ds' (date) and 'y' (close price)
        """
        ohlcv_df = await self._fetch_lookback_ohlcv(stock_code)
        return self._build_price_series(stock_code, ohlcv_df)

    async def _prepare_buy_ratio_series(
        self,
        stock_code: str,
        ohlcv_df: pd.DataFrame = None
    ) -> pd.DataFrame:
        """
        순매수 비율 계열을 Prophet 입력('ds'/'y')으로 만든다.

        설계(2-4, 3-2): 순매수 비율 = 매수체결량 / 총체결량.
        총 거래량만으로는 매수 주도/매도 주도를 구분할 수 없으므로,
        일별 매수·매도 체결량(FHKST03010800)을 사용해 방향성을 확보한다.
        값이 0.5보다 크면 매수세 우위, 작으면 매도세 우위를 의미한다.

        과거 구현은 (close-low)/(high-low) 가격 위치 프록시(MVP 단축)였으나,
        이는 체결 방향성과 무관하므로 실제 체결량 기반으로 대체한다.

        Args:
            stock_code: Stock code
            ohlcv_df: (선택) 거래량 0 보정 등에 사용할 수 있는 일봉 데이터.
                      현재 구현은 체결량 합으로 총량을 산출하므로 필수는 아니다.

        폴백(6/12 장애 대응): 체결량 조회가 실패하거나 비면, 이미 받아온 OHLCV로부터
        일중 종가 위치 (close - low) / (high - low) 를 방향성 프록시로 사용한다.
        이 값은 0~1 범위로, 0.5 초과면 매수 주도(종가가 고가 쪽 마감), 미만이면 매도
        주도를 의미하므로 buy_ratio와 동일하게 해석 가능하다. 이로써 volume_trend가
        모든 종목에서 0.0으로 붕괴하는 것을 방지한다(빈 계열 반환 금지).

        Returns:
            DataFrame with columns 'ds' (date) and 'y' (buy ratio, 0.0~1.0).
            체결량·프록시 모두 불가한 극단적 경우에만 빈 DataFrame 반환.
        """
        # 1차: 실제 매수/매도 체결량 기반 순매수 비율
        try:
            volume_df = await self.kis_client.get_daily_trade_volume(
                stock_code, days=self.lookback_days
            )

            if volume_df is not None and not volume_df.empty:
                total = volume_df['total_volume'].astype(float)
                buy = volume_df['buy_volume'].astype(float)
                buy_ratio = pd.Series(
                    np.where(total > 0, buy / total, 0.5),
                    index=volume_df.index
                )

                buy_ratio_series = self.prophet.prepare_series_for_prophet(
                    dates=pd.to_datetime(volume_df['trade_date'], format='%Y%m%d'),
                    values=buy_ratio
                )

                logger.debug(f"Buy ratio series (trade volume): "
                             f"{len(buy_ratio_series)} days for {stock_code}")
                return buy_ratio_series

            logger.warning(f"No daily trade-volume data for {stock_code}; "
                           f"falling back to OHLCV close-position proxy")

        except Exception as e:
            logger.warning(f"Buy ratio via trade volume failed for {stock_code}: {e}; "
                           f"falling back to OHLCV close-position proxy")

        # 2차(폴백): OHLCV 종가 위치 프록시 = (종가-저가)/(고가-저가)
        return self._build_buy_ratio_proxy_from_ohlcv(stock_code, ohlcv_df)

    def _build_buy_ratio_proxy_from_ohlcv(
        self,
        stock_code: str,
        ohlcv_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        OHLCV로부터 매수세 방향성 프록시 계열을 만든다.

        프록시 정의: close_position = (종가 - 저가) / (고가 - 저가), 범위 [0, 1].
        - > 0.5: 종가가 고가 쪽에 형성 → 매수 주도(buy-led) 마감
        - < 0.5: 종가가 저가 쪽에 형성 → 매도 주도(sell-led) 마감
        고가==저가(변동 없음)인 날은 중립 0.5로 둔다.

        체결량 API(FHKST03010800)가 실패해도 volume_trend가 0.0으로 붕괴하지 않도록
        보장하기 위한 문서화된 대체 신호이다.

        Args:
            stock_code: Stock code
            ohlcv_df: _fetch_lookback_ohlcv가 반환한 OHLCV DataFrame

        Returns:
            DataFrame with columns 'ds' (date) and 'y' (close-position proxy, 0.0~1.0).
            OHLCV가 없으면 빈 DataFrame.
        """
        try:
            if ohlcv_df is None or ohlcv_df.empty:
                logger.warning(f"No OHLCV for buy-ratio proxy: {stock_code}")
                return pd.DataFrame(columns=['ds', 'y'])

            high = ohlcv_df['high'].astype(float)
            low = ohlcv_df['low'].astype(float)
            close = ohlcv_df['close'].astype(float)
            rng = high - low

            close_position = pd.Series(
                np.where(rng > 0, (close - low) / rng, 0.5),
                index=ohlcv_df.index
            )

            proxy_series = self.prophet.prepare_series_for_prophet(
                dates=pd.to_datetime(ohlcv_df['trade_date'], format='%Y%m%d'),
                values=close_position
            )

            logger.debug(f"Buy ratio series (OHLCV proxy): "
                         f"{len(proxy_series)} days for {stock_code}")
            return proxy_series

        except Exception as e:
            logger.error(f"Buy-ratio proxy build failed for {stock_code}: {e}")
            return pd.DataFrame(columns=['ds', 'y'])

    def validate_features(self, df: pd.DataFrame) -> Dict[str, bool]:
        """
        Validate time-series features for data quality.

        Args:
            df: DataFrame with time-series features

        Returns:
            dict: {validation_metric: is_valid}
        """
        validation_results = {}

        # Check for required columns
        required_columns = ['stock_code', 'prophet_price_trend', 'prophet_volume_trend',
                           'prophet_price_uncertainty']

        for col in required_columns:
            validation_results[f'{col}_exists'] = col in df.columns

        if len(df) > 0:
            # Check for excessive zero values (might indicate forecasting failure)
            if 'prophet_price_trend' in df.columns:
                zero_ratio = (df['prophet_price_trend'] == 0.0).sum() / len(df)
                validation_results['diverse_price_trends'] = zero_ratio < 0.8

            if 'prophet_volume_trend' in df.columns:
                zero_ratio = (df['prophet_volume_trend'] == 0.0).sum() / len(df)
                validation_results['diverse_volume_trends'] = zero_ratio < 0.8

            # Check for NaN values
            for col in required_columns[1:]:  # Exclude stock_code
                if col in df.columns:
                    validation_results[f'{col}_no_nan'] = not df[col].isna().any()

            # Check uncertainty range (should be positive)
            if 'prophet_price_uncertainty' in df.columns:
                validation_results['uncertainty_positive'] = (df['prophet_price_uncertainty'] >= 0).all()

        return validation_results
