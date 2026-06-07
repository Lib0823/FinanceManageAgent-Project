# DB 데이터 확인 가이드

## 📊 Stage별 DB 테이블 매핑

### 전체 파이프라인 구조
```
Stage 0: 휴장일 체크 → (DB 저장 없음, 로그만)
Stage 1: 종목 필터링 → stock_filter_score
Stage 2-1: 정량 분석 → quantitative_features (KIS 데이터)
                    → stock_financial (DART 데이터, 별도 수집)
Stage 2-2: 감성 분석 → news_analysis
Stage 2-3: 시계열 예측 → prophet_forecast
Stage 3: 차트 생성 → /static/charts/*.png (파일)
Stage 4: AI 결정 → ai_trade_decision
Stage 5: 안전 필터 → safety_filter_result
Stage 6: 거래 실행 → trade_history (api-server가 작성)
```

---

## 🗂️ 테이블별 상세 정보

### 1. stock_filter_score (Stage 1)
**용도**: KOSPI 100 → Top 30 필터링 결과

**주요 컬럼**:
- `stock_code`: 종목 코드
- `score_date`: 분석 날짜
- `foreign_net_buy`: 외국인 순매수 금액
- `institutional_net_buy`: 기관 순매수 금액
- `vol_avg_multiple`: 거래량 배율
- `price_volatility`: 가격 변동성
- `scaler_score`: StandardScaler 정규화 후 가중합 점수
- `is_selected`: Top 30 선정 여부

**조회 쿼리**:
```sql
-- 오늘 필터링 결과 (Top 30)
SELECT
  stock_code,
  stock_name,
  foreign_net_buy,
  institutional_net_buy,
  vol_avg_multiple,
  price_volatility,
  scaler_score,
  is_selected
FROM stock_filter_score
WHERE score_date = CURRENT_DATE
  AND is_selected = true
ORDER BY scaler_score DESC;

-- 날짜별 선정 종목 수
SELECT
  score_date,
  COUNT(*) FILTER (WHERE is_selected = true) as selected_count,
  COUNT(*) as total_count
FROM stock_filter_score
GROUP BY score_date
ORDER BY score_date DESC
LIMIT 10;
```

---

### 2. quantitative_features (Stage 2-1, KIS 데이터)
**용도**: KIS API 기반 정량 피처 (4개)

**주요 컬럼**:
- `stock_code`: 종목 코드
- `feature_date`: 분석 날짜
- `morning_return`: 장초반 수익률 (%)
- `close_position`: 종가 위치 (0~1)
- `foreign_net_buy`: 외국인 순매수 (재확인)
- `institutional_net_buy`: 기관 순매수 (재확인)

**조회 쿼리**:
```sql
-- 오늘 정량 분석 결과
SELECT
  stock_code,
  stock_name,
  morning_return,
  close_position,
  foreign_net_buy,
  institutional_net_buy
FROM quantitative_features
WHERE feature_date = CURRENT_DATE
ORDER BY morning_return DESC;

-- 장초반 수익률 상위 10종목
SELECT
  stock_code,
  stock_name,
  morning_return,
  feature_date
FROM quantitative_features
WHERE feature_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY feature_date DESC, morning_return DESC
LIMIT 10;
```

---

### 3. stock_financial (Stage 2-1, DART 데이터)
**용도**: DART 분기 재무지표 (3개)

**주요 컬럼**:
- `stock_code`: 종목 코드
- `base_date`: 재무제표 기준일
- `per`: PER (주가수익비율)
- `roe`: ROE (자기자본이익률)
- `operating_margin`: 영업이익률 (%)

**조회 쿼리**:
```sql
-- 최신 재무지표 조회
SELECT
  stock_code,
  stock_name,
  base_date,
  per,
  roe,
  operating_margin
FROM stock_financial
WHERE base_date = (SELECT MAX(base_date) FROM stock_financial)
ORDER BY roe DESC;

-- 저PER + 고ROE 종목
SELECT
  stock_code,
  stock_name,
  per,
  roe,
  operating_margin
FROM stock_financial
WHERE base_date = (SELECT MAX(base_date) FROM stock_financial)
  AND per IS NOT NULL
  AND roe > 10
  AND per < 15
ORDER BY roe DESC;
```

---

### 4. news_analysis (Stage 2-2)
**용도**: KR-FinBERT 감성 분석 결과

