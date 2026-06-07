# Database Save Implementation

AI 파이프라인 Stage 2 (분석 단계)의 `news_analysis`와 `prophet_forecast` 테이블 저장 구현 문서.

## 시스템 개요

파이프라인은 매일 30개 종목에 대한 감성 분석과 시계열 예측을 수행하며, 결과를 PostgreSQL 데이터베이스에 저장합니다.

**저장 성공률**: 100% (30/30 records)

## DatabaseRepository 구조

### 초기화

```python
class DatabaseRepository:
    def __init__(self):
        self.session_factory = SessionLocal
        self.engine = engine  # pandas to_sql() 작업에 필요
```

`self.engine` 속성은 pandas DataFrame의 `to_sql()` 메서드 호출 시 필수입니다.

### 감성 분석 저장

```python
def save_sentiment_analysis(self,
                            stock_code: str,
                            analysis_date: date,
                            sentiment_score: float,
                            news_count: int) -> bool:
    try:
        import pandas as pd
        df = pd.DataFrame([{
            'stock_code': stock_code,
            'analysis_date': analysis_date,
            'sentiment_score': sentiment_score,
            'news_count': news_count
        }])

        df.to_sql('news_analysis', self.engine, if_exists='append', index=False)
        return True
    except Exception as e:
        logger.error(f"Error saving sentiment analysis for {stock_code}: {e}")
        return False
```

## ProphetForecast 모델

### 테이블 스키마

```python
class ProphetForecast(Base):
    __tablename__ = 'prophet_forecast'

    stock_code = Column(String(10), primary_key=True)
    stock_name = Column(String(50), nullable=True)
    forecast_date = Column(Date, primary_key=True)

    # D+1 to D+5 예측값
    yhat_d1 = Column(Numeric(12, 2), nullable=True)
    yhat_d2 = Column(Numeric(12, 2), nullable=True)
    yhat_d3 = Column(Numeric(12, 2), nullable=True)
    yhat_d4 = Column(Numeric(12, 2), nullable=True)
    yhat_d5 = Column(Numeric(12, 2), nullable=True)

    # 신뢰구간 상한
    yhat_upper_d1 = Column(Numeric(12, 2), nullable=True)
    yhat_upper_d2 = Column(Numeric(12, 2), nullable=True)
    yhat_upper_d3 = Column(Numeric(12, 2), nullable=True)
    yhat_upper_d4 = Column(Numeric(12, 2), nullable=True)
    yhat_upper_d5 = Column(Numeric(12, 2), nullable=True)

    # 신뢰구간 하한
    yhat_lower_d1 = Column(Numeric(12, 2), nullable=True)
    yhat_lower_d2 = Column(Numeric(12, 2), nullable=True)
    yhat_lower_d3 = Column(Numeric(12, 2), nullable=True)
    yhat_lower_d4 = Column(Numeric(12, 2), nullable=True)
    yhat_lower_d5 = Column(Numeric(12, 2), nullable=True)

    # 추세 피처 (Gemini AI 입력용)
    price_trend = Column(Numeric(12, 6), nullable=True)
    volume_trend = Column(Numeric(12, 6), nullable=True)
    price_uncertainty = Column(Numeric(10, 2), nullable=True)

    created_at = Column(DateTime, default=datetime.now)
```

### 컬럼명 규칙

| 용도 | 컬럼명 | 타입 |
|------|--------|------|
| 기본키 | `forecast_date` | DATE |
| 예측값 | `yhat_d1~d5` | NUMERIC(12, 2) |
| 추세 | `price_trend`, `volume_trend` | NUMERIC(12, 6) |
| 불확실성 | `price_uncertainty` | NUMERIC(10, 2) |

## Prophet 예측 저장 프로세스

### Clamping (값 제한) 메커니즘

DB 컬럼의 NUMERIC 정밀도를 초과하는 값을 방지하기 위해 clamping을 적용합니다.

```python
def clamp_value(value, max_val, min_val=None):
    """DB 컬럼 범위 내로 값 제한"""
    if value is None:
        return None
    if min_val is not None:
        value = max(min_val, value)
    return min(max_val, value)
```

### DB 컬럼 제한값

| 컬럼 | NUMERIC 타입 | 최대값 |
|------|-------------|--------|
| `yhat_d1~d5`, `yhat_upper`, `yhat_lower` | NUMERIC(12, 2) | 9,999,999,999.99 |
| `price_trend`, `volume_trend` | NUMERIC(12, 6) | 9,999.999999 |
| `price_uncertainty` | NUMERIC(10, 2) | 999,999.99 |

