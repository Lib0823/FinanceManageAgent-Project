"""Prophet Time-Series Forecasting Module

Trains Prophet models daily (no persistence) for D+1 to D+5 forecasting.
Extracts linear trends from predictions for feature engineering.
"""
import pandas as pd
import numpy as np
from prophet import Prophet
from sklearn.linear_model import LinearRegression
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class ProphetForecaster:
    """Prophet forecasting for stock price and buy ratio trends."""

    def __init__(self, lookback_days: int = 120, forecast_days: int = 5):
        """
        Initialize Prophet forecaster.

        Args:
            lookback_days: Training period (default: 120 trading days)
            forecast_days: Prediction horizon (default: D+1 to D+5)
        """
        self.lookback_days = lookback_days
        self.forecast_days = forecast_days

        logger.info(f"ProphetForecaster initialized (lookback={lookback_days}, forecast={forecast_days})")

    def _clean_for_fit(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prophet fit 직전 입력 계열을 정제한다.

        설계 의도: degenerate 입력(빈 계열·NaN/inf·상수·포인트 부족)이 stan 백엔드
        학습을 불안정하게 만들어 'stan_backend' 미초기화류의 연쇄 실패를 유발하는 것을
        사전에 차단한다. 행 제거가 아닌 정제를 우선하되, 학습 불가 계열은 빈 DataFrame을
        돌려 상위에서 empty-forecast로 graceful 처리되게 한다.

        Args:
            df: 'ds'/'y' 컬럼을 가진 DataFrame

        Returns:
            정제된 DataFrame. 학습 불가 시 빈 DataFrame.
        """
        if df is None or df.empty:
            return pd.DataFrame(columns=['ds', 'y'])

        if not all(col in df.columns for col in ['ds', 'y']):
            raise ValueError("DataFrame must have 'ds' and 'y' columns")

        clean = df.loc[:, ['ds', 'y']].copy()
        clean['ds'] = pd.to_datetime(clean['ds'], errors='coerce')
        clean['y'] = pd.to_numeric(clean['y'], errors='coerce')

        # NaN/inf 제거 (np.isfinite는 inf·-inf·NaN을 모두 걸러낸다)
        clean = clean[np.isfinite(clean['y'])]
        clean = clean.dropna(subset=['ds'])

        # 날짜 중복 제거 + 정렬 (Prophet는 ds 단조 증가를 가정)
        clean = clean.drop_duplicates(subset=['ds']).sort_values('ds').reset_index(drop=True)

        # 학습 가능성 판정: 최소 포인트 수 & 비상수(분산 존재)
        if len(clean) < 10:
            return pd.DataFrame(columns=['ds', 'y'])

        distinct_y = clean['y'].nunique(dropna=True)
        if distinct_y < 2:  # 모든 값이 동일 → Prophet가 추세를 추정할 수 없음
            return pd.DataFrame(columns=['ds', 'y'])

        return clean

    def train_and_forecast(self, df: pd.DataFrame, freq: str = 'B') -> Dict[str, np.ndarray]:
        """
        Train Prophet model and generate D+1 to D+5 forecast.

        견고성 강화:
        - 입력 계열을 _clean_for_fit로 정제(NaN/inf 제거·중복 제거·>=10 distinct·비상수).
        - stan_backend를 'CMDSTANPY'로 명시 지정한다. Prophet 1.3.0의 기본 백엔드
          자동 선택(_load_stan_backend(None))은 모든 백엔드 로드가 실패하면 조용히
          self.stan_backend를 설정하지 않은 채 반환하여, 이후 fit에서
          "'Prophet' object has no attribute 'stan_backend'" 가 발생한다.
          명시 지정 시 로드 실패가 즉시 예외로 드러나 재시도 가능하다.
        - 매 시도마다 새 Prophet 모델을 생성하여 1회 실패가 다음 시도로 전이되지 않게 한다.

        Args:
            df: DataFrame with columns 'ds' (date) and 'y' (value)
            freq: Frequency ('B' for business days)

        Returns:
            dict: {
                'yhat': predicted values array,
                'yhat_lower': lower confidence interval,
                'yhat_upper': upper confidence interval
            }
        """
        # 입력 정제 (학습 불가 계열이면 즉시 empty-forecast)
        try:
            clean_df = self._clean_for_fit(df)
        except ValueError as e:
            logger.error(f"Prophet input validation failed: {e}")
            return self._get_empty_forecast()

        if clean_df.empty:
            logger.warning(
                f"Insufficient/degenerate data for Prophet training "
                f"(rows={0 if df is None else len(df)} → unusable after cleaning)"
            )
            return self._get_empty_forecast()

        import warnings
        warnings.filterwarnings('ignore')

        # Suppress Prophet/cmdstanpy fitting logs
        import logging as prophet_logging
        prophet_logging.getLogger('prophet').setLevel(prophet_logging.ERROR)
        prophet_logging.getLogger('cmdstanpy').setLevel(prophet_logging.ERROR)

        # stan_backend 미초기화 등 일시적 백엔드 실패에 대비해 새 모델로 최대 2회 시도
        max_attempts = 2
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                model = Prophet(
                    daily_seasonality=False,
                    weekly_seasonality=True,
                    yearly_seasonality=False,  # 120 days insufficient for yearly
                    seasonality_mode='additive',
                    stan_backend='CMDSTANPY'  # 명시 지정: 자동 선택의 조용한 실패 방지
                )

                model.fit(clean_df, algorithm='Newton')

                # Generate forecast for next N business days
                future = model.make_future_dataframe(periods=self.forecast_days, freq=freq)
                forecast = model.predict(future)

                # Extract D+1 to D+5 predictions (last N rows)
                future_forecast = forecast.tail(self.forecast_days)

                return {
                    'yhat': future_forecast['yhat'].values,
                    'yhat_lower': future_forecast['yhat_lower'].values,
                    'yhat_upper': future_forecast['yhat_upper'].values
                }

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Prophet training attempt {attempt}/{max_attempts} failed: {e}"
                )
                # 다음 시도는 완전히 새 모델로 재생성 (상태 전이 차단)

        logger.error(f"Prophet training failed after {max_attempts} attempts: {last_error}")
        return self._get_empty_forecast()

    def calculate_trend_slope(self, yhat: np.ndarray) -> float:
        """
        Calculate linear regression slope of D+1 to D+5 predictions.

        Args:
            yhat: Predicted values array (length = forecast_days)

        Returns:
            float: Trend slope (양수: 상승, 음수: 하락)
        """
        if len(yhat) == 0:
            return 0.0

        try:
            X = np.arange(len(yhat)).reshape(-1, 1)  # [0, 1, 2, 3, 4]
            y = yhat.reshape(-1, 1)

            model = LinearRegression()
            model.fit(X, y)

            slope = model.coef_[0][0]
            return round(slope, 6)

        except Exception as e:
            logger.error(f"Slope calculation failed: {e}")
            return 0.0

    def calculate_uncertainty(self, yhat_lower: np.ndarray, yhat_upper: np.ndarray) -> float:
        """
        Calculate average confidence interval width for D+1 to D+5.

        Args:
            yhat_lower: Lower confidence interval
            yhat_upper: Upper confidence interval

        Returns:
            float: Average interval width (클수록 불확실성 높음)
        """
        if len(yhat_lower) == 0 or len(yhat_upper) == 0:
            return 0.0

        try:
            interval_widths = yhat_upper - yhat_lower
            avg_width = np.mean(interval_widths)
            return round(avg_width, 2)

        except Exception as e:
            logger.error(f"Uncertainty calculation failed: {e}")
            return 0.0

    def _get_empty_forecast(self) -> Dict[str, np.ndarray]:
        """
        Return empty forecast result (used when training fails).

        Returns:
            dict: Empty arrays for yhat, yhat_lower, yhat_upper
        """
        return {
            'yhat': np.array([]),
            'yhat_lower': np.array([]),
            'yhat_upper': np.array([])
        }

    def remove_outliers(
        self,
        df: pd.DataFrame,
        lower_pct: float = 1.0,
        upper_pct: float = 99.0,
        min_points: int = 10
    ) -> pd.DataFrame:
        """
        NumPy percentile 기준으로 y 값의 극단값을 윈저라이징(clip)한다.

        거래정지 해제 직후 급등락이나 수집 오류로 인한 비정상 수치가 Prophet 학습을
        왜곡(추세 과대추정·신뢰구간 폭발)하지 않도록, [p_lower, p_upper] 구간으로 클립한다.
        행을 제거(drop)하지 않고 클립하는 이유는 날짜 연속성을 유지하기 위함이며,
        클립은 percentile 경계 밖 값을 경계값으로 치환하여 데이터 포인트 수를 보존한다.

        Args:
            df: 'ds'/'y' 컬럼을 가진 DataFrame
            lower_pct: 하한 백분위수 (기본 1.0)
            upper_pct: 상한 백분위수 (기본 99.0)
            min_points: 이 값 미만이면 클립을 적용하지 않음 (Prophet 학습 최소 포인트 보존)

        Returns:
            y가 [p_lower, p_upper]로 클립된 DataFrame
        """
        if df.empty or 'y' not in df.columns:
            return df

        # 포인트가 너무 적으면(통계적 의미 없음) 클립하지 않고 그대로 반환
        if len(df) < min_points:
            return df

        y = df['y'].to_numpy(dtype=float)

        # 전부 동일하거나 NaN만 있는 경우 클립 불필요
        finite = y[np.isfinite(y)]
        if finite.size == 0:
            return df

        p_low = np.percentile(finite, lower_pct)
        p_high = np.percentile(finite, upper_pct)

        # 경계가 역전되거나 동일하면(분산 거의 없음) 클립 생략
        if not np.isfinite(p_low) or not np.isfinite(p_high) or p_high <= p_low:
            return df

        clipped = df.copy()
        clipped['y'] = np.clip(clipped['y'].astype(float), p_low, p_high)

        return clipped

    def prepare_series_for_prophet(
        self,
        dates: pd.Series,
        values: pd.Series,
        remove_outliers: bool = True
    ) -> pd.DataFrame:
        """
        Convert date/value series to Prophet format (ds/y columns).

        전처리: 중복 제거 → 정렬 → percentile 이상값 제거(윈저라이징).
        가격 계열·순매수 비율 계열 모두 동일 파이프라인을 통과한다.

        Args:
            dates: Date series
            values: Value series
            remove_outliers: True면 [p1, p99] percentile clip 적용 (기본 True)

        Returns:
            DataFrame with columns 'ds' (datetime) and 'y' (float)
        """
        df = pd.DataFrame({
            'ds': pd.to_datetime(dates),
            'y': values.astype(float)
        })

        # Remove duplicates and sort
        df = df.drop_duplicates(subset=['ds']).sort_values('ds').reset_index(drop=True)

        # NumPy percentile 기반 이상값 제거 (설계: 4-1 이상값 제거)
        if remove_outliers:
            df = self.remove_outliers(df)

        return df

    def validate_forecast_quality(self, forecast: Dict[str, np.ndarray]) -> bool:
        """
        Check if forecast is valid and reasonable.

        Args:
            forecast: Forecast dictionary from train_and_forecast

        Returns:
            bool: True if forecast is valid
        """
        yhat = forecast.get('yhat', np.array([]))

        # Check if forecast exists
        if len(yhat) == 0:
            return False

        # Check for NaN values
        if np.isnan(yhat).any():
            return False

        # Check for unreasonable values (e.g., negative prices)
        if np.any(yhat < 0):
            return False

        return True