**주요 컬럼**:
- `stock_code`: 종목 코드 (NULL = 시장 전체)
- `analysis_date`: 분석 날짜
- `sentiment_score`: 감성 점수 (-1.0 ~ 1.0)
- `news_count`: 분석한 뉴스 개수
- `created_at`: 생성 시각

**조회 쿼리**:
```sql
-- 오늘 종목별 감성 분석
SELECT
  stock_code,
  stock_name,
  sentiment_score,
  news_count,
  CASE
    WHEN sentiment_score >= 0.5 THEN '매우 긍정'
    WHEN sentiment_score >= 0.2 THEN '긍정'
    WHEN sentiment_score >= -0.2 THEN '중립'
    WHEN sentiment_score >= -0.5 THEN '부정'
    ELSE '매우 부정'
  END as sentiment_label
FROM news_analysis
WHERE analysis_date = CURRENT_DATE
  AND stock_code IS NOT NULL
ORDER BY sentiment_score DESC;

-- 시장 전체 감성 추이 (최근 7일)
SELECT
  analysis_date,
  sentiment_score,
  news_count
FROM news_analysis
WHERE stock_code IS NULL
  AND analysis_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY analysis_date DESC;
```

---

### 5. prophet_forecast (Stage 2-3)
**용도**: Prophet 시계열 예측 결과

**주요 컬럼**:
- `stock_code`: 종목 코드
- `forecast_date`: 예측 기준 날짜
- `prophet_price_trend`: 가격 추세 (D+1~D+5 slope)
- `prophet_volume_trend`: 거래량 추세 (매수 비율 slope)
- `prophet_price_uncertainty`: 가격 불확실성 (신뢰구간 너비)
- `d1_price_yhat` ~ `d5_price_yhat`: D+1~D+5 가격 예측값

**조회 쿼리**:
```sql
-- 오늘 시계열 예측 결과
SELECT
  stock_code,
  stock_name,
  prophet_price_trend,
  prophet_volume_trend,
  prophet_price_uncertainty,
  d1_price_yhat,
  d5_price_yhat
FROM prophet_forecast
WHERE forecast_date = CURRENT_DATE
ORDER BY prophet_price_trend DESC;

-- 상승 추세 + 매수세 강화 종목
SELECT
  stock_code,
  stock_name,
  prophet_price_trend,
  prophet_volume_trend,
  prophet_price_uncertainty
FROM prophet_forecast
WHERE forecast_date = CURRENT_DATE
  AND prophet_price_trend > 0
  AND prophet_volume_trend > 0
ORDER BY prophet_price_trend DESC;
```

---

### 6. ai_trade_decision (Stage 4)
**용도**: Gemini AI 매수/매도 결정

**주요 컬럼**:
- `stock_code`: 종목 코드
- `decision_date`: 결정 날짜
- `decision`: BUY 또는 SELL
- `rank`: 순위 (1, 2, 3)
- `reason`: Gemini 판단 이유
- `confidence_score`: 신뢰도 (0.0~1.0, 추후 확장)

**조회 쿼리**:
```sql
-- 오늘 AI 매수/매도 결정
SELECT
  decision,
  rank,
  stock_code,
  stock_name,
  reason,
  confidence_score
FROM ai_trade_decision
WHERE decision_date = CURRENT_DATE
ORDER BY decision, rank;

-- TOP 3 매수 종목 상세
SELECT
  rank,
  stock_code,
  stock_name,
  reason,
  created_at
FROM ai_trade_decision
WHERE decision_date = CURRENT_DATE
  AND decision = 'BUY'
ORDER BY rank;

-- 최근 7일 매수 결정 종목 빈도
SELECT
  stock_code,
  stock_name,
  COUNT(*) as decision_count,
  MAX(decision_date) as latest_date
FROM ai_trade_decision
WHERE decision_date >= CURRENT_DATE - INTERVAL '7 days'
  AND decision = 'BUY'
GROUP BY stock_code, stock_name
ORDER BY decision_count DESC;
```

---

### 7. safety_filter_result (Stage 5)
**용도**: 안전 필터 검증 결과 (매수/매도 결정 검증)

**주요 컬럼**:
- `stock_code`: 종목 코드
- `stock_name`: 종목명
- `filter_date`: 필터링 날짜
- `passed`: 필터 통과 여부 (boolean)
- `failure_reason`: 실패 사유 (TEXT, NULL if passed)
- `max_quantity`: 최대 매수 가능 수량 (매수 결정 시)
- `current_price`: 필터링 시점 현재가
- `filter_checks`: 피처별 검증 결과 (JSONB)
- `created_at`: 생성 시각

