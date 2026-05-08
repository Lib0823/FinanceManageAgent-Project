# API Server Documentation

AI 주식 자동매매 시스템 백엔드 API 설계 및 아키텍처 문서

---

## 📚 문서 목록

### 1️⃣ [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md) ⭐ **개발 전 필독**
**WEB-API-DB 관계 시각화 및 전체 시스템 아키텍처**

- 전체 시스템 구조도 (Vue3 ↔ Spring Boot/FastAPI ↔ PostgreSQL ↔ KIS API)
- Authentication Flow (JWT + KIS Token 관리)
- API 타입 분류 (Type A/B/C)
- Database ERD 및 테이블 매핑
- 성능 최적화 전략 (캐싱, 토큰 관리)
- 배포 아키텍처

**주요 내용:**
- Mermaid 다이어그램으로 데이터 흐름 시각화
- API별 인증 요구사항 및 데이터 소스 정리
- KIS API TR_ID 매핑 테이블

---

### 2️⃣ [AUTHENTICATION_FLOW.md](./AUTHENTICATION_FLOW.md) ⭐ **보안 필독**
**다중 사용자 인증 및 KIS 토큰 관리 최적화**

- JWT Payload 설계 (`kis_account_id` 포함)
- KIS Access Token 캐싱 전략 (성능 최적화)
- 3가지 API 인증 타입 (No Auth, JWT, JWT+KIS)
- Jasypt 암호화 설정

**핵심 최적화:**
```
첫 호출: DB 조회 + 복호화 + KIS API 호출 (~500ms)
이후 호출: 캐시만 사용 (~50ms, 99% 캐시 히트율)
```

---

### 3️⃣ [KIS_INTEGRATION_GUIDE.md](./KIS_INTEGRATION_GUIDE.md) ⭐ **KIS API 필독**
**KIS Open API 통합 가이드 (통합 문서)**

- **인증 & 보안**: AppKey/AppSecret 관리, Access Token 발급/갱신, Jasypt 암호화
- **아키텍처 패턴**: BFF 필수성 (CORS 제약), 토큰 캐싱 전략 (99% 캐시 히트율)
- **API 매핑**: TR_ID 매핑 테이블, 요청/응답 샘플
- **구현 가이드**: 실제 Java 코드 예제 (KisAuthService, AssetController, TradingService)

**주요 내용:**
```
인증 흐름: AppKey/Secret → KIS Token → Redis Cache (23h)
BFF 패턴: Vue3 → Spring Boot → KIS API (Direct 호출 ❌)
성능: 첫 호출 500ms → 캐시 히트 50ms (10배 향상)
```

**주요 매핑:**
| App API | KIS TR_ID | 용도 |
|---------|-----------|------|
| `GET /api/assets/holdings` | `VTTC8434R` | 잔고조회 |
| `POST /api/trading/buy` | `VTTC0802U` | 매수주문 |
| `POST /api/trading/sell` | `VTTC0801U` | 매도주문 |

---

### 4️⃣ [API_DESIGN.md](./API_DESIGN.md)
**REST API 엔드포인트 전체 명세**

- 인증 API (로그인/로그아웃/토큰 갱신)
- 사용자 API (프로필/설정)
- 자산 API (잔고/보유종목)
- 매매 API (매수/매도/거래내역)
- 시장정보 API (종목검색/현재가/차트)
- 뉴스 API (시장뉴스/종목뉴스)
- AI 분석 API (AI 판단/예측/차트)

**API 명세 포함:**
- HTTP Method, URL, Request/Response
- 인증 요구사항
- KIS API 사용 여부

---

## 🗂️ 관련 디렉토리

### Database 스키마
- `/database/mvp-schema.sql` - MVP 데이터베이스 스키마
- `/database/product-schema.sql` - 프로덕션 스키마 (MVP와 동기화)
- `/database/database-erd.sql` - ERD 다이어그램
- `/database/database-erd-diagram.md` - ERD 마크다운 문서

### Liquibase 마이그레이션
- `/api-server/src/main/resources/db/changelog/mvp/v1.0-initial-schema.yaml` - 초기 스키마
- `/api-server/src/main/resources/db/changelog/mvp/v1.3-schema-updates.yaml` - KIS 인증 최적화 스키마

