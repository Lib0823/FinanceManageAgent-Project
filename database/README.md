# Database Schema

AI 주식 자동매매 시스템 데이터베이스 스키마 문서

## 개요

- **DBMS**: PostgreSQL 16
- **총 테이블 수**: 17개 (+ 뷰 2개)
- **스키마**: 단일 public 스키마 (MVP 단순화)
- **실제 적용**: Liquibase (`api-server/src/main/resources/db/changelog/`)

## 파일 구조

```
database/
├── schema.sql   # 통합 DDL (전체 17 테이블 + 2 뷰, 참고용)
└── README.md    # 이 파일
```

> **실제 스키마 관리는 Liquibase**가 담당합니다. `schema.sql`은 전체 구조를 한눈에 보기 위한 참고용 통합 DDL이며, 직접 실행 대신 Liquibase changelog를 수정하세요.

상위 시스템 데이터 흐름은 [`../_docs/ARCHITECTURE.md`](../_docs/ARCHITECTURE.md) 참고.

---

## 테이블 목록

### 1. 사용자 & 인증 (5개)

| 테이블명 | 설명 | 주요 컬럼 |
|---------|------|-----------|
| `users` | 사용자 기본 정보 | username, email, password(BCrypt), name, phone, birth_date |
| `refresh_tokens` | JWT 리프레시 토큰 | user_id, token, expires_at, revoked_at |
| `user_kis_accounts` | 사용자별 KIS API 키 (1:1) | user_id, account_number, app_key, app_secret (Jasypt 암호화), is_verified |
| `user_trade_config` | 자동매매 설정 (1:1) | user_id, order_amount, max_holdings, order_type, **is_active** |
| `user_settings` | UI 설정 (1:1) | user_id, asset_order(JSONB), dark_mode, auto_login, notifications(JSONB) |

### 2. 분석 데이터 (6개)

| 테이블명 | 설명 | 갱신 주기 | 쓰는 쪽 |
|---------|------|-----------|---------|
| `stock_filter_score` | 코스피 100 스코어링 (→ 30 선정) | 매일 (평일 08:50) | ai-agent |
| `stock_financial` | DART 재무지표 (PER, ROE, 영업이익률) | 분기별 | ai-agent |
| `news_analysis` | KR-FinBERT 감성 분석 | 매일 | ai-agent |
| `prophet_forecast` | Prophet D+1~D+5 시계열 예측 | 매일 | ai-agent |
| `ai_trade_decision` | Gemini AI 매수/매도 판단 (TOP3) | 매일 | ai-agent |
| `safety_filter_result` | Gemini 판단 사후 검증 (안전망 필터) | 매일 | ai-agent |

### 3. 웹 표시용 (3개)

| 테이블명 | 설명 | 비고 |
|---------|------|------|
| `market_daily_summary` | 시장 전체 일일 요약 (KOSPI 지수, 등락 종목수, 시장 감성) | 대시보드용 |
| `stock_realtime_price` | 종목별 실시간 가격 (캐시) | 현재가, 등락률, 거래량 |
| `user_holdings` | 사용자별 보유 종목 현황 | 평가손익, 평가손익률 |

### 4. 매매 실행 & 거래 (3개)

| 테이블명 | 설명 | 관리 주체 |
|---------|------|-----------|
| `trade_execution_plan` | 안전망 필터 통과 후 매매 계획 및 실행 결과 | ai-agent |
| `feature_threshold_config` | 안전망 필터 임계값 (BUY/SELL 규칙, 동적 조정) | ai-agent (기본값 seed) |
| `trade_history` | 주문 체결 이력 (KIS 주문번호, 상태, 체결가) | Spring Boot |

### 5. 뷰 (2개)

| 뷰명 | 설명 |
|------|------|
| `v_latest_trade_plan` | 당일 매매 계획 요약 (계획/통과/실행 건수, 예상 금액) |
| `v_decision_with_filter` | Gemini 판단 + 안전망 필터 결합 결과 (최근 7일) |

---

## 데이터 흐름

```
[FastAPI 파이프라인 @ 평일 08:50]
    ↓
stock_filter_score        ← 코스피 100 스코어링 → Top 30 (is_selected)
    ↓
news_analysis             ← KR-FinBERT 감성 분석
prophet_forecast          ← Prophet 시계열 예측
(stock_financial 조회)    ← DART 재무지표 (분기별 적재분 사용)
    ↓
ai_trade_decision         ← Gemini AI 판단 (buy/sell/hold TOP3)
    ↓
safety_filter_result      ← 임계값 기반 사후 검증
    ↓
trade_execution_plan      ← 통과 종목 매매 계획
    ↓
[Spring Boot, is_active=true]
    ↓
trade_history             ← KIS API 체결 결과
```

