# MVP 통합 상태 (Integration Status Hub)

> 세 모듈(web-app · api-server · ai-agent)의 **통합·연동(integration) 관점** 진행 상황을 추적하는 허브 문서입니다. 화면/기능 단위 상세 진행은 [`_docs/mvp_progress.md`](_docs/mvp_progress.md), 모듈 내부 상태는 각 모듈 `_docs/`를 참고하세요.

**최종 갱신**: 2026-06 (문서 정리 시점) · 이전 상세 스냅샷(2025-05-03)은 git 이력 참고

---

## 1. 모듈 간 연동 매트릭스

| 연동 구간 | 상태 | 비고 |
|----------|------|------|
| web-app → api-server (인증) | ✅ | 로그인/회원가입/토큰 갱신/로그아웃, 401 자동 리프레시 |
| web-app → api-server (자산·거래내역·설정) | ✅ | 보유 종목, 거래내역, 거래 설정 연동 완료 |
| web-app → api-server (시장 분석·종목 상세) | 🔄 | `MarketAnalysisController`/`CompanyController` 백엔드 존재, 화면 연동 진행 |
| api-server → KIS API | ✅ | 주문/잔고/시세/체결내역 (모의투자) |
| api-server → DART API | ✅ | 기업 재무·공시 (`CompanyController`) |
| api-server ⇄ PostgreSQL | ✅ | Liquibase 스키마, JPA 연동 |
| ai-agent ⇄ PostgreSQL | ✅ | 분석 결과·예측·판단·안전망 필터 적재 |
| ai-agent → KIS / DART / News | ✅ | 분석용 원천 데이터 수집 |
| ai-agent → Gemini API | ✅ | 11 피처 판단 |
| ai-agent → api-server (매매 실행) | 🔄 | `is_active=true` 시 실행 경로, 통합 검증 진행 |
| web-app(AI 분석 화면) ← ai-agent 결과 | 📅 | DB 적재분을 api-server 경유로 노출 예정 |

> ai-agent가 DB에 쓴 분석 결과를 web-app이 **api-server를 통해 조회**하는 구조입니다(직접 호출 아님). 이 경로의 화면 연동이 남은 핵심 통합 작업입니다.

범례: ✅ 완료 · 🔄 진행 중 · 📅 계획 · ⏸️ 대기 · ⚠️ 부분/임시

---

## 2. 모듈별 진행 상황 (요약 + 링크)

### web-app (Vue 3)
인증·자산·거래내역·설정·봇(BotView) 화면 API 연동 완료. AI 분석 화면이 남은 작업.
→ 상세: [`web-app/_docs/README.md`](web-app/_docs/README.md), 화면 단위: [`_docs/mvp_progress.md`](_docs/mvp_progress.md)

### api-server (Spring Boot)
인증(JWT + RefreshToken), 사용자/설정, 자산, 거래(KIS 직접 조회), 시장 분석/종목 상세 조회 API 구현. 예외 체계(`GlobalExceptionHandler`), CORS, Jasypt 암호화 적용.
→ 상세: [`api-server/_docs/README.md`](api-server/_docs/README.md), 인증 흐름: [`api-server/_docs/AUTHENTICATION_FLOW.md`](api-server/_docs/AUTHENTICATION_FLOW.md)

### ai-agent (FastAPI)
6단계 파이프라인(휴장일 체크 → 필터링 → 3-way 분석 → Gemini 판단 → 안전망 필터 → 매매 실행) 구현. 분석 결과 DB 적재.
→ 상세: [`ai-agent/_docs/README.md`](ai-agent/_docs/README.md), 시스템 구조: [`ai-agent/_docs/PIPELINE_DESIGN.md`](ai-agent/_docs/PIPELINE_DESIGN.md)

---

## 3. 주요 API 엔드포인트 (api-server)

| 그룹 | 엔드포인트 |
|------|-----------|
| 인증 (`/auth`) | `POST /login`, `POST /register`, `POST /reset-password`, `GET /check-username`, `GET /check-email`, `POST /refresh`, `POST /logout`, `POST /validate-kis-account` |
| 사용자 (`/users`) | `GET/PUT /me`, `GET/PUT /settings`, `DELETE /me`, `GET/PUT /kis-account`, `GET/PUT /trade-config` |
| 자산 (`/assets`) | `GET /holdings`, `GET /balance` |
| 거래 (`/trading`) | `POST /buy`, `POST /sell`, `GET /history`, `GET /recent`, `GET /holdings` |
| 시장 분석 (`/market`) | `GET /summary`, `GET /sentiment`, `GET /decisions`, `GET /latest-date`, `GET /heatmap`, `GET /stock-analysis/{code}`, `GET /stock-detail/{code}`, `GET /indices`, `GET /exchange-rates`, `GET /news` |
| 기업 (`/company`) | `GET /{code}/basic-info`, `GET /{code}/financials`, `GET /{code}/disclosures` |
| 헬스 (`/health`) | `GET`, `GET /db` |

> 정확한 요청/응답 스펙은 [`api-server/_docs/API_DESIGN.md`](api-server/_docs/API_DESIGN.md) 참고.

---

## 4. 실행 (Quick Start)

```bash
# 1. DB
docker-compose up -d                 # PostgreSQL (financemanage / admin / admin1234)

# 2. api-server
cd api-server
export JWT_SECRET="<256bit 이상 키>"
export JASYPT_PASSWORD="<암호화 키>"
./gradlew bootRun                    # http://localhost:7070 (Liquibase 자동 마이그레이션)

# 3. web-app
cd web-app && npm install && npm run dev   # http://localhost:5173

# 4. ai-agent (venv 필수)
cd ai-agent && ./run_dev.sh          # http://localhost:8000
```

개발용 테스트 계정: `testuser` / `password123` (Liquibase `v1.4-test-data.yaml`)

---

## 5. 알려진 제약 / 통합 잔여 작업

| 항목 | 상태 | 비고 |
|------|------|------|
| AI 분석 화면 연동 | 📅 | ai-agent DB 적재분을 api-server 경유로 web-app에 노출 |
| ai-agent → api-server 매매 실행 e2e | 🔄 | `is_active=true` 경로 통합 검증 |
| api-server 테스트 stale 가능성 | ⚠️ | 예외 체계 변경 후 일부 테스트 갱신 필요 |
| KIS 실계정 연동 | ⏸️ | 현재 모의투자, `user_kis_accounts`에 실키 입력 시 동작 |
| 멀티 유저 / 운영 배포 | 📅 | MVP 범위 밖 (`product` Liquibase context로 확장 예정) |

---

## 6. 관련 문서

- 전체 문서 지도: [`_docs/README.md`](_docs/README.md)
- 시스템 아키텍처: [`_docs/ARCHITECTURE.md`](_docs/ARCHITECTURE.md)
- 화면/기능 단위 진행: [`_docs/mvp_progress.md`](_docs/mvp_progress.md)
- DB 스키마: [`database/README.md`](database/README.md)
