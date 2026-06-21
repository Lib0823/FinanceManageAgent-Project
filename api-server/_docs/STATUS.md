# STATUS

api-server 모듈의 기능·엔드포인트별 구현 진행 상황이다. 코드(`src/main/java/com/inbeom/apiserver/**`) 기준이며, 상태는 다음 기준으로 분류한다.

- **완료**: 컨트롤러·서비스·연동까지 구현되어 호출 가능
- **진행중**: 일부 구현 또는 임시 동작(MVP fallback)이 있어 보완 필요
- **미착수**: 코드에 존재하지 않음

> 참고: 본 표는 "구현 존재 여부"를 나타내며 통합 테스트 통과를 보증하지 않는다. 자동화 테스트 현황은 마지막 절을 참고한다.

---

## 1. 인증 (AuthController / AuthService)

| 기능 | 엔드포인트 | 상태 | 비고 |
|------|-----------|------|------|
| 로그인 | `POST /auth/login` | 완료 | KIS 계정 연동이 로그인 전제 조건(없으면 `KisAccountNotFoundException`) |
| 회원가입 | `POST /auth/register` | 완료 | KIS 계정 선택 등록, 기본 `UserTradeConfig` 생성 |
| 비밀번호 재설정 | `POST /auth/reset-password` | 완료 | username+phone 본인확인, 토큰 미발급 방식 |
| 아이디 중복확인 | `GET /auth/check-username` | 완료 | |
| 이메일 중복확인 | `GET /auth/check-email` | 완료 | |
| 토큰 갱신 | `POST /auth/refresh` | 완료 | access token만 재발급, refresh token 재사용 |
| 로그아웃 | `POST /auth/logout` | 완료 | refresh token revoke |
| KIS 계정 검증 | `POST /auth/validate-kis-account` | 완료 | KIS `POST /oauth2/tokenP`로 실검증 |

---

## 2. 사용자 (UserController / UserService)

| 기능 | 엔드포인트 | 상태 | 비고 |
|------|-----------|------|------|
| 프로필 조회 | `GET /users/me` | 완료 | |
| 프로필 수정 | `PUT /users/me` | 완료 | 이메일 중복 검사 |
| 회원 탈퇴 | `DELETE /users/me` | 완료 | RefreshToken·KisAccount·TradeConfig·Settings cascade 삭제 |
| 설정 조회 | `GET /users/settings` | 완료 | `assetOrder`/`notifications` JSON 파싱, 없으면 기본값 생성 |
| 설정 수정 | `PUT /users/settings` | 완료 | |
| KIS 계정 조회 | `GET /users/kis-account` | 완료 | 평문 자격증명 미노출 |
| KIS 계정 수정 | `PUT /users/kis-account` | 완료 | 자격증명 변경 시 `isVerified=false` 리셋 |
| 매매 설정 조회 | `GET /users/trade-config` | 완료 | |
| 매매 설정 수정 | `PUT /users/trade-config` | 완료 | `isActive`(자동매매 ON/OFF) 토글 저장 |

---

## 3. 자산 (AssetController / AssetService)

| 기능 | 엔드포인트 | 상태 | 비고 |
|------|-----------|------|------|
| 보유종목 조회 | `GET /assets/holdings` | 완료 | KIS `VTTC8434R` |
| 예수금 조회 | `GET /assets/balance` | 완료 | holdings 응답의 잔고 추출 |

---

## 4. 매매 (TradingController / TradingService)

| 기능 | 엔드포인트 | 상태 | 비고 |
|------|-----------|------|------|
| 매수 주문 | `POST /trading/buy` | 완료 | KIS `VTTC0802U` |
| 매도 주문 | `POST /trading/sell` | 완료 | KIS `VTTC0801U` |
| 거래내역 조회 | `GET /trading/history` | 완료 | KIS `VTTC0081R`, 최근 3개월. (구버전 `VTTC8001R` 버그 수정됨 — `archive/TRADE_HISTORY_FIX_SUMMARY.md`) |
| 최근 거래(홈) | `GET /trading/recent` | 완료 | DB `trade_history` 최근 8건, KIS 비의존 |
| 보유 잔고 요약 | `GET /trading/holdings` | 완료 | KIS `VTTC8434R` → `BalanceSummaryResponse` |

---

## 5. 종목 정보 (CompanyController / CompanyInfoService)

