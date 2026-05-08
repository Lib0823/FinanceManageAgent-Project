# Database Schema - MVP

AI 주식 자동매매 시스템 데이터베이스 스키마 문서

## 개요

- **DBMS**: PostgreSQL 16
- **총 테이블 수**: 10개
- **스키마**: 단일 public 스키마 (MVP 단순화)

## 파일 구조

```
database/
├── mvp-schema.sql           # MVP 범위 DDL (참고용 - Liquibase 사용)
├── product-schema.sql       # 프로덕션 범위 DDL (참고용 - Liquibase 사용)
└── README.md                # 이 파일
```

**참고**: 실제 스키마 관리는 Liquibase를 사용합니다. (`api-server/src/main/resources/db/changelog/`)

## 테이블 목록

### 1. 사용자 & 인증 (4개)

| 테이블명 | 설명 | 주요 컬럼 |
|---------|------|-----------|
| `users` | 사용자 기본 정보 | username, email, password, name |
| `refresh_tokens` | JWT 리프레시 토큰 | user_id, token, expires_at |
| `user_kis_accounts` | 사용자별 KIS API 키 | user_id, account_number, app_key, app_secret |
| `user_trade_config` | 투자 전략 설정 | user_id, order_amount, max_holdings, **is_active** |

### 2. 분석 데이터 (5개)

| 테이블명 | 설명 | 갱신 주기 |
|---------|------|-----------|
| `stock_filter_score` | 코스피 100 스코어링 | 매일 (평일 08:50) |
| `stock_financial` | DART 재무지표 | 분기별 |
| `news_analysis` | KR-FinBERT 감성 분석 | 매일 |
| `prophet_forecast` | Prophet 시계열 예측 | 매일 |
| `ai_trade_decision` | Gemini AI 판단 | 매일 |

### 3. 거래 (1개)

| 테이블명 | 설명 | 관리 주체 |
|---------|------|-----------|
| `trade_history` | 주문 체결 이력 | Spring Boot |

## 데이터 흐름

```
[FastAPI 파이프라인 @ 08:50]
    ↓
stock_filter_score ← 코스피 100 스코어링
    ↓
news_analysis ← KR-FinBERT 감성 분석
prophet_forecast ← Prophet 시계열 예측
    ↓
ai_trade_decision ← Gemini AI 판단
    ↓
[Spring Boot]
    ↓
trade_history ← KIS API 체결 결과
```

## 중요 컬럼

### user_trade_config.is_active
- 자동매매 ON/OFF 플래그
- `FALSE`: 파이프라인 분석만 수행, 매매 실행 안 함
- `TRUE`: 분석 + Gemini 판단 → Spring Boot로 매매 요청

### stock_filter_score.is_selected
- `TRUE`: 분석 대상 30개 종목
- `FALSE`: 코스피 100에는 포함되지만 분석 제외

### ai_trade_decision.decision
- `buy`: 매수 추천
- `sell`: 매도 추천
- `hold`: 보유 유지

## 초기 데이터

`mvp-schema.sql` 실행 시 자동 생성:
- admin 계정 (username: `admin`, password: `admin123`)
- admin 투자 설정 (is_active: `FALSE`)

## 마이그레이션 (Liquibase)

**⚠️ 데이터베이스 스키마는 Liquibase로 관리됩니다.**

모든 스키마 변경은 `api-server/src/main/resources/db/changelog/` 디렉토리에서 관리되며, 직접 SQL 실행이 아닌 Liquibase changelog를 통해 적용됩니다.

### 디렉토리 구조

```
api-server/src/main/resources/db/changelog/
├── db.changelog-master.yaml      # 마스터 changelog
├── mvp/                           # MVP 단계 스키마
│   ├── v1.0-users-auth.yaml      # 사용자 인증 및 설정
│   ├── v1.1-analysis-tables.yaml # AI 분석 데이터
│   └── v1.2-trade-history.yaml   # 매매 이력
└── product/                       # 프로덕션 단계 스키마 (향후)
    └── (향후 멀티유저, 감사로그 등 추가 예정)
```

### Context 구분

- **mvp**: 최소 기능 제품 스키마 (단일 사용자, 핵심 기능)
- **product**: 프로덕션 스키마 (멀티유저, 권한, 감사로그, 성능 최적화 등)

### 스키마 적용 방법

Liquibase는 Spring Boot 시작 시 자동으로 실행됩니다:

```yaml
# api-server/src/main/resources/application.yml
spring:
  liquibase:
    change-log: classpath:db/changelog/db.changelog-master.yaml
    enabled: true
    contexts: mvp  # 또는 product
```

### 새로운 스키마 변경 추가 방법

1. 적절한 디렉토리에 새 changelog 파일 생성 (`mvp/` 또는 `product/`)
2. `db.changelog-master.yaml`에 include 추가
3. 서버 재시작 시 자동 적용

### Liquibase 추적 테이블

Liquibase는 자동으로 2개의 메타데이터 테이블을 생성합니다:
- `databasechangelog`: 실행된 changeset 이력
- `databasechangeloglock`: 동시 실행 방지 락

### 참고: SQL 파일

- `mvp-schema.sql` / `product-schema.sql`: 참고용 SQL 스키마 (실행하지 마세요!)
- **실제 스키마는 Liquibase로 관리됩니다.** 수동 SQL 실행 대신 changelog 파일을 수정하세요.

## 인덱스 전략

- **사용자 조회**: `username`, `email`
- **일자 조회**: `score_date`, `analysis_date`, `forecast_date`, `decision_date`
- **종목 조회**: `stock_code`
- **복합 조회**: `(stock_code, date)`, `(user_id, date)`

## 보안 고려사항

### 암호화 필요
- `users.password` → BCrypt
- `user_kis_accounts.app_key` → AES-256 (권장)
- `user_kis_accounts.app_secret` → AES-256 (권장)
- `refresh_tokens.token` → 평문 저장 (JWT 자체 서명)

### 접근 제어
- 애플리케이션 레벨에서 사용자별 데이터 격리
- KIS API 키는 소유자만 조회 가능

## 백업 전략

### 일일 백업
- `stock_filter_score`, `news_analysis`, `prophet_forecast`, `ai_trade_decision`
- 분석 결과 누적 보관 (성능 분석용)

### 실시간 백업
- `trade_history` → 체결 이력 손실 방지

## 향후 확장 계획

1. **다중 계좌 지원**: `user_kis_accounts` 1:N 관계로 변경
2. **포트폴리오 관리**: `portfolios`, `holdings` 테이블 추가
3. **알림 기능**: `notifications` 테이블 추가
4. **뉴스 원문 저장**: `news_articles` 테이블 추가
5. **ML 모델 성능**: `model_performance` 테이블 추가
