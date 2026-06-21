_# AI Agent Database Tables

AI 파이프라인이 데이터를 저장하는 모든 테이블 현황 및 상세 정보.

## 📋 전체 테이블 목록 (7개)

| # | 테이블명 | Stage | 용도 | 저장 주기 | 레코드 수/일 |
|---|---------|-------|------|----------|--------------|
| 1 | **stock_filter_score** | 1, 2-1-B | 종목 필터링 점수 + KIS 정량 피처 | 매일 | 30개 |
| 2 | **market_daily_summary** | 1 | KOSPI 지수 및 시장 요약 | 매일 | 1개 |
| 3 | **stock_financial** | 2-1-A | DART 재무제표 (PER, ROE 등) | 분기별 | 30개 |
| 4 | **news_analysis** | 2-2 | 뉴스 감성 분석 결과 | 매일 | 30개 |
| 5 | **prophet_forecast** | 2-3 | Prophet 시계열 예측 | 매일 | 30개 |
| 6 | **ai_trade_decision** | 4 | Gemini AI 매매 결정 | 매일 | 6개 (TOP3×2) |
| 7 | **safety_filter_result** | 5 | 안전 필터 검증 결과 | 매일 | 6개 |

---

## 🔄 Stage별 데이터 흐름

```
┌──────────────────────────────────────────────────────────────────┐
│ Stage 1: Stock Filtering (KOSPI 100 → Top 30)                   │
│ 테이블: stock_filter_score, market_daily_summary               │
│ 저장: 30개 종목 점수 + KOSPI 지수 1개                           │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ Stage 2-1-A: DART Financials                                    │
│ 테이블: stock_financial                                          │
│ 저장: 30개 종목 × DART 재무지표 (PER, ROE, 영업이익률)          │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ Stage 2-1-B: KIS Quantitative Features                          │
│ 테이블: stock_filter_score (UPDATE)                             │
│ 저장: 30개 종목 × 2개 추가 컬럼 (morning_return, close_position) │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ Stage 2-2: Sentiment Analysis (KR-FinBERT)                      │
│ 테이블: news_analysis                                            │
│ 저장: 30개 종목 × 감성점수                                        │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ Stage 2-3: Time-Series Forecasting (Prophet)                    │
│ 테이블: prophet_forecast                                         │
│ 저장: 30개 종목 × D+1~D+5 예측 + 추세 피처                       │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ Stage 4: AI Decision (Gemini)                                   │
│ 테이블: ai_trade_decision                                        │
│ 저장: TOP3 매수 + TOP3 매도 (6개 레코드)                         │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ Stage 5: Safety Filter                                          │
│ 테이블: safety_filter_result                                     │
│ 저장: 6개 종목 안전성 검증 결과                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📊 테이블 상세 정보

### 1. stock_filter_score (Stage 1 + 2-1-B)

**용도**: KOSPI 100 → Top 30 필터링 점수 + KIS 정량적 피처 저장

**테이블 스키마**:
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

    -- Stage 2-1-B: KIS 정량 피처
    morning_return NUMERIC(10, 4),
    close_position NUMERIC(5, 4),

    created_at TIMESTAMP DEFAULT NOW()
);
```

**주요 컬럼**:
- `foreign_net_buy`: 외국인 순매수 금액 (원)
- `institutional_net_buy`: 기관 순매수 금액 (원)
- `vol_avg_multiple`: 거래량 배율 (20일 평균 대비)
- `price_volatility`: 가격 변동성 ((고가-저가)/저가)
- `scaler_score`: StandardScaler 정규화 후 가중합산 점수
- `is_selected`: Top 30 선정 여부
- `morning_return`: 장초반 수익률 (09:00~10:00)
- `close_position`: 종가 위치 (0.0~1.0, 고저 범위 내)

**API 엔드포인트 예시**:
- `GET /api/stocks/filtered?date=2026-06-07` → Top 30 종목 조회
- `GET /api/analysis/quantitative?stock_code=005930&date=2026-06-07` → 정량 지표 조회

**Gemini 입력 피처**: `morning_return`, `close_position`, `foreign_net_buy`, `institutional_net_buy` (4개)

**저장 주기**: 매일 30개 종목 (Stage 1 INSERT → Stage 2-1-B UPDATE)

---

### 2. market_daily_summary (Stage 1)

**용도**: KOSPI 지수 및 시장 전반 요약 데이터 저장 (웹 대시보드 표시용)

**테이블 스키마**:
```sql
CREATE TABLE market_daily_summary (
    trade_date DATE PRIMARY KEY,
    kospi_index NUMERIC(10, 2) NOT NULL,
    kospi_change_rate NUMERIC(8, 4) NOT NULL,
    kospi_volume BIGINT NOT NULL,
    kospi_trade_value BIGINT NOT NULL,  -- in million KRW
    created_at TIMESTAMP DEFAULT NOW()
);
```