| 기능 | 엔드포인트 | 상태 | 비고 |
|------|-----------|------|------|
| 기본정보 | `GET /company/{stockCode}/basic-info` | 완료 | KIS 시세(실전) + DART. 시세/DART 키 없으면 해당 필드 null + notice |
| 재무제표 | `GET /company/{stockCode}/financials` | 완료 | KIS 재무(연간), 외부 실패 시 부분 응답 |
| 공시 | `GET /company/{stockCode}/disclosures` | 완료 | DART 약 6개월, 최대 20건 |

---

## 6. 시장 분석 (MarketAnalysisController / MarketAnalysisService)

DB에 적재된 AI 분석 결과 조회. 데이터 생성은 `ai-agent` 모듈 담당.

| 기능 | 엔드포인트 | 상태 | 비고 |
|------|-----------|------|------|
| 시장 요약 | `GET /market/summary` | 완료 | `date` 미지정 시 최신일 fallback |
| 시장 감성 | `GET /market/sentiment` | 완료 | |
| AI 매매 결정 | `GET /market/decisions` | 완료 | buy/sell TOP3 |
| 최신 분석일 | `GET /market/latest-date` | 완료 | 4개 파이프라인 단계 모두 완료된 최신일 |
| 히트맵 | `GET /market/heatmap` | 완료 | 30종목 × 11 ML feature + 요약 |
| 종목 분석 요약 | `GET /market/stock-analysis/{stockCode}` | 완료 | Bot 카드용 |
| 종목 상세 분석 | `GET /market/stock-detail/{stockCode}` | 완료 | quant/sentiment/timeseries(D+1~D+5) |

---

## 7. 시장 데이터 (MarketDataController / MarketDataService)

| 기능 | 엔드포인트 | 상태 | 비고 |
|------|-----------|------|------|
| 지수 | `GET /market/indices` | 완료 | KIS 시세 `FHKUP03500100`. 일부 해외지수 미제공 가능 |
| 환율 | `GET /market/exchange-rates` | 완료 | frankfurter.app(ECB), 60s 캐시 |
| 경제뉴스 | `GET /market/news` | 완료 | RSS 3종, 약 8건, 제목 중복 제거 |

---

## 8. 운영/개발 보조

| 기능 | 엔드포인트 | 상태 | 비고 |
|------|-----------|------|------|
| 헬스 체크 | `GET /health` | 완료 | |
| DB 헬스 체크 | `GET /health/db` | 완료 | |
| BCrypt 유틸 | `GET /test/bcrypt/{password}` | 진행중 | 개발 전용. 운영 배포 전 제거 권장 |

---

## 진행중·미착수 정리

| 항목 | 상태 | 설명 |
|------|------|------|
| KIS 자격증명 복호화 | 진행중 | `KisAuthService`가 Jasypt 복호화 실패 시 평문 fallback(MVP 임시 동작). 모든 계정 암호화 저장으로 정리 필요 |
| `TestController` | 진행중 | 개발용 BCrypt 유틸. 운영에서 노출되지 않도록 제거/비활성 필요 |
| 자동매매 실행 | 미착수(범위 외) | `user_trade_config.isActive` 플래그는 api-server가 저장·관리하나, 실제 자동 주문 실행은 `ai-agent` 스케줄러 담당. api-server에는 스케줄링 로직 없음 |
| 멀티유저 운영 | 진행중 | 인증/도메인은 멀티유저 구조이나 MVP 운영은 단일 관리자 중심 |

---

## 자동화 테스트 현황

`src/test/java/com/inbeom/apiserver/`:

| 테스트 | 대상 |
|--------|------|
| `ApiServerApplicationTests` | 컨텍스트 로드 |
| `AuthServiceTest` | 회원가입/로그인/토큰 로직 |
| `AssetServiceTest` | 잔고·보유종목 조회 |
| `TradingServiceTest` | 매수/매도/거래내역 |
| `KisAuthServiceTest` | KIS 토큰 캐싱/복호화 |

서비스 레이어 단위 테스트 위주이며, 컨트롤러(MockMvc)·리포지토리 통합 테스트는 미작성이다. 실행: `./gradlew test`.

---

## 관련 문서
- [README.md](./README.md) — 문서 인덱스
- [ARCHITECTURE.md](./ARCHITECTURE.md) — 구조·레이어
- [API_DESIGN.md](./API_DESIGN.md) — 엔드포인트 명세
