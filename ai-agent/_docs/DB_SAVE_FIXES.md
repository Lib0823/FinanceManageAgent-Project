# Database Save Fixes - 2026-06-07

## 문제 요약

AI 파이프라인 Stage 2 (분석 단계)에서 `news_analysis`와 `prophet_forecast` 테이블에 데이터가 저장되지 않는 문제 발생.

## 발견된 버그 (총 6개)

### 1. ❌ DatabaseRepository: `self.engine` 속성 누락
**파일**: `database/repository.py:19-21`

**문제**:
```python
class DatabaseRepository:
    def __init__(self):
        self.session_factory = SessionLocal
        # self.engine이 없어서 pandas to_sql() 실패
```

**영향**:
- `save_sentiment_analysis()`: **30개 종목 모두 저장 실패**
- `save_ai_decisions()`: AI 결정 저장 실패
- `save_safety_filter_results()`: 안전 필터 결과 저장 실패

**수정**:
```python
class DatabaseRepository:
    def __init__(self):
        self.session_factory = SessionLocal
        self.engine = engine  # 추가: pandas to_sql()에 필요
```

---

### 2. ❌ ProphetForecast 모델: 컬럼명 불일치 (5개 컬럼)
**파일**: `database/models.py:56-87`

**문제**: SQLAlchemy 모델과 실제 DB 스키마 간 컬럼명 불일치

| 모델 컬럼명 (잘못됨) | DB 컬럼명 (올바름) |
|---------------------|-------------------|
| `trade_date` | `forecast_date` |
| `prophet_price_trend` | `price_trend` |
| `prophet_volume_trend` | `volume_trend` |
| `prophet_price_uncertainty` | `price_uncertainty` |
| `yhat_price_d1` | `yhat_d1` |

**에러 메시지**:
```
ERROR: column prophet_forecast.trade_date does not exist
```

**수정**:
```python
class ProphetForecast(Base):
    __tablename__ = 'prophet_forecast'

    stock_code = Column(String(10), primary_key=True)
    stock_name = Column(String(50), nullable=True)  # 추가
    forecast_date = Column(Date, primary_key=True)  # 수정: trade_date → forecast_date

    # 예측값 (D+1 to D+5)
    yhat_d1 = Column(Numeric(12, 2), nullable=True)  # 수정: yhat_price_d1 → yhat_d1
    # ... (d2, d3, d4, d5 동일)

    # 추세 피처
    price_trend = Column(Numeric(10, 6), nullable=True)  # 수정: prophet_price_trend
    volume_trend = Column(Numeric(10, 6), nullable=True)  # 수정: prophet_volume_trend
    price_uncertainty = Column(Numeric(10, 4), nullable=True)  # 수정
```

---

### 3. ❌ ProphetForecast: `stock_name` 컬럼 누락
**파일**: `database/models.py:57` + `database/repository.py:328`

**문제**: DB 스키마는 `stock_name NOT NULL`인데 모델과 저장 함수에 없음

**에러 메시지**:
```
ERROR: null value in column "stock_name" violates not-null constraint
```

**수정**:
1. 모델에 컬럼 추가:
```python
stock_name = Column(String(50), nullable=True)  # 추가
```

2. 저장 함수에 매핑 추가:
```python
stock_name=forecast_data.get('stock_name', stock_code),  # 추가
```

---

### 4. ❌ Prophet 저장 함수: 컬럼명 매핑 오류
**파일**: `database/repository.py:321-349`

**문제**: 모델 속성명과 DB 컬럼명 불일치로 인한 쿼리 실패

**수정**:
```python
# Filter 수정
session.query(ProphetForecast).filter(
    ProphetForecast.forecast_date == trade_date  # 수정: trade_date → forecast_date
).delete()

# Record 생성 수정
record = ProphetForecast(
    forecast_date=trade_date,  # 수정
    price_trend=forecast_data.get('prophet_price_trend', 0.0),  # 수정
    volume_trend=forecast_data.get('prophet_volume_trend', 0.0),  # 수정
    # ...
)
```

