# Database Save Implementation

AI 파이프라인 Stage 2 (분석 단계)의 `news_analysis`와 `prophet_forecast` 테이블 저장 구현 문서.

## 파이프라인 분석 데이터 테이블 현황

### Stage별 데이터 흐름

```
┌──────────────────────────────────────────────────────────────────┐
│ Stage 1: Stock Filtering (KOSPI 100 → Top 30)                   │
│ 테이블: stock_filter_score                                       │
│ 저장: 매일 30개 종목 × 5개 지표                                  │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ Stage 2-1: Quantitative Analysis                                │
│ 테이블: stock_filter_score (UPDATE)                             │
│ 저장: 30개 종목 × 2개 추가 컬럼 (morning_return, close_position) │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ Stage 2-2: Sentiment Analysis (KR-FinBERT)                      │
│ 테이블: news_analysis                                            │
│ 저장: 매일 30개 종목 × 감성점수                                  │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ Stage 2-3: Time-Series Forecasting (Prophet)                    │
│ 테이블: prophet_forecast                                         │
│ 저장: 매일 30개 종목 × D+1~D+5 예측 + 추세 피처                 │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ Stage 4: AI Decision (Gemini)                                   │
│ 테이블: ai_trade_decision                                        │
│ 저장: 매일 TOP3 매수 + TOP3 매도 (6개 레코드)                    │
└──────────────────────────────────────────────────────────────────┘
```

### 테이블별 상세 정보

| 테이블명 | Stage | 용도 | 주요 컬럼 | 저장 주기 | 레코드 수/일 |
|---------|-------|------|-----------|----------|--------------|
| **stock_filter_score** | 1, 2-1 | 종목 필터링 점수 + 정량 피처 | `stock_code`, `score_date`, `scaler_score`, `is_selected`, `morning_return`, `close_position` | 매일 | 30개 |
| **news_analysis** | 2-2 | 뉴스 감성 분석 결과 | `stock_code`, `analysis_date`, `sentiment_score`, `news_count` | 매일 | 30개 |
| **prophet_forecast** | 2-3 | Prophet 시계열 예측 | `stock_code`, `forecast_date`, `yhat_d1~d5`, `price_trend`, `volume_trend`, `price_uncertainty` | 매일 | 30개 |
| **ai_trade_decision** | 4 | Gemini AI 매매 결정 | `stock_code`, `trade_date`, `decision_type` (BUY/SELL), `reason`, `rank` | 매일 | 6개 (TOP3×2) |

### API 서버 연동 가이드

#### 1. stock_filter_score (Stage 1 + 2-1)

**데이터 구조:**
```sql
CREATE TABLE stock_filter_score (
    id BIGSERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50) NOT NULL,
    score_date DATE NOT NULL,

    -- Stage 1: 필터링 지표 (KIS API)
    foreign_net_buy BIGINT NOT NULL,
    institutional_net_buy BIGINT NOT NULL,
    vol_avg_multiple NUMERIC(10, 2) NOT NULL,
    price_volatility NUMERIC(10, 4) NOT NULL,
    scaler_score NUMERIC(10, 4) NOT NULL,
    is_selected BOOLEAN NOT NULL,

    -- Stage 2-1: 정량 피처 (KIS API)
    morning_return NUMERIC(10, 4),
    close_position NUMERIC(5, 4),

    created_at TIMESTAMP DEFAULT NOW()
);
```

**API 활용:**
- `GET /api/stocks/filtered?date=2026-06-07` → Top 30 종목 조회
- `GET /api/analysis/quantitative?stock_code=005930&date=2026-06-07` → 정량 지표 조회

**Gemini 입력 피처:** `morning_return`, `close_position`

---

#### 2. news_analysis (Stage 2-2)

**데이터 구조:**
```sql
CREATE TABLE news_analysis (
    stock_code VARCHAR(10) NOT NULL,
    analysis_date DATE NOT NULL,
    sentiment_score NUMERIC(5, 4) NOT NULL,  -- -1.0000 ~ 1.0000
    news_count INT NOT NULL,
    PRIMARY KEY (stock_code, analysis_date)
);
```

**API 활용:**
- `GET /api/analysis/sentiment?date=2026-06-07` → 30개 종목 감성점수
- `GET /api/analysis/sentiment/{stock_code}?date=2026-06-07` → 특정 종목 감성

**Gemini 입력 피처:** `sentiment_score`

---

#### 3. prophet_forecast (Stage 2-3)