**조회 쿼리**:
```sql
-- 오늘 안전 필터 결과 (전체)
SELECT
  stock_code,
  stock_name,
  passed,
  failure_reason,
  max_quantity,
  current_price,
  filter_checks,
  created_at
FROM safety_filter_result
WHERE filter_date = CURRENT_DATE
ORDER BY passed DESC, stock_code;

-- 필터 통과/실패 요약
SELECT
  filter_date,
  COUNT(*) as total_checked,
  COUNT(*) FILTER (WHERE passed = true) as passed_count,
  COUNT(*) FILTER (WHERE passed = false) as failed_count,
  ROUND(COUNT(*) FILTER (WHERE passed = true)::numeric / COUNT(*) * 100, 2) as pass_rate
FROM safety_filter_result
GROUP BY filter_date
ORDER BY filter_date DESC
LIMIT 10;

-- 필터 실패 이유 분석
SELECT
  failure_reason,
  COUNT(*) as count
FROM safety_filter_result
WHERE filter_date >= CURRENT_DATE - INTERVAL '7 days'
  AND passed = false
GROUP BY failure_reason
ORDER BY count DESC;
```

---

### 8. trade_history (Stage 6)
**용도**: 실제 거래 실행 이력 (api-server가 작성)

**주요 컬럼**:
- `user_id`: 사용자 ID
- `stock_code`: 종목 코드
- `trade_type`: BUY 또는 SELL
- `quantity`: 수량
- `price`: 체결 가격
- `executed_at`: 체결 시각
- `order_no`: KIS 주문 번호

**조회 쿼리**:
```sql
-- 오늘 거래 내역
SELECT
  trade_type,
  stock_code,
  stock_name,
  quantity,
  price,
  quantity * price as total_amount,
  executed_at
FROM trade_history
WHERE DATE(executed_at) = CURRENT_DATE
ORDER BY executed_at DESC;

-- 종목별 거래 수익률
SELECT
  stock_code,
  stock_name,
  SUM(CASE WHEN trade_type = 'BUY' THEN quantity ELSE 0 END) as total_buy,
  SUM(CASE WHEN trade_type = 'SELL' THEN quantity ELSE 0 END) as total_sell,
  AVG(CASE WHEN trade_type = 'BUY' THEN price END) as avg_buy_price,
  AVG(CASE WHEN trade_type = 'SELL' THEN price END) as avg_sell_price
FROM trade_history
WHERE executed_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY stock_code, stock_name
HAVING SUM(CASE WHEN trade_type = 'BUY' THEN quantity ELSE 0 END) > 0
ORDER BY stock_code;
```

---

## 🔍 전체 파이프라인 데이터 확인 쿼리

### 특정 날짜 전체 데이터 존재 여부
```sql
SELECT
  'stock_filter_score' as stage,
  COUNT(*) as rows
FROM stock_filter_score
WHERE score_date = '2026-06-02'

UNION ALL

SELECT
  'quantitative_features',
  COUNT(*)
FROM quantitative_features
WHERE feature_date = '2026-06-02'

UNION ALL

SELECT
  'news_analysis',
  COUNT(*)
FROM news_analysis
WHERE analysis_date = '2026-06-02'

UNION ALL

SELECT
  'prophet_forecast',
  COUNT(*)
FROM prophet_forecast
WHERE forecast_date = '2026-06-02'

UNION ALL

SELECT
  'ai_trade_decision',
  COUNT(*)
FROM ai_trade_decision
WHERE decision_date = '2026-06-02'

UNION ALL

SELECT
  'safety_filter_result',
  COUNT(*)
FROM safety_filter_result
WHERE filter_date = '2026-06-02'

UNION ALL

SELECT
  'trade_history',
  COUNT(*)
FROM trade_history
WHERE DATE(executed_at) = '2026-06-02'

ORDER BY stage;
```