### 저장 함수

```python
def save_prophet_forecast_detailed(self, forecast_data: Dict[str, Any], trade_date: date) -> bool:
    session = self.session_factory()
    try:
        stock_code = forecast_data['stock_code']

        # 기존 레코드 삭제 (UPSERT 패턴)
        session.query(ProphetForecast).filter(
            ProphetForecast.stock_code == stock_code,
            ProphetForecast.forecast_date == trade_date
        ).delete()

        # 값 제한 적용
        price_trend_val = clamp_value(
            forecast_data.get('prophet_price_trend', 0.0),
            9999.0, -9999.0
        )
        volume_trend_val = clamp_value(
            forecast_data.get('prophet_volume_trend', 0.0),
            9999.0, -9999.0
        )
        uncertainty_val = clamp_value(
            forecast_data.get('prophet_price_uncertainty', 0.0),
            999999.0, 0.0
        )

        # 레코드 생성
        record = ProphetForecast(
            stock_code=stock_code,
            stock_name=forecast_data.get('stock_name', stock_code),
            forecast_date=trade_date,
            price_trend=price_trend_val,
            volume_trend=volume_trend_val,
            price_uncertainty=uncertainty_val,
            yhat_d1=clamp_value(forecast_data.get('yhat_price_d1'), 9999999999.99, 0.0),
            yhat_d2=clamp_value(forecast_data.get('yhat_price_d2'), 9999999999.99, 0.0),
            # ... (d3, d4, d5 동일)
            yhat_lower_d1=clamp_value(forecast_data.get('yhat_price_lower_d1'), 9999999999.99, 0.0),
            # ... (lower d2-d5)
            yhat_upper_d1=clamp_value(forecast_data.get('yhat_price_upper_d1'), 9999999999.99, 0.0),
            # ... (upper d2-d5)
        )

        session.add(record)
        session.commit()
        return True
    except SQLAlchemyError as e:
        logger.error(f"Database error while saving Prophet forecast: {e}")
        session.rollback()
        return False
    finally:
        session.close()
```

## Orchestrator 통합

파이프라인에서 저장 함수를 호출할 때 `conn` 파라미터를 전달하지 않습니다 (Repository가 자체적으로 세션 관리).

```python
# Stage 2-2: Sentiment Analysis
self.repo.save_sentiment_analysis(
    stock_code,
    analysis_date,
    sentiment_score,
    news_count
)

# Stage 2-3: Time-Series Forecast
self.repo.save_prophet_forecast_detailed(
    forecast_data,
    trade_date
)
```

## 데이터 검증

### 검증 스크립트

```bash
python _claude/verify_db_data.py
```

### 출력 예시

```
================================================================================
데이터베이스 검증 (2026-06-07)
================================================================================

📰 news_analysis (최근 5일):
  2026-06-05: 30 records
  2026-06-01: 30 records

📈 prophet_forecast (최근 5일):
  2026-06-05: 30 records
  2026-06-01: 24 records

🎯 stock_filter_score (최근 5일):
  2026-06-04: 30 records
  2026-06-03: 30 records
================================================================================
```

### 파이프라인 로그

정상 동작 시 로그:

```
2026-06-07 01:00:00 - pipeline.orchestrator - INFO - [Stage 2-2] Sentiment analysis complete: 30 stocks
2026-06-07 01:00:00 - pipeline.orchestrator - INFO - Saved 30 sentiment records to news_analysis table
2026-06-07 01:00:05 - pipeline.orchestrator - INFO - [Stage 2-3] Time-series analysis complete: 30 stocks
2026-06-07 01:00:05 - pipeline.orchestrator - INFO - Saved 30 time-series records to prophet_forecast table
```

## 파일 위치

| 파일 | 경로 | 역할 |
|------|------|------|
| 모델 정의 | `database/models.py:56-87` | ProphetForecast 클래스 |
| Repository | `database/repository.py:19-21, 224-257, 318-368` | 저장 로직 |
| Orchestrator | `pipeline/orchestrator.py:296-303, 338, 368` | 저장 호출 |
| 검증 스크립트 | `_claude/verify_db_data.py` | DB 데이터 확인 |

## 성능

| 작업 | 처리량 | 예상 시간 |
|------|--------|-----------|
| `news_analysis` 저장 | 30건 INSERT | < 1초 |
| `prophet_forecast` 저장 | 30건 UPSERT (DELETE + INSERT) | < 2초 |

## 관련 문서

- [Database Schema](../database/schema.sql)
- [Pipeline Architecture](../CLAUDE.md)