**주요 컬럼**:
- `kospi_index`: KOSPI 지수 (예: 2650.47)
- `kospi_change_rate`: KOSPI 등락률 (%) (예: -0.0123 = -1.23%)
- `kospi_volume`: KOSPI 거래량
- `kospi_trade_value`: KOSPI 거래대금 (백만원 단위)

**API 엔드포인트 예시**:
- `GET /api/market/summary?date=2026-06-07` → 당일 시장 요약
- `GET /api/market/summary/latest` → 최신 시장 데이터

**저장 주기**: 매일 1개 레코드 (KOSPI 종합지수 데이터)

---

### 3. stock_financial (Stage 2-1-A)

**용도**: DART API로 수집한 분기 재무제표 데이터 저장 (PER, ROE, 영업이익률)

**테이블 스키마**:
```sql
CREATE TABLE stock_financial (
    id BIGSERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50) NOT NULL,
    base_date DATE NOT NULL,           -- 분기 기준일 (예: 2025-09-30)
    per NUMERIC(10, 2),                -- 주가수익비율
    roe NUMERIC(10, 2),                -- 자기자본이익률 (%)
    operating_margin NUMERIC(10, 2),   -- 영업이익률 (%)
    created_at TIMESTAMP NOT NULL
);
```

**주요 컬럼**:
- `base_date`: 분기 재무제표 기준일 (예: 2025-09-30 = 3분기)
- `per`: 주가수익비율 (Price-to-Earnings Ratio) - 낮을수록 저평가
- `roe`: 자기자본이익률 (Return on Equity, %) - 높을수록 수익성 우수
- `operating_margin`: 영업이익률 (%) - 높을수록 본업 수익성 안정

**API 엔드포인트 예시**:
- `GET /api/financials?date=2026-06-07` → 최신 분기 재무지표 (30개 종목)
- `GET /api/financials/{stock_code}?base_date=2025-09-30` → 특정 종목 재무지표

**Gemini 입력 피처**: `per`, `roe`, `operating_margin` (3개)

**저장 주기**: 분기별 (DART API 기준, 매일 파이프라인은 최신 분기 데이터 사용)

**데이터 출처**: DART (전자공시시스템) API

---

### 4. news_analysis (Stage 2-2)

**용도**: KR-FinBERT 기반 종목별 뉴스 감성 분석 결과 저장

**테이블 스키마**:
```sql
CREATE TABLE news_analysis (
    stock_code VARCHAR(10) NOT NULL,
    analysis_date DATE NOT NULL,
    sentiment_score NUMERIC(5, 4) NOT NULL,  -- -1.0000 ~ 1.0000
    news_count INT NOT NULL,
    PRIMARY KEY (stock_code, analysis_date)
);
```

**주요 컬럼**:
- `sentiment_score`: 감성 점수 (-1.0 = 매우 부정, 0.0 = 중립, 1.0 = 매우 긍정)
- `news_count`: 분석에 사용된 뉴스 기사 수

**API 엔드포인트 예시**:
- `GET /api/analysis/sentiment?date=2026-06-07` → 30개 종목 감성점수
- `GET /api/analysis/sentiment/{stock_code}?date=2026-06-07` → 특정 종목 감성

**Gemini 입력 피처**: `sentiment_score` (1개)

**저장 주기**: 매일 30개 종목

**데이터 출처**:
- Track 1 (시장 전반): RSS 피드 (한경, 매경, 연합뉴스)
- Track 2 (종목별): 네이버 금융 뉴스 크롤링 (종목당 최대 5건)

---

### 5. prophet_forecast (Stage 2-3)

**용도**: Prophet 기반 D+1~D+5 가격/거래량 예측 및 추세 피처 저장

**테이블 스키마**:
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

**주요 컬럼**:
- `yhat_d1~d5`: D+1~D+5 예측 가격
- `yhat_upper_d1~d5`: 신뢰구간 상한 (95% CI)
- `yhat_lower_d1~d5`: 신뢰구간 하한 (95% CI)
- `price_trend`: 가격 추세 기울기 (Linear Regression slope)
- `volume_trend`: 거래량 추세 기울기 (매수 비율 기준)
- `price_uncertainty`: 예측 불확실성 (CI 평균 너비)

**API 엔드포인트 예시**:
- `GET /api/analysis/forecast?date=2026-06-07` → 30개 종목 예측
- `GET /api/analysis/forecast/{stock_code}?date=2026-06-07` → 차트용 D+1~D+5 데이터

**Gemini 입력 피처**: `price_trend`, `volume_trend`, `price_uncertainty` (3개)

