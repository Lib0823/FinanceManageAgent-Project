# MVP 진행상황 현황

> 프로젝트 진행 현황을 큰 기능 단위별로 추적하는 문서입니다.

## 📋 기능 범위 (MVP Scope)

| 대분류 | 설명 | 상태 |
|--------|------|------|
| 🔐 로그인/인증 | 사용자 인증 및 회원가입 | ✅ 완료 |
| 👤 내정보 | 사용자 정보 관리 | ✅ 완료 |
| 🤖 AI분석 | AI 기반 주식 분석 | 📅 계획 |
| 📊 거래내역 | 거래 이력 조회 | ✅ 완료 |

---

## 🔐 로그인/인증

### 1️⃣ 로그인

#### API-Server (Spring Boot)
| 항목 | 상태 | 구현 파일 | 비고 |
|------|------|-----------|------|
| POST /auth/login | ✅ | AuthController.java:19-23 | LoginRequest DTO 검증 포함 |
| 비즈니스 로직 | ✅ | AuthService.java:88-123 | JWT 토큰 생성, KIS 계좌 조회 |
| 토큰 생성 | ✅ | JwtTokenProvider.java | AccessToken + RefreshToken |
| RefreshToken 저장 | ✅ | AuthService.java:210-229 | DB에 저장, 기존 토큰 revoke |

#### Web-App (Vue3)
| 항목 | 상태 | 구현 파일 | 비고 |
|------|------|-----------|------|
| 로그인 화면 | ✅ | LoginView.vue | Username/Password 입력 폼 |
| API 호출 | ✅ | api.js:93 | authApi.login() |
| 상태 관리 | ✅ | stores/auth.js:97-106 | Pinia store (토큰/사용자 정보) |
| LocalStorage 저장 | ✅ | stores/auth.js:103-105 | accessToken, refreshToken, user |

#### 화면-API 연동
| 항목 | 상태 | 비고 |
|------|------|------|
| 로그인 성공 시 토큰 저장 | ✅ | authStore.setAuthData() 호출 |
| 로그인 성공 시 /home 이동 | ✅ | router.push('/home') |
| 에러 핸들링 | ✅ | Toast 메시지 표시 |

---

### 2️⃣ 회원가입

#### API-Server (Spring Boot)
| 항목 | 상태 | 구현 파일 | 비고 |
|------|------|-----------|------|
| POST /auth/register | ✅ | AuthController.java:25-30 | RegisterRequest DTO 검증 포함 |
| 비즈니스 로직 | ✅ | AuthService.java:33-86 | User + KIS Account + TradeConfig 생성 |
| 중복 확인 (아이디) | ✅ | AuthController.java:38-43 | GET /auth/check-username |
| 중복 확인 (이메일) | ✅ | AuthController.java:45-50 | GET /auth/check-email |
| 비밀번호 암호화 | ✅ | AuthService.java:51 | PasswordEncoder 사용 |

#### Web-App (Vue3)
| 항목 | 상태 | 구현 파일 | 비고 |
|------|------|-----------|------|
| 회원가입 1단계 (기본정보) | ✅ | RegisterView.vue | ID, PW, 이름, 휴대폰, 생년월일 |
| 회원가입 2단계 (금융정보) | ✅ | RegisterFinanceView.vue | KIS 계좌번호, APP Key/Secret |
| 아이디 중복 확인 | ✅ | RegisterView.vue:41-66 | authApi.checkUsername() |
| 이메일 중복 확인 | ✅ | RegisterView.vue:68-100 | authApi.checkEmail() |
| 휴대폰 인증 | ⚠️ | RegisterView.vue:102-119 | 개발 중 - 임시 우회 처리 |
| 상태 관리 (Step1) | ✅ | stores/auth.js:39-49 | Pinia store |
| 상태 관리 (Step2) | ✅ | stores/auth.js:51-56 | Pinia store |

#### 화면-API 연동
| 항목 | 상태 | 비고 |
|------|------|------|
| 아이디 중복 확인 연동 | ✅ | RegisterView.vue:41-66 → authApi.checkUsername() |
| 이메일 중복 확인 연동 | ✅ | RegisterView.vue:68-100 → authApi.checkEmail() |
| 회원가입 요청 | ✅ | Step1 + Step2 데이터 합쳐서 authApi.register() 호출 |
| 성공 시 /terms 이동 | ✅ | 약관 동의 화면으로 이동 |
| 에러 핸들링 | ✅ | 중복 에러 시 Step1으로 복귀 |

---

### 3️⃣ 자동 로그인

#### API-Server (Spring Boot)
| 항목 | 상태 | 구현 파일 | 비고 |
|------|------|-----------|------|
| RefreshToken 저장 | ✅ | AuthService.java:210-229 | DB에 저장 (expires_at 포함) |
| POST /auth/refresh | ✅ | AuthController.java:52-56 | RefreshToken으로 새 AccessToken 발급 |
| 토큰 검증 | ✅ | AuthService.java:166-168 | jwtTokenProvider.validateToken() |