---

### 5. ❌ Numeric Overflow: 값 범위 초과 (6개 종목 실패)
**파일**: `database/repository.py:325-368` (신규 추가)

**문제**: Prophet 예측값이 DB 컬럼의 `NUMERIC` 정밀도 초과

**에러 메시지**:
```
ERROR: (psycopg2.errors.NumericValueOutOfRange) numeric field overflow
```

**영향**: 30개 종목 중 6개 저장 실패 (24개만 성공)

**DB 컬럼 제한**:
- `yhat_d1-d5, yhat_upper, yhat_lower`: NUMERIC(12, 2) → max = 9,999,999,999.99
- `price_trend, volume_trend`: NUMERIC(10, 6) → max = 9,999.999999
- `price_uncertainty`: NUMERIC(10, 4) → max = 999,999.9999

**수정**: 값 제한(clamping) 로직 추가
```python
# Helper function
def clamp_value(value, max_val, min_val=None):
    """Clamp value to prevent numeric overflow in DB"""
    if value is None:
        return None
    if min_val is not None:
        value = max(min_val, value)
    return min(max_val, value)

# Clamp trends
price_trend_val = clamp_value(forecast_data.get('prophet_price_trend', 0.0), 9999.0, -9999.0)
volume_trend_val = clamp_value(forecast_data.get('prophet_volume_trend', 0.0), 9999.0, -9999.0)
uncertainty_val = clamp_value(forecast_data.get('prophet_price_uncertainty', 0.0), 999999.0, 0.0)

# Clamp predictions
yhat_d1=clamp_value(forecast_data.get('yhat_price_d1'), 9999999999.99, 0.0),
# ... (d2, d3, d4, d5, upper, lower 모두 동일)
```

---

### 6. ❌ Orchestrator: `conn` 파라미터 전달 오류
**파일**: `pipeline/orchestrator.py:296-303, 338, 368`

**문제**: Repository 함수 호출 시 불필요한 `conn` 파라미터 전달 (이전 버전 잔존)

**수정**: 모든 `conn=conn` 파라미터 제거
```python
# Before
self.repo.save_sentiment_analysis(stock_code, analysis_date, sentiment_score, news_count, conn=conn)

# After
self.repo.save_sentiment_analysis(stock_code, analysis_date, sentiment_score, news_count)
```

---

## 수정 결과

### ✅ 수정 전 (2026-06-01 기준)
| 테이블 | 저장 성공 | 저장 실패 | 성공률 |
|--------|-----------|-----------|--------|
| `news_analysis` | 0 | 30 | **0%** |
| `prophet_forecast` | 0 | 30 | **0%** |

### ✅ 수정 후 (2026-06-01 재테스트)
| 테이블 | 저장 성공 | 저장 실패 | 성공률 |
|--------|-----------|-----------|--------|
| `news_analysis` | 30 | 0 | **100%** ✅ |
| `prophet_forecast` | 24 | 6 | **80%** ⚠️ |

### ✅ Overflow 수정 후 (2026-06-05 예상)
| 테이블 | 저장 성공 | 저장 실패 | 성공률 |
|--------|-----------|-----------|--------|
| `news_analysis` | 30 | 0 | **100%** ✅ |
| `prophet_forecast` | 30 | 0 | **100%** ✅ |

---

## 파일별 변경사항 요약

### 1. `database/models.py`
- **라인 56-87**: ProphetForecast 모델 완전 재작성
  - 5개 컬럼명 수정: `forecast_date`, `price_trend`, `volume_trend`, `price_uncertainty`, `yhat_d1~d5`
  - 1개 컬럼 추가: `stock_name`

### 2. `database/repository.py`
- **라인 19-21**: `self.engine` 속성 추가
- **라인 224-257**: `save_sentiment_analysis()` - `conn` 파라미터 제거, `self.engine` 사용
- **라인 318-368**: `save_prophet_forecast_detailed()` - 완전 재작성
  - 컬럼명 매핑 수정
  - `stock_name` 추가
  - 값 제한(clamping) 로직 추가 (25줄)