---

## 🚀 개발 시작 전 체크리스트

### 1. 문서 숙지
- [ ] `SYSTEM_ARCHITECTURE.md` 전체 시스템 이해
- [ ] `AUTHENTICATION_FLOW.md` JWT + KIS 토큰 관리 이해
- [ ] `KIS_INTEGRATION_GUIDE.md` KIS API 통합 및 보안 요구사항 확인

### 2. 환경 설정
- [ ] PostgreSQL 16 설치 및 데이터베이스 생성
- [ ] `/database/mvp-schema.sql` 실행하여 테이블 생성
- [ ] 환경 변수 설정 (`JASYPT_PASSWORD`, `KIS_APP_KEY`, etc.)

### 3. 의존성 확인
- [ ] Java 21 (LTS) 설치
- [ ] Gradle 빌드 도구
- [ ] Spring Boot 3.x/4.x
- [ ] Jasypt (암호화)

### 4. KIS API 계정
- [ ] 한국투자증권 모의투자 계정 생성
- [ ] AppKey/AppSecret 발급
- [ ] Jasypt로 암호화하여 DB 저장

### 5. 보안 검토
- [ ] JWT Secret 256비트 이상 생성
- [ ] Jasypt Master Password 안전한 곳에 보관
- [ ] .env 파일 .gitignore 등록

---

## 📊 주요 데이터 흐름 요약

### 로그인 흐름
```
사용자 → Vue3 → Spring Boot
  → DB (users + user_kis_accounts 조회)
  → JWT 발급 (userId + kisAccountId 포함)
  ← JWT Token (1h)
```

### 잔고 조회 흐름 (최초)
```
사용자 → Vue3 → Spring Boot (JWT 검증)
  → Token Cache 확인 (kis_account_id=123)
  → [캐시 미스] DB 조회 → Jasypt 복호화
  → KIS OAuth Token 발급
  → Cache 저장 (24h)
  → KIS API (VTTC8434R 잔고조회)
  ← 잔고 데이터
```

### 잔고 조회 흐름 (이후)
```
사용자 → Vue3 → Spring Boot (JWT 검증)
  → Token Cache 조회 (kis_account_id=123) ✅ 캐시 히트
  → KIS API (VTTC8434R 잔고조회)
  ← 잔고 데이터

성능: 500ms → 50ms (10배 빠름, DB 조회 없음)
```

### AI 분석 흐름
```
FastAPI Scheduler (평일 08:50)
  → KIS API (KOSPI 100 데이터 수집)
  → StandardScaler (TOP 30 선정)
  → Prophet (시계열 예측)
  → KR-FinBERT (감성 분석)
  → Gemini API (매매 판단)
  → PostgreSQL INSERT
  → matplotlib 차트 생성

사용자 → Vue3 → FastAPI
  → DB (ai_trade_decision 조회)
  ← AI 판단 결과 + 차트 이미지 URL
```

---

## 🔐 보안 주의사항

### 절대 커밋하지 말 것
- `.env` 파일
- `application-local.yml`
- KIS AppKey/AppSecret 평문
- JWT Secret 평문
- Jasypt Master Password

### 암호화 필수
- `user_kis_accounts.app_key` → Jasypt 암호화
- `user_kis_accounts.app_secret` → Jasypt 암호화
- `users.password` → BCrypt 해시

### 환경 변수 관리
```bash
# .env (절대 커밋하지 말 것!)
JASYPT_PASSWORD=your_strong_master_key_min_32_chars
JWT_SECRET=your_jwt_secret_min_256_bits
KIS_APP_KEY=your_kis_app_key
KIS_APP_SECRET=your_kis_app_secret
```

---

## 📞 문의 및 이슈

- 아키텍처 관련: `SYSTEM_ARCHITECTURE.md` 참고
- 인증 관련: `AUTHENTICATION_FLOW.md` 참고
- KIS API 관련: `KIS_INTEGRATION_GUIDE.md` 참고
- API 명세 관련: `API_DESIGN.md` 참고

---

**작성일:** 2025-05-02
**버전:** MVP v1.0
**상태:** 개발 준비 완료 ✅
