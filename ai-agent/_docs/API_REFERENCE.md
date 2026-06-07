# API Reference - Spring Boot API Server 개발 완전 가이드

> **용도**: Spring Boot API Server 개발을 위한 모든 참조 자료 통합
> **대상**: Backend 개발자
> **업데이트**: 2026-06-01

---

## 📚 목차

1. [빠른 시작](#빠른-시작)
2. [데이터베이스 스키마](#데이터베이스-스키마)
3. [API 엔드포인트 및 쿼리](#api-엔드포인트-및-쿼리)
4. [웹 화면 데이터 요구사항](#웹-화면-데이터-요구사항)
5. [중요 주의사항](#중요-주의사항)

---

## 🚀 빠른 시작

### API 엔드포인트 구현 3단계

```
1. DB 스키마 확인 → 이 문서의 "데이터베이스 스키마" 섹션
2. SQL 쿼리 작성 → 이 문서의 "API 엔드포인트 및 쿼리" 섹션
3. Spring Boot Controller 구현 → 아래 예시 코드 참고
```

### Controller 구현 예시

```java
@RestController
@RequestMapping("/api/market")
public class MarketController {

    @Autowired
    private MarketService marketService;

    /**
     * 시장 일일 요약 조회
     * GET /api/market/summary?date=2026-06-01
     */
    @GetMapping("/summary")
    public ResponseEntity<MarketSummaryDto> getMarketSummary(
        @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date
    ) {
        if (date == null) {
            date = LocalDate.now();
        }
        MarketSummaryDto summary = marketService.getMarketSummary(date);
        return ResponseEntity.ok(summary);
    }

    /**
     * 오늘의 AI 매매 결정 조회
     * GET /api/market/decisions
     */
    @GetMapping("/decisions")
    public ResponseEntity<TradeDecisionsDto> getTradeDecisions() {
        TradeDecisionsDto decisions = marketService.getTodayDecisions();
        return ResponseEntity.ok(decisions);
    }
}
```

---

## 🗄️ 데이터베이스 스키마

### 테이블 개요

| 테이블명 | 작성자 | 용도 | 갱신 주기 |
|----------|--------|------|-----------|
| `stock_filter_score` | AI Agent | KOSPI 100 → Top 30 필터링 + 정량 지표 | 매일 08:50 |
| `news_analysis` | AI Agent | 종목별 뉴스 감성 분석 | 매일 08:50 |
| `prophet_forecast` | AI Agent | D+1~D+5 가격/거래량 예측 | 매일 08:50 |
| `ai_trade_decision` | AI Agent | Gemini AI 매매 결정 TOP3 | 매일 08:50 |
| `safety_filter_result` | AI Agent | Safety Filter 검증 결과 | 매일 08:50 |
| `market_daily_summary` | AI Agent | KOSPI 지수 및 시장 요약 | 매일 08:50 |
| `stock_financial` | DART | 분기 재무제표 데이터 | 분기별 (수동) |
| `trade_history` | API Server | KIS API 실제 거래 내역 | 거래 실행 시 |
| `user_holdings` | API Server | 사용자 보유 종목 현황 | 거래 실행 시 |
| `user_trade_config` | API Server | 사용자 자동매매 설정 | 설정 변경 시 |

---

### 핵심 테이블 상세

#### 1. stock_filter_score (가장 중요!)

**Stage 1 필터링 결과 + Stage 2-1 정량 지표**

```sql
CREATE TABLE stock_filter_score (
    id BIGSERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50) NOT NULL,
    score_date DATE NOT NULL,  -- ⚠️ trade_date 아님!

    -- Stage 1: 필터링 지표
    foreign_net_buy BIGINT NOT NULL,           -- 외국인 순매수 (원)
    institutional_net_buy BIGINT NOT NULL,     -- 기관 순매수 (원)
    vol_avg_multiple NUMERIC(10, 2) NOT NULL,  -- ⚠️ volume_ratio 아님!
    price_volatility NUMERIC(10, 4) NOT NULL,  -- (고가-저가)/저가
    scaler_score NUMERIC(10, 4) NOT NULL,      -- ⚠️ final_score 아님!
    is_selected BOOLEAN NOT NULL DEFAULT FALSE, -- Top 30 선정 여부

    -- Stage 2-1: 정량 지표 (나중에 업데이트됨)
    morning_return NUMERIC(10, 4),             -- 장초반 수익률 (%)
    close_position NUMERIC(5, 4),              -- 종가 위치 (0~1)

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE(stock_code, score_date)
);

CREATE INDEX idx_sfs_date_selected ON stock_filter_score(score_date, is_selected);
```

**⚠️ 컬럼명 주의**:
- `score_date` (O) / `trade_date` (X)
- `institutional_net_buy` (O) / `institution_net_buy` (X)
- `vol_avg_multiple` (O) / `volume_ratio` (X)
- `scaler_score` (O) / `final_score` (X)

---

#### 2. prophet_forecast

**Stage 2-3 시계열 예측 결과**

```sql
CREATE TABLE prophet_forecast (
    stock_code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,

    -- 집계 트렌드 (Gemini AI 입력)
    prophet_price_trend NUMERIC(12, 6) NOT NULL,      -- D+1~D+5 가격 추세
    prophet_volume_trend NUMERIC(12, 6) NOT NULL,     -- D+1~D+5 거래량 추세
    prophet_price_uncertainty NUMERIC(10, 2) NOT NULL, -- 예측 불확실성

    -- 상세 예측 (웹 화면 표시용)
    yhat_price_d1 NUMERIC(10, 2),
    yhat_price_d2 NUMERIC(10, 2),
    yhat_price_d3 NUMERIC(10, 2),
    yhat_price_d4 NUMERIC(10, 2),
    yhat_price_d5 NUMERIC(10, 2),

    yhat_price_lower_d1 NUMERIC(10, 2),
    yhat_price_upper_d1 NUMERIC(10, 2),
    -- ... (d2~d5 lower/upper 생략)

    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (stock_code, trade_date)
);
```

---

#### 3. news_analysis

**Stage 2-2 뉴스 감성 분석 결과**

```sql
CREATE TABLE news_analysis (
    stock_code VARCHAR(10),  -- NULL = 시장 전반 감성
    analysis_date DATE NOT NULL,
    sentiment_score NUMERIC(5, 4) NOT NULL,  -- -1.0 ~ 1.0
    news_count INT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (stock_code, analysis_date)
);
```

---

#### 4. ai_trade_decision

**Stage 4 Gemini AI 매매 결정**

```sql
CREATE TABLE ai_trade_decision (
    id BIGSERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    decision_date DATE NOT NULL,
    decision_type VARCHAR(4) NOT NULL,  -- 'BUY' or 'SELL'
    reason TEXT NOT NULL,               -- AI 판단 이유
    rank INT NOT NULL,                  -- 1, 2, 3 (TOP3)
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

#### 5. safety_filter_result

**Stage 5 Safety Filter 검증 결과**

```sql
CREATE TABLE safety_filter_result (
    id BIGSERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    filter_date DATE NOT NULL,
    decision_type VARCHAR(4) NOT NULL,  -- 'BUY' or 'SELL'
    passed BOOLEAN NOT NULL,            -- 통과 여부
    failure_reason TEXT,                -- 실패 사유
    max_quantity INT,                   -- 최대 주문 가능 수량
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

#### 6. market_daily_summary

**시장 전체 일일 요약**

```sql
CREATE TABLE market_daily_summary (
    trade_date DATE PRIMARY KEY,
    kospi_index NUMERIC(10, 2) NOT NULL,
    kospi_change_rate NUMERIC(8, 4) NOT NULL,
    kospi_volume BIGINT NOT NULL,
    kospi_trade_value BIGINT NOT NULL,  -- 거래대금 (백만원)
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

#### 7. stock_financial

**DART 분기 재무제표 데이터**

```sql
CREATE TABLE stock_financial (
    stock_code VARCHAR(10) NOT NULL,
    base_date DATE NOT NULL,  -- 분기 기준일
    per NUMERIC(10, 2),       -- 주가수익비율
    roe NUMERIC(8, 4),        -- 자기자본이익률 (%)
    operating_margin NUMERIC(8, 4),  -- 영업이익률 (%)
    created_at TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (stock_code, base_date)
);
```

---

## 🔍 API 엔드포인트 및 쿼리

### 1. 시장 전체 데이터

#### 1.1 시장 일일 요약
**엔드포인트**: `GET /api/market/summary`

```sql
-- 최신 시장 요약 조회
SELECT
    trade_date,
    kospi_index,
    kospi_change_rate,
    kospi_volume,
    kospi_trade_value
FROM market_daily_summary
WHERE trade_date = CURRENT_DATE
ORDER BY trade_date DESC
LIMIT 1;
```

**응답 예시**:
```json
{
  "trade_date": "2026-06-01",
  "kospi_index": 2650.25,
  "kospi_change_rate": 1.25,
  "kospi_volume": 850000000,
  "kospi_trade_value": 12500000
}
```

---

#### 1.2 오늘의 매매 결정 요약
**엔드포인트**: `GET /api/market/decisions`

```sql
-- 매수 TOP3
SELECT
    atd.stock_code,
    atd.reason,
    atd.rank,
    sfs.stock_name
FROM ai_trade_decision atd
LEFT JOIN stock_filter_score sfs
    ON atd.stock_code = sfs.stock_code
    AND sfs.score_date = CURRENT_DATE
WHERE atd.decision_date = CURRENT_DATE
  AND atd.decision_type = 'BUY'
ORDER BY atd.rank
LIMIT 3;

-- 매도 TOP3
SELECT
    atd.stock_code,
    atd.reason,
    atd.rank,
    sfs.stock_name
FROM ai_trade_decision atd
LEFT JOIN stock_filter_score sfs
    ON atd.stock_code = sfs.stock_code
    AND sfs.score_date = CURRENT_DATE
WHERE atd.decision_date = CURRENT_DATE
  AND atd.decision_type = 'SELL'
ORDER BY atd.rank
LIMIT 3;
```

---

#### 1.3 Safety Filter 통과 현황
**엔드포인트**: `GET /api/market/safety-status`

```sql
-- 통과율 계산
SELECT
    COUNT(*) FILTER (WHERE passed = true) as passed_count,
    COUNT(*) FILTER (WHERE passed = false) as failed_count,
    ROUND(COUNT(*) FILTER (WHERE passed = true) * 100.0 / COUNT(*), 2) as pass_rate
FROM safety_filter_result
WHERE filter_date = CURRENT_DATE;

-- 실패 사유별 집계
SELECT
    failure_reason,
    COUNT(*) as count
FROM safety_filter_result
WHERE filter_date = CURRENT_DATE
  AND passed = false
GROUP BY failure_reason
ORDER BY count DESC;
```

---

### 2. 종목별 상세 데이터

#### 2.1 종목 11개 피처 전체 조회
**엔드포인트**: `GET /api/stocks/{stockCode}/analysis`

```sql
-- 종목별 전체 분석 데이터 통합 조회
SELECT
    sfs.stock_code,
    sfs.stock_name,
    sfs.score_date,

    -- Stage 1 필터링 지표
    sfs.foreign_net_buy,
    sfs.institutional_net_buy,
    sfs.vol_avg_multiple,
    sfs.price_volatility,
    sfs.scaler_score,
    sfs.is_selected,

    -- Stage 2-1 정량 지표
    sfs.morning_return,
    sfs.close_position,

    -- DART 재무 지표
    sf.per,
    sf.roe,
    sf.operating_margin,

    -- Stage 2-2 감성 지표
    na.sentiment_score,
    na.news_count,

    -- Stage 2-3 시계열 지표
    pf.prophet_price_trend,
    pf.prophet_volume_trend,
    pf.prophet_price_uncertainty,

    -- Stage 4 AI 판단
    atd.decision_type,
    atd.reason as ai_reason,
    atd.rank as ai_rank,

    -- Stage 5 Safety Filter
    sfr.passed as safety_passed,
    sfr.failure_reason as safety_failure_reason,
    sfr.max_quantity
FROM stock_filter_score sfs
LEFT JOIN stock_financial sf
    ON sfs.stock_code = sf.stock_code
LEFT JOIN news_analysis na
    ON sfs.stock_code = na.stock_code
    AND sfs.score_date = na.analysis_date
LEFT JOIN prophet_forecast pf
    ON sfs.stock_code = pf.stock_code
    AND sfs.score_date = pf.trade_date
LEFT JOIN ai_trade_decision atd
    ON sfs.stock_code = atd.stock_code
    AND sfs.score_date = atd.decision_date
LEFT JOIN safety_filter_result sfr
    ON sfs.stock_code = sfr.stock_code
    AND sfs.score_date = sfr.filter_date
WHERE sfs.stock_code = :stockCode
  AND sfs.score_date = CURRENT_DATE;
```

---

#### 2.2 종목별 시계열 예측 상세
**엔드포인트**: `GET /api/stocks/{stockCode}/forecast`

```sql
-- D+1~D+5 예측 상세 조회
SELECT
    stock_code,
    trade_date,

    -- 가격 예측
    yhat_price_d1, yhat_price_lower_d1, yhat_price_upper_d1,
    yhat_price_d2, yhat_price_lower_d2, yhat_price_upper_d2,
    yhat_price_d3, yhat_price_lower_d3, yhat_price_upper_d3,
    yhat_price_d4, yhat_price_lower_d4, yhat_price_upper_d4,
    yhat_price_d5, yhat_price_lower_d5, yhat_price_upper_d5,

    -- 거래량 예측
    yhat_volume_d1, yhat_volume_lower_d1, yhat_volume_upper_d1,
    yhat_volume_d2, yhat_volume_lower_d2, yhat_volume_upper_d2,
    yhat_volume_d3, yhat_volume_lower_d3, yhat_volume_upper_d3,
    yhat_volume_d4, yhat_volume_lower_d4, yhat_volume_upper_d4,
    yhat_volume_d5, yhat_volume_lower_d5, yhat_volume_upper_d5
FROM prophet_forecast
WHERE stock_code = :stockCode
  AND trade_date = CURRENT_DATE;
```

---

#### 2.3 종목별 감성 분석
**엔드포인트**: `GET /api/stocks/{stockCode}/sentiment`

```sql
-- 종목별 감성 점수 조회
SELECT
    na.stock_code,
    sfs.stock_name,
    na.sentiment_score,
    na.news_count,
    na.analysis_date
FROM news_analysis na
JOIN stock_filter_score sfs
    ON na.stock_code = sfs.stock_code
    AND na.analysis_date = sfs.score_date
WHERE na.stock_code = :stockCode
  AND na.analysis_date = CURRENT_DATE;
```

---

### 3. 전체 종목 리스트

#### 3.1 오늘의 Top 30 종목 조회
**엔드포인트**: `GET /api/stocks/selected`

```sql
-- Top 30 선정 종목 조회
SELECT
    sfs.stock_code,
    sfs.stock_name,
    sfs.scaler_score,
    sfs.foreign_net_buy,
    sfs.institutional_net_buy,
    na.sentiment_score,
    atd.decision_type,
    atd.rank
FROM stock_filter_score sfs
LEFT JOIN news_analysis na
    ON sfs.stock_code = na.stock_code
    AND sfs.score_date = na.analysis_date
LEFT JOIN ai_trade_decision atd
    ON sfs.stock_code = atd.stock_code
    AND sfs.score_date = atd.decision_date
WHERE sfs.score_date = CURRENT_DATE
  AND sfs.is_selected = TRUE
ORDER BY sfs.scaler_score DESC;
```

---

## 📱 웹 화면 데이터 요구사항

### 1. 홈 대시보드 (Home View)

**필요 데이터**:
- KOSPI 지수 및 변화율 → `market_daily_summary`
- 오늘의 매수/매도 TOP3 → `ai_trade_decision` + `stock_filter_score`
- Safety Filter 통과율 → `safety_filter_result`
- 사용자 보유 종목 요약 → `user_holdings`

**엔드포인트**:
- `GET /api/market/summary`
- `GET /api/market/decisions`
- `GET /api/market/safety-status`
- `GET /api/user/holdings/summary`

---

### 2. 자산 현황 (Assets View)

**필요 데이터**:
- 보유 종목 목록 및 평가손익 → `user_holdings` + 실시간 시세
- 매매 이력 → `trade_history`
- 일별 자산 변동 그래프 → `user_holdings` (일별 집계)

**엔드포인트**:
- `GET /api/user/holdings`
- `GET /api/user/trades?startDate=&endDate=`
- `GET /api/user/asset-trend?period=30`

---

### 3. AI 분석 (Bot View)

**필요 데이터**:
- 전체 종목 분석 히트맵 (11개 피처) → 위의 2.1 쿼리 사용
- 종목별 감성 분석 그래프 → `news_analysis`
- 종목별 시계열 예측 그래프 → `prophet_forecast`
- AI 매매 결정 및 이유 → `ai_trade_decision`

**엔드포인트**:
- `GET /api/stocks/selected` (Top 30 목록)
- `GET /api/stocks/{stockCode}/analysis` (종목 상세)
- `GET /api/stocks/{stockCode}/forecast` (시계열 상세)

---

### 4. 거래 내역 (Transactions View)

**필요 데이터**:
- 거래 내역 (매수/매도) → `trade_history`
- 종목별 거래 통계 → `trade_history` 집계
- 일별/월별 거래 요약 → `trade_history` 집계

**엔드포인트**:
- `GET /api/user/trades?page=&size=&sort=`
- `GET /api/user/trades/stats?startDate=&endDate=`

---

### 5. 설정 (Settings View)

**필요 데이터**:
- 자동매매 설정 → `user_trade_config`
- 투자 한도 설정 → `user_trade_config`
- KIS API 연동 상태 → `user_kis_accounts`

**엔드포인트**:
- `GET /api/user/config`
- `PUT /api/user/config`

---

## ⚠️ 중요 주의사항

### 1. DB 컬럼명 오류 주의!

AI Agent 코드에서 사용하는 컬럼명과 실제 DB 컬럼명이 다릅니다:

| ❌ AI Agent 코드 | ✅ 실제 DB 컬럼명 | 테이블 |
|------------------|------------------|--------|
| `trade_date` | **`score_date`** | stock_filter_score |
| `institution_net_buy` | **`institutional_net_buy`** | stock_filter_score |
| `volume_ratio` | **`vol_avg_multiple`** | stock_filter_score |
| `final_score` | **`scaler_score`** | stock_filter_score |

**항상 실제 DB 컬럼명을 사용하세요!**

---

### 2. NULL 처리 주의

- `prophet_forecast`의 상세 예측값 (yhat_price_d1~d5) 은 NULL 가능
- `stock_financial`의 PER은 적자 기업의 경우 NULL
- LEFT JOIN 사용 시 반드시 NULL 체크

```java
// DTO에서 NULL 처리 예시
@JsonProperty("per")
public BigDecimal getPer() {
    return per != null ? per : BigDecimal.ZERO;
}
```

---

### 3. 날짜 기준

- **AI Agent 실행 시점**: 매일 08:50
- **데이터 기준일**: `CURRENT_DATE` (실행 당일)
- **휴장일**: AI Agent가 자동 체크하여 데이터 저장 안 함

**쿼리 작성 시**:
```sql
-- ✅ 올바른 방법
WHERE score_date = CURRENT_DATE

-- ❌ 잘못된 방법
WHERE score_date = NOW()  -- TIMESTAMP 비교 오류
```

---

### 4. 인덱스 활용

자주 사용되는 조회 조건에는 인덱스가 설정되어 있습니다:

```sql
-- stock_filter_score
CREATE INDEX idx_sfs_date_selected ON stock_filter_score(score_date, is_selected);
CREATE INDEX idx_sfs_code_date ON stock_filter_score(stock_code, score_date);

-- 쿼리 작성 시 인덱스 활용
WHERE score_date = :date AND is_selected = TRUE  -- ✅ 인덱스 사용
WHERE stock_code = :code AND score_date = :date  -- ✅ 인덱스 사용
```

---

### 5. Spring Boot DTO 예시

```java
@Data
@NoArgsConstructor
@AllArgsConstructor
public class StockAnalysisDto {
    private String stockCode;
    private String stockName;
    private LocalDate scoreDate;

    // Stage 1
    private Long foreignNetBuy;
    private Long institutionalNetBuy;
    private BigDecimal volAvgMultiple;  // ⚠️ volume_ratio 아님!
    private BigDecimal priceVolatility;
    private BigDecimal scalerScore;     // ⚠️ final_score 아님!
    private Boolean isSelected;

    // Stage 2-1
    private BigDecimal morningReturn;
    private BigDecimal closePosition;

    // DART
    private BigDecimal per;
    private BigDecimal roe;
    private BigDecimal operatingMargin;

    // Stage 2-2
    private BigDecimal sentimentScore;
    private Integer newsCount;

    // Stage 2-3
    private BigDecimal prophetPriceTrend;
    private BigDecimal prophetVolumeTrend;
    private BigDecimal prophetPriceUncertainty;

    // Stage 4
    private String decisionType;  // "BUY" or "SELL"
    private String aiReason;
    private Integer aiRank;

    // Stage 5
    private Boolean safetyPassed;
    private String safetyFailureReason;
    private Integer maxQuantity;
}
```

---

## 📚 참고 문서

- **시스템 전체 이해**: `SYSTEM_ARCHITECTURE.md`
- **변경 이력**: `CHANGELOG.md`
- **사용자 가이드**: `USER_GUIDE.md`

---

**문서 버전**: 2.0
**최종 업데이트**: 2026-06-01
**작성**: AI Agent 개발팀
