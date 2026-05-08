# 인증 흐름 및 API 구분 (멀티 유저 환경)

## 📋 목차
1. [인증 방식 개요](#1-인증-방식-개요)
2. [API 종류별 인증 구분](#2-api-종류별-인증-구분)
3. [KIS API Key 관리 전략](#3-kis-api-key-관리-전략)
4. [인증 흐름도](#4-인증-흐름도)
5. [구현 가이드](#5-구현-가이드)

---

## 1. 인증 방식 개요

### 1.1 2단계 인증 구조

```
사용자 로그인
    ↓
[1단계] JWT 인증 (자체 시스템)
    ├─ Access Token (1시간)
    ├─ Refresh Token (24시간)
    └─ Payload에 user_id + kis_account_id 포함
    ↓
[2단계] KIS API 인증 (증권사)
    ├─ 사용자별 AppKey/AppSecret (DB 암호화 저장)
    ├─ KIS Access Token (24시간, 메모리 캐싱)
    └─ API 호출 시마다 헤더에 포함
```

### 1.2 인증 정보 저장 위치

| 정보 | 저장 위치 | 암호화 | 유효기간 |
|------|----------|--------|----------|
| **사용자 비밀번호** | DB (users.password) | BCrypt | 영구 |
| **JWT Secret** | 환경변수 | - | - |
| **KIS AppKey/AppSecret** | DB (user_kis_account) | Jasypt | 영구 |
| **JWT Access Token** | 클라이언트 (localStorage) | - | 1시간 |
| **JWT Refresh Token** | DB (refresh_tokens) | - | 24시간 |
| **KIS Access Token** | 서버 메모리 (캐시) | - | 24시간 |

---

## 2. API 종류별 인증 구분

### 2.1 인증 방식 분류

| API 종류 | 필요한 인증 | 예시 |
|---------|-----------|------|
| **Type A: 자체 인증만** | JWT 토큰 | 사용자 정보 조회, 설정 조회 |
| **Type B: KIS 인증만** | KIS API Key | 종목 시세 조회 (로그인 불필요) |
| **Type C: 자체 + KIS 인증** | JWT + KIS API Key | 잔고 조회, 주문 실행 |

### 2.2 API별 상세 분류

#### Type A: 자체 JWT 인증만 필요

| API | Method | 인증 헤더 | 데이터 소스 |
|-----|--------|-----------|------------|
| `POST /api/auth/login` | POST | ❌ None | RDB (users) |
| `POST /api/auth/register` | POST | ❌ None | RDB (users) |
| `POST /api/auth/refresh` | POST | Refresh Token | RDB (refresh_tokens) |
| `GET /api/users/profile` | GET | ✅ JWT | RDB (users) |
| `PUT /api/users/profile` | PUT | ✅ JWT | RDB (users) |
| `GET /api/settings/trading` | GET | ✅ JWT | RDB (user_trade_config) |
| `PUT /api/settings/trading` | PUT | ✅ JWT | RDB (user_trade_config) |
| `GET /api/notifications` | GET | ✅ JWT | RDB (notifications) |
| `GET /api/ai/recommendations` | GET | ✅ JWT | RDB (ai_trade_decision) |
| `GET /api/bot/status` | GET | ✅ JWT | RDB (user_trade_config) |

#### Type B: KIS 인증만 필요 (공개 시세 정보)

> **주의**: 실제로는 FastAPI를 통해 제공되므로 Spring Boot에서는 구현하지 않음

| API | Method | 인증 헤더 | 데이터 소스 |
|-----|--------|-----------|------------|
| `GET /api/market/indices` | GET | ❌ None (FastAPI 경유) | KIS API (지수 조회) |
| `GET /api/market/current-price/{code}` | GET | ❌ None (FastAPI 경유) | KIS API (현재가) |
| `GET /api/market/daily-price/{code}` | GET | ❌ None (FastAPI 경유) | KIS API (일별시세) |

**구현 방식**: FastAPI가 자체 KIS API Key로 조회 후 Spring Boot로 전달하거나 Vue3가 직접 FastAPI 호출

#### Type C: JWT + KIS 인증 모두 필요

| API | Method | 인증 헤더 | 데이터 소스 |
|-----|--------|-----------|------------|
| `GET /api/assets/summary` | GET | ✅ JWT | JWT → user_id → KIS AppKey → KIS API (잔고) |
| `GET /api/assets/holdings` | GET | ✅ JWT | JWT → user_id → KIS AppKey → KIS API (잔고) |
| `GET /api/trading/buyable-amount` | GET | ✅ JWT | JWT → user_id → KIS AppKey → KIS API (매수가능) |
| `POST /api/trading/buy` | POST | ✅ JWT | JWT → user_id → KIS AppKey → KIS API (매수주문) |
| `POST /api/trading/sell` | POST | ✅ JWT | JWT → user_id → KIS AppKey → KIS API (매도주문) |
| `PUT /api/trading/orders/{id}` | PUT | ✅ JWT | JWT → user_id → KIS AppKey → KIS API (주문정정) |
| `DELETE /api/trading/orders/{id}` | DELETE | ✅ JWT | JWT → user_id → KIS AppKey → KIS API (주문취소) |

---

## 3. KIS API Key 관리 전략

### 3.1 문제점: 매번 DB 조회는 비효율적

```java
// ❌ 나쁜 예: 매 API 호출마다 DB 조회
@GetMapping("/assets/holdings")
public ApiResponse getHoldings(@AuthenticationPrincipal UserDetails user) {
    // 1. DB에서 KIS 계정 조회
    UserKisAccount kisAccount = kisAccountRepository.findByUserId(user.getId());

    // 2. DB에서 암호화된 AppKey/AppSecret 복호화
    String appKey = encryptor.decrypt(kisAccount.getAppKey());
    String appSecret = encryptor.decrypt(kisAccount.getAppSecret());

    // 3. KIS API 호출
    return kisApiService.getBalance(appKey, appSecret);
}
// 문제: API 호출마다 DB 조회 + 복호화 발생!
```

### 3.2 해결 방안: JWT Payload에 kis_account_id 포함

#### 3.2.1 JWT 토큰 구조

```json
{
  "sub": "testuser",
  "userId": 1,
  "kisAccountId": 123,  // ← user_kis_account.id
  "role": "USER",
  "iat": 1714617600,
  "exp": 1714621200
}
```

#### 3.2.2 KIS 인증 정보 캐싱 전략

```java
@Service
public class KisAuthService {

    // 사용자별 KIS Access Token 캐시 (메모리)
    // Key: kis_account_id, Value: {accessToken, expiresAt}
    private final Map<Long, KisTokenCache> userKisTokens = new ConcurrentHashMap<>();

    /**
     * 사용자별 KIS Access Token 조회
     * 1. 캐시에서 조회 (유효하면 반환)
     * 2. 캐시 없거나 만료 시 → DB 조회 + 토큰 발급 + 캐싱
     */
    public String getKisAccessToken(Long kisAccountId) {
        // 1. 캐시 확인
        KisTokenCache cached = userKisTokens.get(kisAccountId);
        if (cached != null && !cached.isExpired()) {
            return cached.getAccessToken();
        }

        // 2. DB에서 KIS 계정 조회 (최초 1회만)
        UserKisAccount kisAccount = kisAccountRepository.findById(kisAccountId)
            .orElseThrow(() -> new IllegalArgumentException("KIS 계정 정보가 없습니다."));

        // 3. 암호화된 AppKey/AppSecret 복호화
        String appKey = encryptor.decrypt(kisAccount.getAppKey());
        String appSecret = encryptor.decrypt(kisAccount.getAppSecret());

        // 4. KIS API 토큰 발급
        String accessToken = kisTokenClient.issueToken(appKey, appSecret);

        // 5. 캐시에 저장 (24시간)
        userKisTokens.put(kisAccountId, new KisTokenCache(accessToken, 24 * 60 * 60));

        return accessToken;
    }
}
```

#### 3.2.3 API 호출 흐름 (최적화)

```java
@GetMapping("/assets/holdings")
public ApiResponse getHoldings(@AuthenticationPrincipal CustomUserDetails user) {
    // 1. JWT에서 kis_account_id 추출 (DB 조회 없음!)
    Long kisAccountId = user.getKisAccountId();

    // 2. 캐시에서 KIS Access Token 조회 (최초 1회만 DB 조회)
    String kisAccessToken = kisAuthService.getKisAccessToken(kisAccountId);

    // 3. KIS API 호출
    return kisApiService.getBalance(kisAccessToken);
}
```

**성능 개선**:
- 매 API 호출: 0회 DB 조회 (캐시 히트 시)
- 최초 호출 또는 토큰 만료: 1회 DB 조회 + 암호화 복호화

---

## 4. 인증 흐름도

### 4.1 로그인 흐름

```
[Vue3] → POST /api/auth/login {username, password}
            ↓
    [Spring Boot] 1. users 테이블에서 사용자 조회
                  2. 비밀번호 검증 (BCrypt)
                  3. user_kis_account 테이블에서 kis_account_id 조회
                  4. JWT 생성 (payload: userId + kisAccountId)
            ↓
    [Vue3] ← {accessToken, refreshToken, user}
            ↓
    localStorage에 토큰 저장
```

### 4.2 KIS API 호출 흐름 (잔고 조회 예시)

```
[Vue3] → GET /api/assets/holdings
         Authorization: Bearer {JWT}
            ↓
    [Spring Boot] 1. JWT 검증 및 파싱
                     - userId = 1
                     - kisAccountId = 123
                  2. KisAuthService.getKisAccessToken(123)
                     - 캐시 확인
                     - 없으면 DB 조회 + 복호화 + KIS 토큰 발급
                  3. KIS API 호출
                     - authorization: Bearer {KIS_ACCESS_TOKEN}
                     - appkey: {복호화된 AppKey}
                     - appsecret: {복호화된 AppSecret}
            ↓
    [KIS API] ← GET /uapi/domestic-stock/v1/trading/inquire-balance
            ↓
    [Spring Boot] ← KIS 응답 수신
                  4. DTO 변환
            ↓
    [Vue3] ← {holdings: [...]}
```

### 4.3 시세 조회 흐름 (FastAPI 경유)

```
[Vue3] → GET /api/market/current-price/005930
            ↓
    [FastAPI] 1. FastAPI 자체 KIS API Key 사용 (환경변수)
              2. KIS API 호출 (시세 조회)
              3. 캐싱 (30초)
            ↓
    [Vue3] ← {stockCode: "005930", currentPrice: 71000, ...}
```

---

## 5. 구현 가이드

### 5.1 JWT CustomUserDetails

```java
public class CustomUserDetails implements UserDetails {
    private Long userId;
    private String username;
    private Long kisAccountId;  // ← JWT에서 추출
    private Collection<? extends GrantedAuthority> authorities;

    // Getters
    public Long getUserId() { return userId; }
    public Long getKisAccountId() { return kisAccountId; }
}
```

### 5.2 JWT 생성 시 kis_account_id 포함

```java
@Service
public class JwtTokenProvider {

    public String generateAccessToken(User user) {
        // user_kis_account 조회
        UserKisAccount kisAccount = kisAccountRepository.findByUserId(user.getId())
            .orElse(null);

        Long kisAccountId = (kisAccount != null) ? kisAccount.getId() : null;

        return Jwts.builder()
            .setSubject(user.getUsername())
            .claim("userId", user.getId())
            .claim("kisAccountId", kisAccountId)  // ← 포함
            .claim("role", "USER")
            .setIssuedAt(new Date())
            .setExpiration(new Date(System.currentTimeMillis() + accessTokenExpiration))
            .signWith(SignatureAlgorithm.HS512, jwtSecret)
            .compact();
    }
}
```

### 5.3 KisAuthService 구현

```java
@Service
@RequiredArgsConstructor
public class KisAuthService {

    private final UserKisAccountRepository kisAccountRepository;
    private final StringEncryptor encryptor;
    private final KisTokenClient kisTokenClient;

    // 사용자별 KIS Token 캐시
    private final Map<Long, KisTokenCache> tokenCache = new ConcurrentHashMap<>();

    public String getKisAccessToken(Long kisAccountId) {
        // 1. 캐시 확인
        KisTokenCache cached = tokenCache.get(kisAccountId);
        if (cached != null && !cached.isExpired()) {
            log.debug("KIS token cache hit: {}", kisAccountId);
            return cached.getAccessToken();
        }

        // 2. DB 조회 및 토큰 발급
        log.info("KIS token cache miss: {}. Issuing new token.", kisAccountId);
        UserKisAccount account = kisAccountRepository.findById(kisAccountId)
            .orElseThrow(() -> new IllegalArgumentException("KIS 계정이 없습니다."));

        String appKey = encryptor.decrypt(account.getAppKey());
        String appSecret = encryptor.decrypt(account.getAppSecret());

        String accessToken = kisTokenClient.issueToken(appKey, appSecret);

        // 3. 캐시 저장 (24시간)
        tokenCache.put(kisAccountId, new KisTokenCache(accessToken, 24 * 60 * 60));

        return accessToken;
    }

    @Getter
    @AllArgsConstructor
    private static class KisTokenCache {
        private final String accessToken;
        private final LocalDateTime expiresAt;

        public KisTokenCache(String accessToken, long expiresInSeconds) {
            this.accessToken = accessToken;
            this.expiresAt = LocalDateTime.now().plusSeconds(expiresInSeconds);
        }

        public boolean isExpired() {
            return LocalDateTime.now().isAfter(expiresAt);
        }
    }
}
```

### 5.4 Controller에서 사용

```java
@RestController
@RequestMapping("/api/assets")
@RequiredArgsConstructor
public class AssetsController {

    private final KisAuthService kisAuthService;
    private final KisApiService kisApiService;

    @GetMapping("/holdings")
    public ApiResponse<List<HoldingDto>> getHoldings(
        @AuthenticationPrincipal CustomUserDetails user
    ) {
        // 1. JWT에서 kis_account_id 추출
        Long kisAccountId = user.getKisAccountId();
        if (kisAccountId == null) {
            throw new IllegalStateException("KIS 계정이 연동되지 않았습니다.");
        }

        // 2. KIS Access Token 조회 (캐시 우선)
        String kisAccessToken = kisAuthService.getKisAccessToken(kisAccountId);

        // 3. KIS API 호출
        List<HoldingDto> holdings = kisApiService.getHoldings(kisAccessToken);

        return ApiResponse.success(holdings);
    }
}
```

---

## 6. 보안 고려사항

### 6.1 암호화 방식 (Jasypt)

```yaml
# application.yml
jasypt:
  encryptor:
    password: ${JASYPT_PASSWORD}  # 환경변수로 관리
    algorithm: PBEWithMD5AndDES
    pool-size: 1
```

### 6.2 KIS 계정 미연동 사용자 처리

```java
@GetMapping("/assets/holdings")
public ApiResponse getHoldings(@AuthenticationPrincipal CustomUserDetails user) {
    if (user.getKisAccountId() == null) {
        return ApiResponse.error("KIS_ACCOUNT_NOT_LINKED",
            "한국투자증권 계정을 먼저 연동해주세요.");
    }
    // ...
}
```

### 6.3 토큰 캐시 무효화 (계정 정보 변경 시)

```java
@PutMapping("/users/kis-account")
public ApiResponse updateKisAccount(@RequestBody UpdateKisAccountRequest request) {
    // KIS 계정 정보 업데이트
    userKisAccountRepository.save(...);

    // 캐시 무효화
    kisAuthService.invalidateCache(kisAccountId);

    return ApiResponse.success("KIS 계정이 업데이트되었습니다.");
}
```

---

## 7. 최종 요약

### API 인증 방식 요약표

| API 종류 | JWT 필요 | KIS 인증 필요 | 데이터 소스 | 예시 |
|---------|---------|-------------|------------|------|
| **Type A** | ✅ | ❌ | RDB | 프로필 조회, 설정 조회, AI 분석 결과 |
| **Type B** | ❌ | ✅ | KIS API (FastAPI) | 시세 조회 (공개 정보) |
| **Type C** | ✅ | ✅ | RDB + KIS API | 잔고 조회, 주문 실행 |

### 성능 최적화 핵심

1. **JWT Payload에 kis_account_id 포함** → DB 조회 불필요
2. **KIS Access Token 메모리 캐싱** → 24시간 재사용
3. **최초 1회만 DB 조회 + 암호화 복호화** → 이후 캐시 사용

### 구현 체크리스트

- [ ] CustomUserDetails에 kisAccountId 필드 추가
- [ ] JwtTokenProvider에서 kis_account_id를 JWT에 포함
- [ ] KisAuthService 구현 (캐싱 로직)
- [ ] Jasypt 설정 (KIS AppKey/AppSecret 암호화)
- [ ] Controller에서 @AuthenticationPrincipal 사용
- [ ] KIS 계정 미연동 사용자 에러 처리