**데이터 구조:**
```sql
CREATE TABLE prophet_forecast (
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50),
    forecast_date DATE NOT NULL,

    -- D+1 ~ D+5 예측값
    yhat_d1 NUMERIC(12, 2),
    yhat_d2 NUMERIC(12, 2),
    yhat_d3 NUMERIC(12, 2),
    yhat_d4 NUMERIC(12, 2),
    yhat_d5 NUMERIC(12, 2),

    -- 신뢰구간 상한
    yhat_upper_d1 NUMERIC(12, 2),
    yhat_upper_d2 NUMERIC(12, 2),
    yhat_upper_d3 NUMERIC(12, 2),
    yhat_upper_d4 NUMERIC(12, 2),
    yhat_upper_d5 NUMERIC(12, 2),

    -- 신뢰구간 하한
    yhat_lower_d1 NUMERIC(12, 2),
    yhat_lower_d2 NUMERIC(12, 2),
    yhat_lower_d3 NUMERIC(12, 2),
    yhat_lower_d4 NUMERIC(12, 2),
    yhat_lower_d5 NUMERIC(12, 2),

    -- Gemini AI 입력 피처 (추세 요약)
    price_trend NUMERIC(12, 6),        -- D+1~D+5 가격 추세 기울기
    volume_trend NUMERIC(12, 6),       -- D+1~D+5 거래량 추세 기울기
    price_uncertainty NUMERIC(10, 2),  -- 예측 불확실성 (신뢰구간 평균)

    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (stock_code, forecast_date)
);
```

**API 활용:**
- `GET /api/analysis/forecast?date=2026-06-07` → 30개 종목 예측
- `GET /api/analysis/forecast/{stock_code}?date=2026-06-07` → 차트용 D+1~D+5 데이터

**Gemini 입력 피처:** `price_trend`, `volume_trend`, `price_uncertainty`

**웹 차트 활용:**
- `yhat_d1~d5`: 예측 가격 라인
- `yhat_upper_d1~d5`: 신뢰구간 상한 (area fill)
- `yhat_lower_d1~d5`: 신뢰구간 하한 (area fill)

---

#### 4. ai_trade_decision (Stage 4)

**데이터 구조:**
```sql
CREATE TABLE ai_trade_decision (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    decision_type VARCHAR(4) NOT NULL,  -- 'BUY' or 'SELL'
    reason TEXT NOT NULL,
    rank INT NOT NULL,                  -- 1, 2, 3 (TOP3)
    created_at TIMESTAMP DEFAULT NOW()
);
```

**API 활용:**
- `GET /api/ai/decisions?date=2026-06-07` → 당일 AI 결정 (6개)
- `GET /api/ai/decisions/buy?date=2026-06-07` → TOP3 매수 추천
- `GET /api/ai/decisions/sell?date=2026-06-07` → TOP3 매도 추천

**응답 예시:**
```json
{
  "buy_top3": [
    {
      "stock_code": "005930",
      "rank": 1,
      "reason": "외국인·기관 동시 순매수 + 가격 상승 추세 + 긍정 뉴스"
    }
  ],
  "sell_top3": [...]
}
```

---

### Gemini AI 입력 피처 요약 (11개)

| 피처명 | 출처 테이블 | 타입 | 설명 |
|--------|------------|------|------|
| `morning_return` | stock_filter_score | NUMERIC(10, 4) | 장초반 수익률 (09:00~10:00) |
| `close_position` | stock_filter_score | NUMERIC(5, 4) | 종가 위치 (고저 범위 내) |
| `foreign_net_buy` | stock_filter_score | BIGINT | 외국인 순매수 (원) |
| `institutional_net_buy` | stock_filter_score | BIGINT | 기관 순매수 (원) |
| `per` | stock_financial (DART) | NUMERIC | 주가수익비율 |
| `roe` | stock_financial (DART) | NUMERIC | 자기자본이익률 (%) |
| `operating_margin` | stock_financial (DART) | NUMERIC | 영업이익률 (%) |
| `sentiment_score` | news_analysis | NUMERIC(5, 4) | 뉴스 감성점수 (-1.0 ~ 1.0) |
| `price_trend` | prophet_forecast | NUMERIC(12, 6) | D+1~D+5 가격 추세 |
| `volume_trend` | prophet_forecast | NUMERIC(12, 6) | D+1~D+5 거래량 추세 |
| `price_uncertainty` | prophet_forecast | NUMERIC(10, 2) | 예측 불확실성 |

---

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