#### Web-App (Vue3)
| 항목 | 상태 | 구현 파일 | 비고 |
|------|------|-----------|------|
| LocalStorage에서 토큰 로드 | ✅ | stores/auth.js:119-131 | loadAuthDataFromStorage() |
| 자동 로그인 체크박스 | ✅ | LoginView.vue:119 | uiSettings에 저장 |
| 토큰 자동 갱신 | ✅ | api.js:32-88 | Response 인터셉터 (401 시 자동 리프레시) |

#### 화면-API 연동
| 항목 | 상태 | 비고 |
|------|------|------|
| 앱 시작 시 토큰 확인 | ✅ | stores/auth.js:119-131 |
| 토큰 만료 시 자동 갱신 | ✅ | api.js Response 인터셉터에서 처리 |
| 갱신 실패 시 로그아웃 | ✅ | localStorage.clear() + /login 이동 |

---

### 4️⃣ 로그아웃

#### API-Server (Spring Boot)
| 항목 | 상태 | 구현 파일 | 비고 |
|------|------|-----------|------|
| POST /auth/logout | ✅ | AuthController.java:58-62 | RefreshToken revoke |
| RefreshToken revoke | ✅ | AuthService.java:196-208 | revoked_at 컬럼 업데이트 |

#### Web-App (Vue3)
| 항목 | 상태 | 구현 파일 | 비고 |
|------|------|-----------|------|
| 로그아웃 함수 | ✅ | stores/auth.js:133-145 | authApi.logout() 호출 후 clearAuthData() |
| LocalStorage 삭제 | ✅ | stores/auth.js:108-117 | clearAuthData() |

#### 화면-API 연동
| 항목 | 상태 | 비고 |
|------|------|------|
| 로그아웃 API 호출 | ✅ | authStore.logout() |
| 로컬 데이터 삭제 | ✅ | localStorage 완전 삭제 |

---

### 5️⃣ 비밀번호 재설정

#### API-Server (Spring Boot)
| 항목 | 상태 | 구현 파일 | 비고 |
|------|------|-----------|------|
| POST /auth/reset-password | ✅ | AuthController.java:32-36 | ResetPasswordRequest DTO |
| 본인 확인 (ID + 휴대폰) | ✅ | AuthService.java:132-138 | username + phone 일치 확인 |
| 비밀번호 변경 | ✅ | AuthService.java:141-142 | 암호화 후 DB 업데이트 |

#### Web-App (Vue3)
| 항목 | 상태 | 구현 파일 | 비고 |
|------|------|-----------|------|
| 비밀번호 재설정 화면 | ✅ | ResetPasswordView.vue | 아이디, 휴대폰, 새 비밀번호 입력 |
| 휴대폰 인증 | ⚠️ | ResetPasswordView.vue:19-34 | 개발 중 - 임시 우회 처리 |
| API 호출 | ✅ | api.js:95 | authApi.resetPassword() |

#### 화면-API 연동
| 항목 | 상태 | 비고 |
|------|------|------|
| 재설정 성공 시 /login 이동 | ✅ | 1초 후 자동 이동 |
| 에러 핸들링 | ✅ | Toast 메시지 표시 |

---

## 👤 내정보

### 사용자 정보 조회
| 항목 | API-Server | Web-App | 연동 | 비고 |
|------|-----------|---------|------|------|
| GET /users/me | ✅ | ✅ | ✅ | UserController.java:29-40, UserService.java:95-109 |
| PUT /users/me | ✅ | ✅ | ✅ | UserController.java:47-60, UserService.java:115-144, ProfileView.vue:58-102 |

### 설정 화면
| 항목 | API-Server | Web-App | 연동 | 비고 |
|------|-----------|---------|------|------|
| GET /users/settings | ✅ | ✅ | ✅ | UserController.java:46-58, SettingsView.vue:46-65 |
| PUT /users/settings | ✅ | ✅ | ✅ | UserController.java:64-77, SettingsView.vue:67-89 |
| 관심 자산 순위 | ✅ | ✅ | ✅ | user_settings.asset_order (JSONB), 드래그앤드롭 지원 |
| 일반 설정 | ✅ | ✅ | ✅ | user_settings.dark_mode, auto_login (BOOLEAN) |
| 알림 설정 | ✅ | ✅ | ✅ | user_settings.notifications (JSONB) |

