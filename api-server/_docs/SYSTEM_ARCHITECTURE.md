# System Architecture - WEB-API-DB Relationship

## Overall Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        VUE[Vue3 SPA]
        VUE_AUTH[인증 컴포넌트]
        VUE_ASSET[자산 컴포넌트]
        VUE_TRADE[매매 컴포넌트]
        VUE_BOT[AI봇 컴포넌트]
        VUE_NEWS[뉴스 컴포넌트]
    end

    subgraph "Backend Layer"
        SPRING[Spring Boot API Server]
        FASTAPI[FastAPI AI Server]

        subgraph "Spring Boot Services"
            AUTH_SVC[AuthService]
            KIS_SVC[KisAuthService]
            ASSET_SVC[AssetService]
            TRADE_SVC[TradingService]
        end

        subgraph "FastAPI Services"
            MARKET_SVC[MarketDataService]
            AI_SVC[AIAnalysisService]
        end
    end

    subgraph "External APIs"
        KIS_API[KIS Open API<br/>한국투자증권]
    end

    subgraph "Database Layer"
        PG[(PostgreSQL)]

        subgraph "User Tables"
            TBL_USER[users]
            TBL_KIS[user_kis_accounts]
            TBL_CONFIG[user_trade_config]
        end

        subgraph "Analysis Tables"
            TBL_FILTER[stock_filter_score]
            TBL_FIN[stock_financial]
            TBL_NEWS[news_analysis]
            TBL_PROPHET[prophet_forecast]
            TBL_AI[ai_trade_decision]
        end

        subgraph "Trading Tables"
            TBL_TRADE[trade_history]
        end
    end

    %% Frontend to Backend Connections
    VUE_AUTH --> AUTH_SVC
    VUE_ASSET --> ASSET_SVC
    VUE_TRADE --> TRADE_SVC
    VUE_BOT --> AI_SVC
    VUE_NEWS --> MARKET_SVC

    %% Backend to Database Connections
    AUTH_SVC --> TBL_USER
    AUTH_SVC --> TBL_KIS
    ASSET_SVC --> TBL_KIS
    TRADE_SVC --> TBL_TRADE
    AI_SVC --> TBL_AI
    AI_SVC --> TBL_NEWS
    AI_SVC --> TBL_PROPHET
    MARKET_SVC --> TBL_FILTER
    MARKET_SVC --> TBL_FIN

    %% Backend to External API Connections
    KIS_SVC --> KIS_API
    ASSET_SVC --> KIS_SVC
    TRADE_SVC --> KIS_SVC
    MARKET_SVC --> KIS_API

    style KIS_API fill:#ffcccc
    style PG fill:#ccffcc
    style SPRING fill:#cce5ff
    style FASTAPI fill:#ffe5cc
```

---

## Authentication Flow

### JWT + KIS Token Flow

```mermaid
sequenceDiagram
    participant User as 사용자
    participant Vue as Vue3
    participant Spring as Spring Boot
    participant Cache as Token Cache
    participant DB as PostgreSQL
    participant KIS as KIS API

    %% Initial Login
    User->>Vue: 로그인 (username/password)
    Vue->>Spring: POST /api/auth/login
    Spring->>DB: SELECT users + user_kis_accounts
    DB-->>Spring: user_id=1, kis_account_id=123

    Note over Spring: JWT 생성<br/>{userId: 1, kisAccountId: 123}
    Spring-->>Vue: JWT Token (1h)
    Vue->>Vue: localStorage 저장

    %% First KIS API Call
    User->>Vue: 잔고 조회
    Vue->>Spring: GET /api/assets/holdings<br/>Authorization: Bearer JWT
    Spring->>Spring: JWT 검증 → kisAccountId=123 추출

    Spring->>Cache: 캐시 확인 (kis_account_id=123)
    Cache-->>Spring: 캐시 미스

    Spring->>DB: SELECT * FROM user_kis_accounts<br/>WHERE id = 123
    DB-->>Spring: app_key(암호화), app_secret(암호화)

    Note over Spring: Jasypt 복호화
    Spring->>KIS: POST /oauth2/tokenP<br/>(app_key, app_secret)
    KIS-->>Spring: KIS Access Token (24h)

    Spring->>Cache: 캐시 저장 (kis_account_id=123)<br/>만료시간: 24h

    Spring->>KIS: GET /uapi/.../inquire-balance<br/>Authorization: Bearer KIS_TOKEN
    KIS-->>Spring: 잔고 데이터
    Spring-->>Vue: JSON 응답

    %% Subsequent KIS API Calls (Cache Hit)
    User->>Vue: 주문 실행
    Vue->>Spring: POST /api/trading/buy<br/>Authorization: Bearer JWT
    Spring->>Spring: JWT 검증 → kisAccountId=123

    Spring->>Cache: 캐시 확인 (kis_account_id=123)
    Cache-->>Spring: 캐시 히트 ✅

    Note over Spring: DB 조회 없음!<br/>성능 최적화

    Spring->>KIS: POST /uapi/.../order-cash<br/>Authorization: Bearer KIS_TOKEN
    KIS-->>Spring: 주문 결과
    Spring->>DB: INSERT INTO trade_history
    Spring-->>Vue: 주문 완료