**웹 차트 활용**:
- `yhat_d1~d5`: 예측 가격 라인
- `yhat_upper_d1~d5`: 신뢰구간 상한 (area fill)
- `yhat_lower_d1~d5`: 신뢰구간 하한 (area fill)

**저장 주기**: 매일 30개 종목

**학습 데이터**: 120 거래일 (OHLCV + 분봉 매수 비율)

---

### 6. ai_trade_decision (Stage 4)

**용도**: Gemini AI의 매수/매도 TOP3 결정 및 근거 저장

**테이블 스키마**:
```sql
CREATE TABLE ai_trade_decision (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50) NOT NULL,
    decision_date DATE NOT NULL,
    decision VARCHAR(4) NOT NULL,  -- 'BUY' or 'SELL'
    reason TEXT NOT NULL,
    rank INT NOT NULL,              -- 1, 2, 3 (TOP3)
    created_at TIMESTAMP DEFAULT NOW()
);
```

**주요 컬럼**:
- `decision`: 매매 결정 ('BUY' 또는 'SELL')
- `reason`: Gemini AI의 결정 근거 (텍스트)
- `rank`: 우선순위 (1=가장 추천, 2, 3)

**API 엔드포인트 예시**:
- `GET /api/ai/decisions?date=2026-06-07` → 당일 AI 결정 (6개)
- `GET /api/ai/decisions/buy?date=2026-06-07` → TOP3 매수 추천
- `GET /api/ai/decisions/sell?date=2026-06-07` → TOP3 매도 추천

**응답 예시**:
```json
{
  "buy_top3": [
    {
      "stock_code": "005930",
      "stock_name": "삼성전자",
      "rank": 1,
      "reason": "외국인·기관 동시 순매수 + 가격 상승 추세 + 긍정 뉴스 + ROE 우수"
    }
  ],
  "sell_top3": [...]
}
```

**저장 주기**: 매일 6개 레코드 (매수 3개 + 매도 3개)

**입력 피처**: 11개 (stock_filter_score 4개 + stock_financial 3개 + news_analysis 1개 + prophet_forecast 3개)

---

### 7. safety_filter_result (Stage 5)

**용도**: AI 결정 종목에 대한 안전성 검증 결과 저장 (손절, 집중도, 가격 변동성 등)

**테이블 스키마**:
```sql
CREATE TABLE safety_filter_result (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50),
    filter_date DATE NOT NULL,
    passed BOOLEAN NOT NULL,
    failure_reason TEXT,
    max_quantity INT,
    current_price NUMERIC(12, 2),
    filter_checks JSONB,  -- 상세 검증 항목별 결과
    created_at TIMESTAMP DEFAULT NOW()
);
```

**주요 컬럼**:
- `passed`: 안전 필터 통과 여부 (true/false)
- `failure_reason`: 실패 시 원인 (예: "손절가 위반", "집중도 초과")
- `max_quantity`: 매수 가능 최대 수량
- `current_price`: 검증 시점 현재가
- `filter_checks`: 상세 검증 항목 (JSON)

**filter_checks 예시**:
```json
{
  "stop_loss_check": true,
  "concentration_check": false,
  "volatility_check": true,
  "liquidity_check": true
}
```

**API 엔드포인트 예시**:
- `GET /api/safety/results?date=2026-06-07` → 당일 안전 필터 결과
- `GET /api/safety/results/{stock_code}?date=2026-06-07` → 특정 종목 검증 결과

**저장 주기**: 매일 6개 레코드 (ai_trade_decision 6개 종목 검증)

---

## 🎯 Gemini AI 입력 피처 요약 (11개)

| 피처명 | 출처 테이블 | 타입 | 설명 |
|--------|------------|------|------|
| `morning_return` | stock_filter_score | NUMERIC(10, 4) | 장초반 수익률 (09:00~10:00) |
| `close_position` | stock_filter_score | NUMERIC(5, 4) | 종가 위치 (고저 범위 내) |
| `foreign_net_buy` | stock_filter_score | BIGINT | 외국인 순매수 (원) |
| `institutional_net_buy` | stock_filter_score | BIGINT | 기관 순매수 (원) |
| `per` | stock_financial | NUMERIC(10, 2) | 주가수익비율 |
| `roe` | stock_financial | NUMERIC(10, 2) | 자기자본이익률 (%) |
| `operating_margin` | stock_financial | NUMERIC(10, 2) | 영업이익률 (%) |
| `sentiment_score` | news_analysis | NUMERIC(5, 4) | 뉴스 감성점수 (-1.0 ~ 1.0) |
| `price_trend` | prophet_forecast | NUMERIC(12, 6) | D+1~D+5 가격 추세 |
| `volume_trend` | prophet_forecast | NUMERIC(12, 6) | D+1~D+5 거래량 추세 |
| `price_uncertainty` | prophet_forecast | NUMERIC(10, 2) | 예측 불확실성 |