### 계정 관리
| 항목 | API-Server | Web-App | 연동 | 비고 |
|------|-----------|---------|------|------|
| DELETE /users/me | ✅ | ✅ | ✅ | UserController.java:83-95, SettingsView.vue:108-122 |
| 회원 탈퇴 화면 | ✅ | ✅ | ✅ | SettingsView.vue (확인 다이얼로그 + API 호출 + /welcome 이동) |
| 로그아웃 | ✅ | ✅ | ✅ | SettingsView.vue:91-97 (AuthStore 연동 + /login 이동) |

---

## 🤖 투자 봇 (BotView)

### 거래 설정 관리 (Trade Configuration)
| 항목 | API-Server | Web-App | 연동 | 비고 |
|------|-----------|---------|------|------|
| GET /users/trade-config | ✅ | ✅ | ✅ | UserController.java:153-168, UserService.java:45-60 |
| PUT /users/trade-config | ✅ | ✅ | ✅ | UserController.java:174-187, UserService.java:65-91 |
| 투자금액 설정 | ✅ | ✅ | ✅ | orderAmount (Long), BotView.vue:42-53, 97-133 |
| 봇 활성화 토글 | ✅ | ✅ | ✅ | isActive (Boolean), BotView.vue:114-119 |
| 설정 저장 기능 | ✅ | ✅ | ✅ | maxHoldings, orderType 기본값 유지 |

### 보유 종목 조회 (Holdings)
| 항목 | API-Server | Web-App | 연동 | 비고 |
|------|-----------|---------|------|------|
| GET /trading/holdings | ✅ | ✅ | ✅ | TradingController.java:99-116, TradingService.java:261-354 |
| KIS API 연동 | ✅ | - | ✅ | TR_ID: VTTC8434R (주식잔고조회), KisBalanceResponse DTO |
| 보유 종목 목록 | ✅ | ✅ | ✅ | BalanceSummaryResponse.holdings (List<HoldingResponse>) |
| 평가금액 표시 | ✅ | ✅ | ✅ | HoldingResponse.evaluationAmount |
| 평가손익 표시 | ✅ | ✅ | ✅ | HoldingResponse.profitLoss + profitLossRate |
| 매도가능수량 표시 | ✅ | ✅ | ✅ | HoldingResponse.availableQuantity |
| 평균단가 표시 | ✅ | ✅ | ✅ | HoldingResponse.averagePrice |
| 총 평가금액 | ✅ | ✅ | ✅ | BalanceSummaryResponse.totalEvaluationAmount |
| 현금 잔고 | ✅ | ✅ | ✅ | BalanceSummaryResponse.cashBalance |
| AI 분석 | ⏸️ | ✅ | ⏸️ | Mock 데이터로 임시 표시 |

### BotView 화면 구성
| 항목 | 상태 | 구현 파일 | 비고 |
|------|------|-----------|------|
| 투자 봇 상태 표시 | ✅ | BotView.vue:104-204 | 총 평가금액, 수익률, 활성화 상태 |
| 투자금액 섹션 | ✅ | BotView.vue:206-218 | 투자금액 표시 + 설정 버튼 |
| 설정 모달 | ✅ | BotView.vue:336-399 | 봇 활성화, 투자금액, 시장 선택 |
| 보유 종목 카드 | ✅ | BotView.vue:242-330 | 종목 정보, 평가 데이터, AI 분석 |
| API 연동 | ✅ | BotView.vue:55-136 | onMounted에서 loadTradeConfig, loadHoldings 호출 |

### DTO 구조
| DTO | 역할 | 필드 | 비고 |
|-----|------|------|------|
| TradeConfigResponse | 거래 설정 응답 | id, orderAmount, maxHoldings, orderType, isActive | UserService.java:48-56 |
| UpdateTradeConfigRequest | 거래 설정 수정 요청 | orderAmount, maxHoldings, orderType, isActive | 모든 필드 필수 (Validation) |
| BalanceSummaryResponse | 보유 종목 요약 | holdings (List), totalEvaluationAmount, cashBalance 등 | TradingService.java:328-335 |
| HoldingResponse | 개별 보유 종목 | stockCode, stockName, holdingQuantity, evaluationAmount 등 | TradingService.java:342-353 |
| KisBalanceResponse | KIS API 응답 | Output1 (종목별), Output2 (요약) | TR_ID: VTTC8434R |

### 데이터 흐름
```
1. 거래 설정
   - Frontend: BotView.vue (설정 모달 → saveSettings())
   - API: PUT /users/trade-config (UpdateTradeConfigRequest)
   - Backend: UserService.updateTradeConfig() → user_trade_config 테이블 UPDATE
   - Response: TradeConfigResponse

2. 보유 종목 조회
   - Frontend: BotView.vue (onMounted → loadHoldings())
   - API: GET /trading/holdings
   - Backend: TradingService.getHoldings() → KIS API (VTTC8434R) 호출
   - KIS Response: KisBalanceResponse (Output1 + Output2)
   - Mapping: mapToHoldingResponse() → HoldingResponse
   - Response: BalanceSummaryResponse
```