```

**주요 특징:**
- JWT에 `kis_account_id` 포함 → DB 조회 없이 KIS 토큰 캐시 조회 가능
- 첫 API 호출 시에만 DB 조회 + 복호화 발생 (캐시 미스)
- 이후 24시간 동안 모든 KIS API 호출은 캐시만 사용 (0 DB 쿼리)
- 성능: 99% 이상 캐시 히트율

---

## API Type Classification

### Type A: JWT 인증만 필요 (RDB 조회)

| Vue Component | Spring Boot API | Database Table | 설명 |
|--------------|----------------|---------------|------|
| 프로필 설정 | `GET /api/users/profile` | `users` | 사용자 정보 조회 |
| 프로필 설정 | `PUT /api/users/profile` | `users` | 사용자 정보 수정 |
| 투자 설정 | `GET /api/users/config` | `user_trade_config` | 자동매매 설정 조회 |
| 투자 설정 | `PUT /api/users/config` | `user_trade_config` | 자동매매 ON/OFF |
| AI봇 화면 | `GET /api/analysis/ai-decisions` | `ai_trade_decision` | Gemini AI 판단 결과 |
| AI봇 화면 | `GET /api/analysis/charts` | (Static Files) | matplotlib 차트 이미지 |

**인증 헤더:**
```http
Authorization: Bearer {JWT_TOKEN}
```

**데이터 흐름:**
```
Vue3 → Spring Boot → PostgreSQL → Spring Boot → Vue3
```

---

### Type B: KIS API만 필요 (공개 시장 데이터)

| Vue Component | FastAPI Endpoint | KIS API Endpoint | 설명 |
|--------------|-----------------|------------------|------|
| 종목 검색 | `GET /api/market/search` | `CTPF1002R` | 종목 검색 |
| 종목 상세 | `GET /api/market/stocks/{code}/price` | `FHKST01010100` | 현재가 조회 |
| 종목 상세 | `GET /api/market/stocks/{code}/chart` | `FHKST01010400` | 차트 데이터 |
| 뉴스 화면 | `GET /api/news/market` | (Crawling) | 시장 뉴스 |

**인증 헤더:**
```http
# KIS API 호출 시
authorization: Bearer {KIS_ACCESS_TOKEN}
appkey: {APP_KEY}
appsecret: {APP_SECRET}
tr_id: FHKST01010100  # API별 고유값
```

**데이터 흐름:**
```
Vue3 → FastAPI → KIS API → FastAPI → Vue3
```

**특징:**
- 사용자별 인증 불필요 (공개 데이터)
- FastAPI가 단일 KIS 계정으로 호출
- 응답 캐싱 가능 (1분~5분)

---

### Type C: JWT + KIS 인증 필요 (사용자별 KIS 계정)

| Vue Component | Spring Boot API | KIS API Endpoint | Database Table | 설명 |
|--------------|----------------|------------------|---------------|------|
| 자산 화면 | `GET /api/assets/holdings` | `VTTC8434R` | `user_kis_accounts` | 보유 종목 조회 |
| 자산 화면 | `GET /api/assets/balance` | `VTTC8434R` | `user_kis_accounts` | 예수금 조회 |
| 매매 화면 | `POST /api/trading/buy` | `VTTC0802U` | `trade_history`, `user_kis_accounts` | 매수 주문 |
| 매매 화면 | `POST /api/trading/sell` | `VTTC0801U` | `trade_history`, `user_kis_accounts` | 매도 주문 |
| 매매 화면 | `GET /api/trading/history` | - | `trade_history` | 거래 이력 |

**인증 헤더:**
```http
# 1. Spring Boot API 호출 시
Authorization: Bearer {JWT_TOKEN}