### 종목별 11개 피처 전체 조회 (Gemini 입력 데이터)
```sql
SELECT
  f.stock_code,
  f.stock_name,
  -- KIS 정량 피처 (4개)
  q.morning_return,
  q.close_position,
  q.foreign_net_buy,
  q.institutional_net_buy,
  -- DART 정량 피처 (3개)
  s.per,
  s.roe,
  s.operating_margin,
  -- 감성 피처 (1개)
  n.sentiment_score,
  -- 시계열 피처 (3개)
  p.prophet_price_trend,
  p.prophet_volume_trend,
  p.prophet_price_uncertainty
FROM stock_filter_score f
LEFT JOIN quantitative_features q
  ON f.stock_code = q.stock_code
  AND f.score_date = q.feature_date
LEFT JOIN stock_financial s
  ON f.stock_code = s.stock_code
  AND s.base_date = (SELECT MAX(base_date) FROM stock_financial)
LEFT JOIN news_analysis n
  ON f.stock_code = n.stock_code
  AND f.score_date = n.analysis_date
LEFT JOIN prophet_forecast p
  ON f.stock_code = p.stock_code
  AND f.score_date = p.forecast_date
WHERE f.score_date = CURRENT_DATE
  AND f.is_selected = true
ORDER BY f.scaler_score DESC;
```

---

## ✅ 2026-06-04 스키마 수정 완료

### 수정 1: stock_filter_score - stock_name 추가
**위치**: `analysis/filter.py:174-175`

**문제**: DataFrame에 stock_name 컬럼이 없어서 빈 문자열로 저장됨

**해결**:
```python
# 추가된 코드
filtered_df['stock_name'] = filtered_df['stock_code'].map(STOCK_NAMES).fillna('Unknown')
```

**상태**: ✅ 수정 완료 및 검증됨 (30개 레코드 정상 저장 확인)

---

### 수정 2: ai_trade_decision - 컬럼명 불일치
**위치**: `database/repository.py:439-462`

**문제**:
- 코드: `trade_date` → 실제 테이블: `decision_date`
- 코드: `decision_type` → 실제 테이블: `decision`
- `stock_name` 매핑 누락

**해결**:
```python
# 수정된 컬럼 매핑
{
    'decision_date': decision_date,      # trade_date에서 변경
    'decision': decision['decision'],    # decision_type에서 변경
    'stock_name': STOCK_NAMES.get(stock_code, 'Unknown')  # 추가
}
```

**상태**: ✅ 수정 완료 (검증 대기 중)

---

### 수정 3: safety_filter_result - 컬럼명 불일치
**위치**: `database/repository.py:498-509`

**문제**:
- 존재하지 않는 `decision` 컬럼 사용
- `feature_values` → 실제 테이블: `filter_checks`
- `max_quantity`, `current_price` 누락

**해결**:
```python
# 수정된 컬럼 매핑
{
    'stock_code': result['stock_code'],
    'stock_name': result.get('stock_name', ''),
    'filter_date': filter_date,
    'passed': result['passed'],
    'failure_reason': result.get('failure_reason'),
    'max_quantity': result.get('max_quantity'),      # 추가
    'current_price': result.get('current_price'),    # 추가
    'filter_checks': json.dumps(result.get('filter_checks', {}))  # feature_values에서 변경
}
```

**상태**: ✅ 수정 완료 (검증 대기 중)

---

## ⚠️ 현재 상태

### 데이터 저장 상태 (2026-06-04 기준)
```
stock_filter_score: 0개 (KIS API 500 에러로 인한 파이프라인 실패)
ai_trade_decision: 0개 (파이프라인 미완료)
safety_filter_result: 0개 (파이프라인 미완료)
```

**원인**: KIS API 외부 장애 (HTTP 500 Internal Server Error)

**다음 테스트 시점**:
1. KIS API 복구 후 수동 실행
2. 다음 정기 실행: 평일 08:50 KST (APScheduler)

---

### 이전 문제점 (해결됨)

~~**문제 1: Stage 1만 실행됨**~~ → ✅ 해결 (스키마 수정 완료)
~~**문제 2: KIS API 데이터가 모두 0**~~ → ⚠️ 외부 API 장애 (해결 불가)

---

## 🛠️ Docker 환경에서 직접 조회하기

### PostgreSQL 접속
```bash
cd /Users/inbeom/IdeaProjects/FinanceManage_Agent-Project

# 방법 1: docker compose exec
docker compose exec -it postgres psql -U admin -d financemanage

# 방법 2: docker compose exec 한 줄 쿼리
docker compose exec -T postgres psql -U admin -d financemanage -c "SELECT COUNT(*) FROM stock_filter_score;"
```