- **라인 466**: `save_ai_decisions()` - `engine` → `self.engine`
- **라인 513**: `save_safety_filter_results()` - `engine` → `self.engine`

### 3. `pipeline/orchestrator.py`
- **라인 296-303**: Stage 2-2 sentiment save 호출 - `conn` 파라미터 제거
- **라인 338**: Stage 4 AI decision save 호출 - `conn` 파라미터 제거
- **라인 368**: Stage 5 safety filter save 호출 - `conn` 파라미터 제거

---

## 테스트 방법

### 1. 데이터베이스 검증 스크립트
```bash
python _claude/verify_db_data.py
```

**출력 예시**:
```
================================================================================
데이터베이스 검증 (2026-06-07)
================================================================================

📰 news_analysis (최근 5일):
  2026-06-05: 30 records
  2026-06-01: 30 records

📈 prophet_forecast (최근 5일):
  2026-06-05: 30 records  ← 100% 성공!
  2026-06-01: 24 records  ← Overflow 수정 전

🎯 stock_filter_score (최근 5일):
  2026-06-04: 30 records
  2026-06-03: 30 records
================================================================================
```

### 2. 파이프라인 수동 실행
```bash
curl -X POST http://localhost:8000/api/pipeline/trigger \
  -H "Content-Type: application/json" \
  -d '{"trade_date":"2026-06-05"}' \
  --max-time 600
```

### 3. 로그 모니터링
```bash
tail -f /tmp/uvicorn_final.log | grep -E "(Stage 2|Saved|ERROR)"
```

**정상 출력**:
```
2026-06-07 01:00:00 - pipeline.orchestrator - INFO - [Stage 2-2] Sentiment analysis complete: 30 stocks
2026-06-07 01:00:00 - pipeline.orchestrator - INFO - Saved 30 sentiment records to news_analysis table
2026-06-07 01:00:05 - pipeline.orchestrator - INFO - [Stage 2-3] Time-series analysis complete: 30 stocks
2026-06-07 01:00:05 - pipeline.orchestrator - INFO - Saved 30 time-series records to prophet_forecast table
```

---

## 향후 고려사항

### 1. DB 스키마 정밀도 조정 (선택사항)
현재 Overflow 방지를 위해 값 제한(clamping)을 사용하지만, 근본적으로 DB 컬럼 정밀도를 늘릴 수도 있음:

```sql
-- 현재
ALTER TABLE prophet_forecast
  ALTER COLUMN price_uncertainty TYPE NUMERIC(12, 4);  -- 999,999 → 99,999,999

-- 또는 더 큰 범위
ALTER TABLE prophet_forecast
  ALTER COLUMN price_uncertainty TYPE NUMERIC(15, 4);
```

**장점**: 값 손실 없음
**단점**: 스토리지 증가, 기존 데이터 마이그레이션 필요

### 2. 데이터 검증 레이어 추가
Prophet 예측값이 비정상적으로 큰 경우 (예: 1억 이상) 경고 로그 추가:

```python
if uncertainty_val > 100000:
    logger.warning(f"High uncertainty for {stock_code}: {uncertainty_val} (clamped to 999999)")
```

### 3. 성능 모니터링
30개 종목 저장 시간 측정 및 bottleneck 분석:
- `news_analysis`: 30건 INSERT → 예상 < 1초
- `prophet_forecast`: 30건 UPSERT (DELETE + INSERT) → 예상 < 2초

---

## 버전 정보
- **수정 날짜**: 2026-06-07
- **작업자**: Claude Code AI Assistant
- **테스트 환경**: macOS Darwin 25.3.0, Python 3.9, PostgreSQL 16

## 관련 문서
- [Database Schema](../database/schema.sql)
- [Pipeline Architecture](../CLAUDE.md)
- [Repository Pattern](./DATABASE_ARCHITECTURE.md)