## 🤖 AI분석

| 항목 | API-Server | AI-Agent | Web-App | 연동 | 비고 |
|------|-----------|----------|---------|------|------|
| AI 분석 결과 조회 | 📅 | 📅 | 📅 | 📅 | 미구현 |
| 차트 데이터 조회 | 📅 | 📅 | 📅 | 📅 | 미구현 |
| 종목 추천 조회 | 📅 | 📅 | 📅 | 📅 | 미구현 |

---

## 📊 거래내역

### 거래내역 조회 (Trade History)
| 항목 | API-Server | Web-App | 연동 | 비고 |
|------|-----------|---------|------|------|
| GET /trading/history | ✅ | ✅ | ✅ | KIS API (VTTC8001R) 직접 조회, 최근 3개월 |
| 거래내역 화면 | ✅ | ✅ | ✅ | TransactionsView.vue, tradingApi.getHistory() |
| KIS API 연동 | ✅ | - | ✅ | TradingService.java:140-192, KisDailyCcldResponse DTO |
| 응답 DTO | ✅ | - | ✅ | TradeHistoryResponse (id, stockCode, stockName, orderType, orderStatus, etc.) |
| Data Source | KIS API | - | - | **DB 저장 없음** (데이터 정합성 보장) |

### 주문 실행 (Trading Orders)
| 항목 | API-Server | Web-App | 연동 | 비고 |
|------|-----------|---------|------|------|
| POST /trading/buy | ✅ | ⏸️ | ⏸️ | KIS API (VTTC0802U), DB 저장 제거 |
| POST /trading/sell | ✅ | ⏸️ | ⏸️ | KIS API (VTTC0801U), DB 저장 제거 |

---

## 범례 (Legend)

- ✅ 완료 (Completed)
- 🔄 진행 중 (In Progress)
- ⏸️ 대기 (Pending)
- ⚠️ 부분 완료 / 임시 처리 (Partial / Workaround)
- 📅 계획 (Planned)
- ❌ 중단 (Blocked)

---

## 최종 업데이트

**작성일**: 2026-05-22
**작성자**: Claude Code
**다음 작업**: AI 분석 기능 개발

**최근 변경사항** (투자 봇 BotView 기능 완료):
- **거래 설정 관리 API 개발 및 연동 완료**
  - GET /users/trade-config: 거래 설정 조회 (UserController.java:153-168)
  - PUT /users/trade-config: 거래 설정 수정 (UserController.java:174-187)
  - UserService.getTradeConfig(), updateTradeConfig() 비즈니스 로직 구현
  - BotView.vue API 연동 (투자금액 설정, 봇 활성화 토글)

- **보유 종목 조회 API 개발 및 연동 완료**
  - GET /trading/holdings: KIS API 직접 조회 (TradingController.java:99-116)
  - TradingService.getHoldings(): KIS API (VTTC8434R) 통합 (TradingService.java:261-354)
  - KisBalanceResponse, HoldingResponse, BalanceSummaryResponse DTO 생성
  - BotView.vue 보유 종목 카드 표시 (평가금액, 평가손익, 매도가능수량, 평균단가)

- **BotView 화면 완전 연동**
  - 투자 봇 상태 표시 (총 평가금액, 수익률, 활성화 상태)
  - 투자금액 설정 및 저장 기능
  - 설정 모달 (봇 활성화, 투자금액, 시장 선택)
  - 보유 종목 카드 UI (AI 분석은 mock 데이터로 임시 표시)
  - web-app/src/services/api.js: userApi.getTradeConfig(), updateTradeConfig(), tradingApi.getHoldings() 추가

**이전 변경사항** (거래내역 기능):
- **KIS API 직접 조회 방식으로 리팩토링** (데이터 정합성 보장)
- KisDailyCcldResponse DTO 생성 (TR_ID: VTTC8001R, 최근 3개월 조회)
- TradeHistoryResponse DTO 생성 (id, stockCode, stockName, orderType, orderStatus, etc.)
- TradingService.getTradeHistory() KIS API 호출로 변경 (TradingService.java:140-280)
- TradingController return type 변경 (List<TradeHistory> → List<TradeHistoryResponse>)
- **trade_history 테이블 DB 저장 제거** (executeBuy/executeSell 메서드)
- TradeHistoryRepository 의존성 제거 (TradingService, UserService)
- TransactionsView.vue 기존 연동 확인 완료 (tradingApi.getHistory())
- 거래내역 화면 완전 연동 완료

**더 이전 변경사항**:
- user_settings 테이블 추가 및 DB 저장 기능 구현
- 사용자 프로필 조회/수정 API 구현 (GET /users/me, PUT /users/me)
- 로그인/인증 및 내정보 기능 100% 완료
