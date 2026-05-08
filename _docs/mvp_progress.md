# MVP 진행상황 현황

> 프로젝트 진행 현황을 큰 기능 단위별로 추적하는 문서입니다.

## 📋 기능 범위 (MVP Scope)

| 대분류 | 설명 | 상태 |
|--------|------|------|
| 🔐 로그인/인증 | 사용자 인증 및 회원가입 | ✅ 완료 |
| 👤 내정보 | 사용자 정보 관리 | ⚠️ 부분 완료 |
| 🤖 AI분석 | AI 기반 주식 분석 | 📅 계획 |
| 📊 거래내역 | 거래 이력 조회 | 📅 계획 |

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
| 내 정보 조회 | ⏸️ | ⏸️ | ⏸️ | API 미구현 |
| 프로필 수정 | ⏸️ | ⏸️ | ⏸️ | API 미구현 |

### 투자 설정 관리
| 항목 | API-Server | Web-App | 연동 | 비고 |
|------|-----------|---------|------|------|
| GET /users/trade-config | ✅ | ✅ | ✅ | UserController.java:27-39, SettingsView.vue:55-68 |
| PUT /users/trade-config | ✅ | ✅ | ✅ | UserController.java:45-58, SettingsView.vue:70-95 |
| 투자 설정 화면 | ✅ | ✅ | ✅ | SettingsView.vue (자동거래, 주문금액, 최대보유종목수, 주문유형) |

### 계정 관리
| 항목 | API-Server | Web-App | 연동 | 비고 |
|------|-----------|---------|------|------|
| DELETE /users/me | ✅ | ✅ | ✅ | UserController.java:64-77, SettingsView.vue:108-128 |
| 회원 탈퇴 화면 | ✅ | ✅ | ✅ | SettingsView.vue (확인 다이얼로그 + API 호출 + /welcome 이동) |

---

## 🤖 AI분석

| 항목 | API-Server | AI-Agent | Web-App | 연동 | 비고 |
|------|-----------|----------|---------|------|------|
| AI 분석 결과 조회 | 📅 | 📅 | 📅 | 📅 | 미구현 |
| 차트 데이터 조회 | 📅 | 📅 | 📅 | 📅 | 미구현 |
| 종목 추천 조회 | 📅 | 📅 | 📅 | 📅 | 미구현 |

---

## 📊 거래내역

| 항목 | API-Server | Web-App | 연동 | 비고 |
|------|-----------|---------|------|------|
| GET /trading/history | ✅ | ⏸️ | ⏸️ | TradingController.java 구현 완료 |
| 거래내역 화면 | ⏸️ | ⏸️ | ⏸️ | Vue 컴포넌트 미구현 |
| POST /trading/buy | ✅ | ⏸️ | ⏸️ | TradingController.java 구현 완료 |
| POST /trading/sell | ✅ | ⏸️ | ⏸️ | TradingController.java 구현 완료 |

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

**작성일**: 2025-05-08
**작성자**: Claude Code
**다음 작업**: AI 분석 및 거래내역 기능 개발