# 2. Spring Boot → KIS API 호출 시
authorization: Bearer {USER_KIS_ACCESS_TOKEN}
appkey: {USER_APP_KEY}  # DB에서 복호화
appsecret: {USER_APP_SECRET}  # DB에서 복호화
tr_id: VTTC8434R
```

**데이터 흐름:**
```
Vue3
  → Spring Boot (JWT 검증 → kisAccountId 추출)
    → Token Cache (캐시 조회)
      → [캐시 미스 시] PostgreSQL (user_kis_accounts 복호화)
        → KIS API (사용자 AppKey/Secret로 토큰 발급)
          → Token Cache (캐시 저장)
    → KIS API (잔고/주문 실행)
      → Spring Boot (응답 + trade_history INSERT)
        → Vue3
```

**성능 최적화:**
- 첫 호출: DB 조회 + KIS 토큰 발급 (~500ms)
- 이후 호출: 캐시 사용 (~50ms, 10배 빠름)

---

## Database Schema Mapping

### 사용자 인증 관련

```mermaid
erDiagram
    users ||--o{ user_kis_accounts : "1:1"
    users ||--o{ user_trade_config : "1:1"
    users ||--o{ trade_history : "1:N"

    users {
        bigserial id PK
        varchar username UK
        varchar email UK
        varchar password "BCrypt"
        varchar name
        timestamp created_at
    }

    user_kis_accounts {
        bigserial id PK
        bigint user_id FK
        varchar account_number UK "8자리"
        varchar account_product_code "기본값: 01"
        varchar app_key "Jasypt 암호화"
        varchar app_secret "Jasypt 암호화"
        boolean is_verified
    }

    user_trade_config {
        bigserial id PK
        bigint user_id FK
        bigint order_amount "1회 주문 금액"
        int max_holdings "최대 보유 종목"
        varchar order_type "market/limit"
        boolean is_active "자동매매 ON/OFF"
    }
```

**사용 API:**
- `POST /api/auth/login` → `users`, `user_kis_accounts` 조회
- `GET /api/users/profile` → `users` 조회
- `GET /api/users/config` → `user_trade_config` 조회

---

### 거래 이력 관련

```mermaid
erDiagram
    users ||--o{ trade_history : "1:N"

    trade_history {
        bigserial id PK
        bigint user_id FK
        varchar order_number "KIS ODNO"
        varchar stock_code "종목코드"
        varchar stock_name "종목명"
        varchar order_type "BUY/SELL"
        varchar order_status "PENDING/EXECUTED/CANCELLED/FAILED"
        int quantity "주문수량"
        numeric order_price "주문단가"
        numeric executed_price "체결단가"
        int executed_quantity "체결수량"
        timestamp ordered_at "주문시각"
        timestamp executed_at "체결시각"
    }
```

**사용 API:**
- `POST /api/trading/buy` → `trade_history` INSERT (status=PENDING)
- `GET /api/trading/history` → `trade_history` SELECT
- FastAPI 스케줄러 → `trade_history` UPDATE (status=EXECUTED)

**주문 상태 흐름:**
```
PENDING → EXECUTED (정상 체결)
        → CANCELLED (사용자 취소)
        → FAILED (주문 실패)
```

---

### AI 분석 결과 관련

```mermaid
erDiagram
    stock_filter_score ||--o{ ai_trade_decision : "N:M"
    stock_filter_score ||--o{ prophet_forecast : "N:M"

    stock_filter_score {
        bigserial id PK
        varchar stock_code
        varchar stock_name
        date score_date
        bigint foreign_net_buy "외국인 순매수"
        bigint institutional_net_buy "기관 순매수"
        numeric vol_avg_multiple "거래량 배율"
        numeric price_volatility "가격 변동성"
        numeric scaler_score "StandardScaler 점수"
        boolean is_selected "TOP30 선정 여부"
    }

    ai_trade_decision {
        bigserial id PK
        varchar stock_code
        varchar stock_name
        date decision_date
        varchar decision "buy/sell/hold"
        int rank "1,2,3 for TOP3"
        text reason "AI 판단 근거"
        text prompt_summary
    }

    prophet_forecast {
        bigserial id PK
        varchar stock_code
        date forecast_date
        numeric yhat_d1 "D+1 예측가"
        numeric yhat_d2 "D+2 예측가"
        numeric price_trend "가격 추세"
        numeric volume_trend "거래량 추세"
        numeric price_uncertainty "예측 불확실성"
    }
```

**사용 API:**
- `GET /api/analysis/ai-decisions` → `ai_trade_decision` SELECT (rank <= 3)
- `GET /api/analysis/prophet` → `prophet_forecast` SELECT
- FastAPI 스케줄러 → 모든 테이블 INSERT (매일 08:50)

---

## API Server Role Split

### Spring Boot 담당 (Java 21)

**책임 영역:**
- 사용자 인증/인가 (JWT)
- 사용자별 KIS 계정 관리
- 주문 실행 및 거래 이력 관리
- KIS API 프록시 (사용자별 인증)

**주요 API:**
```
POST /api/auth/login          # JWT 발급
GET  /api/assets/holdings     # KIS VTTC8434R 호출
POST /api/trading/buy          # KIS VTTC0802U 호출
POST /api/trading/sell         # KIS VTTC0801U 호출
GET  /api/trading/history      # trade_history 조회
```

---

### FastAPI 담당 (Python 3.11+)

**책임 영역:**
- 시장 데이터 수집 (KIS API)
- AI 분석 파이프라인 (APScheduler)
- 차트 생성 (matplotlib)
- 뉴스 감성 분석 (KR-FinBERT)
- 시계열 예측 (Prophet)

**주요 API:**
```
GET /api/market/stocks/{code}/price   # KIS FHKST01010100 호출
GET /api/analysis/charts              # Static PNG 제공
GET /api/analysis/ai-decisions        # ai_trade_decision 조회
```

**스케줄러:**
```python
# 매일 평일 08:50 실행
@scheduler.scheduled_job('cron', day_of_week='mon-fri', hour=8, minute=50)
def daily_pipeline():
    # 1. KOSPI 100 → StandardScaler → TOP 30
    # 2. KIS API 데이터 수집
    # 3. Prophet 예측
    # 4. 감성 분석
    # 5. Gemini AI 판단
    # 6. 차트 생성
    # 7. PostgreSQL INSERT
```

---

## Security Summary

### 암호화 저장 (Database)

| 컬럼 | 암호화 방식 | 복호화 시점 |
|-----|----------|----------|
| `users.password` | BCrypt (단방향) | 복호화 불가 (비교만 가능) |
| `user_kis_accounts.app_key` | Jasypt (양방향) | KIS API 호출 직전 |
| `user_kis_accounts.app_secret` | Jasypt (양방향) | KIS API 호출 직전 |

**Jasypt 설정:**
```yaml
# application.yml
jasypt:
  encryptor:
    password: ${JASYPT_PASSWORD}  # 환경 변수
    algorithm: PBEWithMD5AndDES
```

---

### 토큰 관리

| 토큰 종류 | 발급처 | 유효기간 | 저장 위치 |
|---------|-------|--------|---------|
| JWT Access Token | Spring Boot | 1시간 | Vue3 localStorage |
| JWT Refresh Token | Spring Boot | 24시간 | Vue3 localStorage |
| KIS Access Token | KIS API | 24시간 | Spring Boot Memory Cache |

**KIS 토큰 캐시 키:**
```java
// kis_account_id를 키로 사용 (JWT에서 추출)
Map<Long, KisTokenCache> userKisTokens = new ConcurrentHashMap<>();

// kisAccountId = 123 (JWT payload)
KisTokenCache cache = userKisTokens.get(123L);
```

---

## Performance Optimization

### 캐시 전략

| 데이터 타입 | 캐시 위치 | TTL | 갱신 조건 |
|----------|---------|-----|---------|
| KIS Access Token | JVM Memory | 24시간 | 만료 1시간 전 자동 갱신 |
| 시장 데이터 (현재가) | Redis (선택) | 1분 | 실시간 업데이트 필요 시 |
| AI 분석 결과 | PostgreSQL | 1일 | 매일 08:50 스케줄러 |

### DB 쿼리 최적화

**Before (성능 문제):**
```java
// 매 API 호출마다 DB 조회 + 복호화
@GetMapping("/api/assets/holdings")
public ResponseEntity<?> getHoldings(@AuthUser Long userId) {
    UserKisAccount kisAccount = kisAccountRepo.findByUserId(userId);  // ❌ 매번 DB 조회
    String appKey = jasyptDecrypt(kisAccount.getAppKey());  // ❌ 매번 복호화
    String kisToken = getKisToken(appKey, appSecret);  // ❌ 매번 KIS API 호출
    return kisClient.getHoldings(kisToken);
}
```

**After (최적화):**
```java
// JWT에서 kisAccountId 추출 → 캐시 조회
@GetMapping("/api/assets/holdings")
public ResponseEntity<?> getHoldings(@AuthUser JwtPayload jwt) {
    Long kisAccountId = jwt.getKisAccountId();  // ✅ JWT에서 직접 추출
    String kisToken = kisAuthService.getKisAccessToken(kisAccountId);  // ✅ 캐시 우선
    return kisClient.getHoldings(kisToken);
}

// KisAuthService 내부
public String getKisAccessToken(Long kisAccountId) {
    KisTokenCache cached = userKisTokens.get(kisAccountId);
    if (cached != null && !cached.isExpired()) {
        return cached.getAccessToken();  // ✅ 캐시 히트 (0 DB 쿼리)
    }
    // 캐시 미스 시에만 DB 조회 + 복호화 + KIS API 호출
}
```

**성능 개선:**
- API 응답 시간: 500ms → 50ms (10배 빠름)
- DB 부하: 100 req/sec → 1 req/day (99% 감소)

---

## Environment Variables

### Spring Boot (api-server)

```env
# Database
SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/financedb
SPRING_DATASOURCE_USERNAME=postgres
SPRING_DATASOURCE_PASSWORD=your_password

# Jasypt 암호화 마스터 키
JASYPT_PASSWORD=your_encryption_master_key

# JWT Secret
JWT_SECRET=your_jwt_secret_key_min_256_bits

# KIS API (공통 계정 - FastAPI와 공유)
KIS_APP_KEY=your_kis_app_key
KIS_APP_SECRET=your_kis_app_secret
```

### FastAPI (ai-agent)

```env
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/financedb

# KIS API (시장 데이터 수집용)
KIS_APP_KEY=your_kis_app_key
KIS_APP_SECRET=your_kis_app_secret

# Gemini AI
GEMINI_API_KEY=your_gemini_api_key

# DART API (재무 데이터)
DART_API_KEY=your_dart_api_key
```

---

## Deployment Architecture

```mermaid
graph TB
    subgraph "Production Environment"
        NGINX[Nginx<br/>Port 3000]

        subgraph "Application Containers"
            WEB[Vue3 SPA<br/>Static Files]
            SPRING[Spring Boot<br/>Port 8080]
            FAST[FastAPI<br/>Port 8000]
        end

        subgraph "Data Layer"
            PG[(PostgreSQL<br/>Port 5432)]
            ES[(Elasticsearch<br/>Port 9200)]
        end
    end

    NGINX --> WEB
    WEB --> SPRING
    WEB --> FAST
    SPRING --> PG
    FAST --> PG
    FAST --> ES
```

**Docker Compose 서비스:**
- `nginx`: Vue3 빌드 결과 서빙 + 리버스 프록시
- `api-server`: Spring Boot (Gradle bootJar)
- `ai-agent`: FastAPI (uvicorn)
- `postgres`: PostgreSQL 16
- `elasticsearch`: 뉴스 검색용

---

## Quick Reference

### API 인증 요구사항

| API 경로 | JWT | KIS Token | 데이터 소스 |
|---------|-----|-----------|----------|
| `/api/auth/*` | ❌ | ❌ | PostgreSQL |
| `/api/users/*` | ✅ | ❌ | PostgreSQL |
| `/api/assets/*` | ✅ | ✅ | KIS API + PostgreSQL |
| `/api/trading/*` | ✅ | ✅ | KIS API + PostgreSQL |
| `/api/market/*` | ❌ | ✅ | KIS API (FastAPI) |
| `/api/analysis/*` | ✅ | ❌ | PostgreSQL + Static Files |

### KIS API TR_ID 매핑

| 기능 | Spring Boot API | KIS TR_ID | 용도 |
|-----|----------------|-----------|------|
| 잔고조회 | `GET /api/assets/holdings` | `VTTC8434R` | 보유종목 + 평가금액 |
| 매수주문 | `POST /api/trading/buy` | `VTTC0802U` | 현금 매수 주문 |
| 매도주문 | `POST /api/trading/sell` | `VTTC0801U` | 현금 매도 주문 |
| 현재가조회 | `GET /api/market/stocks/{code}/price` | `FHKST01010100` | 실시간 호가 |
| 차트데이터 | `GET /api/market/stocks/{code}/chart` | `FHKST01010400` | 일봉/분봉 |

### 주요 데이터 흐름

**로그인:**
```
Vue3 → Spring Boot → PostgreSQL (users + user_kis_accounts)
     ← JWT (userId, kisAccountId)
```

**잔고조회:**
```
Vue3 → Spring Boot (JWT 검증)
     → Token Cache (kis_account_id=123)
     → [캐시 미스] PostgreSQL (Jasypt 복호화) → KIS OAuth
     → KIS API (VTTC8434R)
     ← 잔고 데이터
```

**AI 분석:**
```
FastAPI Scheduler (08:50)
  → KIS API (종목 데이터 수집)
  → Prophet (시계열 예측)
  → KR-FinBERT (감성 분석)
  → Gemini API (매매 판단)
  → PostgreSQL INSERT
  → matplotlib (차트 생성)

Vue3 → FastAPI → PostgreSQL (ai_trade_decision)
     ← AI 분석 결과 + 차트 URL
```