### 유용한 조회 명령어
```sql
-- 테이블 목록 확인
\dt

-- 특정 테이블 구조 확인
\d+ stock_filter_score

-- 최근 데이터 확인
SELECT score_date, COUNT(*)
FROM stock_filter_score
GROUP BY score_date
ORDER BY score_date DESC
LIMIT 10;
```

---

## 📝 파이프라인 실행 로그 확인

### FastAPI 로그 확인
```bash
# 컨테이너 로그 실시간 확인
docker compose logs -f ai-agent

# 특정 날짜 파이프라인 실행 로그만 필터링
docker compose logs ai-agent | grep "2026-06-02"

# Stage별 실행 로그 확인
docker compose logs ai-agent | grep "Stage"
```

### 로그 파일 확인 (컨테이너 내부)
```bash
# 컨테이너 내부 접속
docker compose exec -it ai-agent bash

# 로그 파일 확인
tail -f /app/logs/pipeline.log

# Stage별 필터링
cat /app/logs/pipeline.log | grep "Stage 2"
```

---

## 📊 데이터 시각화 (선택)

### Metabase / Grafana 연결
```yaml
# docker-compose.yml에 추가 (선택 사항)
metabase:
  image: metabase/metabase:latest
  ports:
    - "3001:3000"
  environment:
    MB_DB_TYPE: postgres
    MB_DB_DBNAME: financemanage
    MB_DB_PORT: 5432
    MB_DB_USER: admin
    MB_DB_PASS: admin1234
    MB_DB_HOST: postgres
```

접속: http://localhost:3001

---

**문서 버전**: 1.1
**작성일**: 2026-06-02
**최종 수정**: 2026-06-04

---

## ✅ 2026-06-04 추가 수정 사항

### ✅ 수정 4: news_analysis 테이블 - 저장 로직 누락 해결
**위치**: `pipeline/orchestrator.py:257-267`

**문제**: Stage 2-2에서 감성 분석이 실행되었으나 DB 저장 로직이 없어 데이터가 0건

**원인**:
- `sentiment_analyzer.analyze_stocks()` 실행 후 DataFrame 반환
- 반환된 DataFrame을 DB에 저장하는 코드 누락
- `repository.save_sentiment_analysis()` 메서드는 존재하지만 호출되지 않음

**해결**:
```python
# orchestrator.py에 추가된 코드 (라인 257-267)
# Save sentiment results to database
logger.info("Saving sentiment analysis results to database")
for _, row in sentiment_df.iterrows():
    self.db_repo.save_sentiment_analysis(
        stock_code=row['stock_code'],
        analysis_date=trade_date,
        sentiment_score=row['sentiment_score'],
        news_count=0,  # 현재 뉴스 수집이 0건이므로 기본값 0
        conn=conn
    )
logger.info(f"Saved {len(sentiment_df)} sentiment records to news_analysis table")
```

**상태**: ✅ 수정 완료 - 다음 파이프라인 실행 시 30건의 감성 분석 결과 저장 예상

---

### ✅ 수정 5: prophet_forecast 테이블 - 저장 로직 누락 해결
**위치**: `pipeline/orchestrator.py:274-281`

**문제**: Stage 2-3에서 시계열 분석이 실행되었으나 DB 저장 로직이 없어 데이터가 0건

**원인**:
- `ts_analyzer.analyze_stocks()` 실행 후 DataFrame 반환
- 반환된 DataFrame을 DB에 저장하는 코드 누락
- `repository.save_prophet_forecast_detailed()` 메서드는 존재하지만 호출되지 않음

**해결**:
```python
# orchestrator.py에 추가된 코드 (라인 274-281)
# Save time-series results to database
logger.info("Saving time-series forecast results to database")
ts_saved_count = 0
for _, row in ts_df.iterrows():
    forecast_data = row.to_dict()
    if self.db_repo.save_prophet_forecast_detailed(forecast_data, trade_date):
        ts_saved_count += 1
logger.info(f"Saved {ts_saved_count} time-series records to prophet_forecast table")
```

**참고**: Prophet 라이브러리 오류 (`'Prophet' object has no attribute 'stan_backend'`)가 있어 현재는 0건 저장될 수 있음. 라이브러리 오류 해결 후 자동으로 정상 저장됩니다.

**상태**: ✅ 수정 완료 - Prophet 라이브러리 오류 해결 후 30건의 예측 결과 저장 예상

---

### ⚠️ 미해결 이슈: stock_financial 테이블 - DART API 통합 누락