---

## 📝 구현 상세

### DatabaseRepository 초기화

```python
class DatabaseRepository:
    def __init__(self):
        self.session_factory = SessionLocal
        self.engine = engine  # pandas to_sql() 작업에 필요
```

### 저장 메서드 목록

| 메서드 | 테이블 | Stage | 설명 |
|--------|--------|-------|------|
| `save_filter_scores()` | stock_filter_score | 1 | 필터링 점수 bulk insert |
| `save_quantitative_features()` | stock_filter_score | 2-1-B | KIS 정량 피처 UPDATE |
| `save_kospi_index()` | market_daily_summary | 1 | KOSPI 지수 저장 |
| `dart_client.save_to_database()` | stock_financial | 2-1-A | DART 재무제표 저장 |
| `save_sentiment_analysis()` | news_analysis | 2-2 | 감성 분석 결과 |
| `save_prophet_forecast_detailed()` | prophet_forecast | 2-3 | Prophet 예측 전체 |
| `save_ai_decisions()` | ai_trade_decision | 4 | AI 매매 결정 |
| `save_safety_filter_results()` | safety_filter_result | 5 | 안전 필터 결과 |

### Prophet 예측 저장 프로세스

**Clamping (값 제한) 메커니즘**:

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

**DB 컬럼 제한값**:

| 컬럼 | NUMERIC 타입 | 최대값 |
|------|-------------|--------|
| `yhat_d1~d5`, `yhat_upper`, `yhat_lower` | NUMERIC(12, 2) | 9,999,999,999.99 |
| `price_trend`, `volume_trend` | NUMERIC(12, 6) | 9,999.999999 |
| `price_uncertainty` | NUMERIC(10, 2) | 999,999.99 |

**저장 함수**:

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
        # ... (volume_trend, uncertainty도 동일)

        # 레코드 생성
        record = ProphetForecast(
            stock_code=stock_code,
            stock_name=forecast_data.get('stock_name', stock_code),
            forecast_date=trade_date,
            price_trend=price_trend_val,
            volume_trend=volume_trend_val,
            price_uncertainty=uncertainty_val,
            yhat_d1=clamp_value(forecast_data.get('yhat_price_d1'), 9999999999.99, 0.0),
            # ... (d2-d5, upper, lower 동일)
        )

        session.add(record)
        session.commit()
        return True
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        session.rollback()
        return False
    finally:
        session.close()
```

---

## ✅ 데이터 검증

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
2026-06-07 01:00:00 - pipeline.orchestrator - INFO - [Stage 2-1-A] Saved 30 DART financial records
2026-06-07 01:00:00 - pipeline.orchestrator - INFO - [Stage 2-1-B] Saved 30 quantitative records
2026-06-07 01:00:05 - pipeline.orchestrator - INFO - [Stage 2-2] Sentiment analysis complete: 30 stocks
2026-06-07 01:00:05 - pipeline.orchestrator - INFO - Saved 30 sentiment records to news_analysis table
2026-06-07 01:00:10 - pipeline.orchestrator - INFO - [Stage 2-3] Time-series analysis complete: 30 stocks
2026-06-07 01:00:10 - pipeline.orchestrator - INFO - Saved 30 time-series records to prophet_forecast table
```

---

## 📂 파일 위치

| 파일 | 경로 | 역할 |
|------|------|------|
| 모델 정의 | `database/models.py` | SQLAlchemy 모델 클래스 |
| Repository | `database/repository.py` | 저장 로직 (7개 save 메서드) |
| DART Client | `collectors/dart_client.py` | DART API 수집 및 저장 |
| Orchestrator | `pipeline/orchestrator.py` | 저장 호출 |
| 검증 스크립트 | `_claude/verify_db_data.py` | DB 데이터 확인 |

---

## ⚡ 성능

| 작업 | 처리량 | 예상 시간 |
|------|--------|-----------|
| `stock_filter_score` 저장 | 30건 INSERT | < 0.5초 |
| `market_daily_summary` 저장 | 1건 INSERT | < 0.1초 |
| `stock_financial` 저장 | 30건 INSERT | < 0.5초 |
| `news_analysis` 저장 | 30건 INSERT | < 1초 |
| `prophet_forecast` 저장 | 30건 UPSERT (DELETE + INSERT) | < 2초 |
| `ai_trade_decision` 저장 | 6건 INSERT | < 0.5초 |
| `safety_filter_result` 저장 | 6건 INSERT | < 0.5초 |

---

## 🔗 관련 문서

- [Database Schema](../../../database/schema.sql)
- [Pipeline Architecture](../../../CLAUDE.md)_