---

## 중요 컬럼

### user_trade_config.is_active
- 자동매매 ON/OFF 플래그
- `FALSE`: 파이프라인 분석만 수행, 매매 실행 안 함
- `TRUE`: 분석 + Gemini 판단 → Spring Boot로 매매 요청

### stock_filter_score.is_selected
- `TRUE`: 분석 대상 30개 종목
- `FALSE`: 코스피 100에는 포함되지만 분석 제외

### ai_trade_decision.decision
- `buy`: 매수 추천 · `sell`: 매도 추천 · `hold`: 보유 유지
- `feature_summary` (JSONB): 판단 근거가 된 주요 피처값

### safety_filter_result.filter_checks (JSONB)
- 각 규칙별 통과 여부 (예: `uncertainty_check`, `foreign_net_buy_check`, `sentiment_check` 등)

### feature_threshold_config
- 안전망 필터 임계값을 동적으로 관리. `schema.sql` 실행 시 11개 피처 기본 규칙 seed
  (`foreign_net_buy`, `institutional_net_buy`, `sentiment_score`, `prophet_price_trend`,
  `prophet_volume_trend`, `prophet_price_uncertainty`, `per`, `roe`, `operating_margin`,
  `morning_return`, `close_position`)

---

## 마이그레이션 (Liquibase)

**⚠️ 데이터베이스 스키마는 Liquibase로 관리됩니다.**

모든 스키마 변경은 `api-server/src/main/resources/db/changelog/`에서 관리되며, Spring Boot 시작 시 자동 적용됩니다.

### 디렉토리 구조

```
api-server/src/main/resources/db/changelog/
├── db.changelog-master.yaml          # 마스터 changelog
├── mvp/                              # MVP context
│   ├── v1.0-users-auth.yaml          # 사용자 인증 및 설정
│   ├── v1.1-analysis-tables.yaml     # AI 분석 데이터
│   ├── v1.2-trade-history.yaml       # 매매 이력
│   ├── v1.3-schema-updates.yaml      # KIS 연동 스키마 업데이트
│   ├── v1.4-test-data.yaml           # 테스트 데이터
│   ├── v1.5-user-settings.yaml       # 사용자 UI 설정
│   ├── v1.6-stage4-5-enhancements.yaml  # 안전망 필터 + 매매 실행 계획
│   └── v1.7-web-display-tables.yaml  # 시장 요약 / 실시간 가격 / 보유 종목
└── product/                          # 프로덕션 context (향후)
```

### Context 구분
- **mvp**: 최소 기능 제품 스키마 (단일 사용자, 핵심 기능)
- **product**: 프로덕션 스키마 (멀티유저, 권한, 감사로그 등 — 향후)

### 설정

```yaml
# api-server/src/main/resources/application.yml
spring:
  liquibase:
    change-log: classpath:db/changelog/db.changelog-master.yaml
    enabled: true
    contexts: mvp
```

### Liquibase 추적 테이블
- `databasechangelog`: 실행된 changeset 이력
- `databasechangeloglock`: 동시 실행 방지 락

---

## 초기 데이터

- `users`: admin 계정 (username: `admin`, password: `admin123` BCrypt)
- `user_trade_config`: admin 투자 설정 (is_active `FALSE`)
- `feature_threshold_config`: 11개 피처 기본 임계값
- 개발용 테스트 계정(`testuser` / `password123`)은 Liquibase `v1.4-test-data.yaml`로 적재

---

## 인덱스 전략

- **사용자 조회**: `username`, `email`
- **일자 조회**: `score_date`, `analysis_date`, `forecast_date`, `decision_date`, `filter_date`, `execution_date`
- **종목 조회**: `stock_code`
- **복합 조회**: `(stock_code, date)`, `(user_id, stock_code)`, `(decision_date, decision, rank)`

## 보안 고려사항

- `users.password` → BCrypt
- `user_kis_accounts.app_key` / `app_secret` → Jasypt (AES-256) 암호화 저장
- `refresh_tokens.token` → JWT 자체 서명 (평문 저장)
- 애플리케이션 레벨에서 사용자별 데이터 격리

## 향후 확장 계획

1. **다중 계좌 지원**: `user_kis_accounts` 1:N 관계로 변경
2. **포트폴리오 관리**: 포지션·자산 배분 테이블 확장
3. **알림 기능**: `notifications` 테이블 추가
4. **뉴스 원문 저장**: `news_articles` 테이블 추가
5. **ML 모델 성능 추적**: `model_performance` 테이블 추가