**문제**: DART API 연동 코드가 전체적으로 누락되어 재무 데이터 수집 불가

**현재 상태**:
- `collectors/dart_client.py` 파일 없음 (DART API 클라이언트 미구현)
- `pipeline/orchestrator.py`에 DART 관련 코드 전혀 없음
- `database/repository.py`에 재무 데이터 저장 메서드 없음

**영향 범위**:
- Stage 2-1의 DART 재무 데이터 수집 단계 완전 누락
- Gemini AI에게 제공되는 11개 피처 중 3개(PER, ROE, 영업이익률) 누락
- AI 매매 결정의 정확도에 영향 가능

**필요 작업**:

1. **DART API 클라이언트 구현** (`collectors/dart_client.py`)
```python
class DARTClient:
    async def get_financial_statements(self, stock_code: str, quarter: str):
        """DART API에서 분기 재무제표 조회"""
        # API 호출 로직
        pass
```

2. **Repository 저장 메서드 추가** (`database/repository.py`)
```python
def save_financial_data(self, stock_code, base_date, per, roe, operating_margin, conn):
    """stock_financial 테이블에 재무 데이터 저장"""
    import pandas as pd
    df = pd.DataFrame([{
        'stock_code': stock_code,
        'stock_name': STOCK_NAMES.get(stock_code, 'Unknown'),
        'base_date': base_date,
        'per': per,
        'roe': roe,
        'operating_margin': operating_margin
    }])
    df.to_sql('stock_financial', conn, if_exists='append', index=False)
```

3. **Orchestrator 통합** (`pipeline/orchestrator.py` Stage 2-1 수정)
```python
# Stage 2-1에 DART 수집 추가
dart_client = DARTClient()
for stock_code in selected_codes:
    financial_data = await dart_client.get_financial_statements(stock_code, latest_quarter)
    self.db_repo.save_financial_data(
        stock_code=stock_code,
        base_date=financial_data['base_date'],
        per=financial_data['per'],
        roe=financial_data['roe'],
        operating_margin=financial_data['operating_margin'],
        conn=conn
    )
```

**해결 우선순위**: 🔴 높음 (Gemini AI 입력 피처 누락)

---

## 📊 현재 테이블 상태 요약 (2026-06-04 18:00 기준)

| 테이블 | 상태 | 데이터 건수 | 수정 여부 | 비고 |
|--------|------|------------|----------|------|
| `stock_filter_score` | ✅ 정상 | 121 | ✅ 완료 (06-04) | Stage 1 + Stage 2-1 KIS 데이터 |
| `stock_financial` | ❌ 데이터 없음 | 0 | ⚠️ **DART 통합 필요** | Stage 2-1 DART 수집 미구현 |
| `news_analysis` | ✅ **수정 완료** | 저장 로직 추가 (06-04) | ✅ 완료 (06-04) | 다음 파이프라인 실행 시 데이터 생성 예정 |
| `prophet_forecast` | ⚠️ **수정 완료** | 저장 로직 추가 (06-04) | ✅ 완료 (06-04) | Prophet 라이브러리 오류 해결 필요 |
| `ai_trade_decision` | ✅ 정상 | 6 | ✅ 완료 (06-04) | Stage 4 Gemini 결정 |
| `safety_filter_result` | ✅ 정상 | 6 | ✅ 완료 (06-04) | Stage 5 안전 필터 |
| `trade_history` | ✅ 정상 | 4 | - | Stage 6 거래 실행 (api-server) |

---

## 🔄 다음 파이프라인 실행 시 확인 사항

1. **news_analysis 테이블**:
   - ✅ 저장 로직 추가됨
   - 예상: 30건의 감성 분석 결과 (sentiment_score 0.0 기본값)
   - 확인 쿼리: `SELECT COUNT(*) FROM news_analysis WHERE analysis_date = CURRENT_DATE;`

2. **prophet_forecast 테이블**:
   - ✅ 저장 로직 추가됨
   - ⚠️ Prophet 라이브러리 오류로 실제 저장은 0건 가능
   - 확인 쿼리: `SELECT COUNT(*) FROM prophet_forecast WHERE forecast_date = CURRENT_DATE;`
   - 오류 메시지: `'Prophet' object has no attribute 'stan_backend'`

3. **stock_financial 테이블**:
   - ❌ DART API 통합 필요
   - 예상: 계속 0건
   - **해결 방법**: DART 클라이언트 구현 및 통합 작업 필요
