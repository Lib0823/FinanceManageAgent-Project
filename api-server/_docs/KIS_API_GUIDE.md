# KIS API 연동 가이드

> 한국투자증권(KIS) Open API 연동 구조를 코드 기준으로 정리합니다. 두 개의 분리된 자격증명 경로, 토큰 캐싱, TR_ID 매핑, DART/Jasypt 연동을 다룹니다.

## 목차
1. [BFF 아키텍처](#1-bff-아키텍처)
2. [두 개의 KIS 자격증명 경로](#2-두-개의-kis-자격증명-경로)
3. [KisApiClient (공통 호출)](#3-kisapiclient-공통-호출)
4. [TR_ID 매핑](#4-tr_id-매핑)
5. [DART 연동 (DartApiClient)](#5-dart-연동-dartapiclient)
6. [Jasypt 자격증명 암호화](#6-jasypt-자격증명-암호화)
7. [예외 처리 (KisApiException)](#7-예외-처리-kisapiexception)
8. [관련 문서](#8-관련-문서)

---

## 1. BFF 아키텍처

브라우저는 KIS를 직접 호출하지 않습니다. CORS 및 자격증명 보안을 위해 Spring Boot가 BFF(Backend For Frontend)로 중계합니다.

```
Vue3 → Spring Boot → KIS
```

---

## 2. 두 개의 KIS 자격증명 경로

KIS 연동에는 목적이 다른 두 경로가 있으며, 자격증명 소스/도메인/캐시 방식이 모두 다릅니다.

| 구분 | (A) 사용자별 거래/잔고 | (B) 앱 레벨 시세/재무 |
|------|------------------------|------------------------|
| 관리 서비스 | `KisAuthService` | `KisQuoteService` |
| base URL 설정 | `kis.base-url` | `kis.quote-base-url` |
| 기본 도메인 | mock `https://openapivts.koreainvestment.com:29443` | real `https://openapi.koreainvestment.com:9443` |
| 자격증명 소스 | `user_kis_accounts` (Jasypt 암호화 appKey/appSecret) | env `KIS_QUOTE_APP_KEY` / `KIS_QUOTE_APP_SECRET` |
| 캐시 구조 | per-user `Map<Long kisAccountId, KisTokenCache>` (`ConcurrentHashMap`) | 단일 app-level `AtomicReference<QuoteTokenCache>` |
| 캐시 TTL | `kis.token-cache-ttl` 기본 `86400000ms` (24h) | 24h |
| 사용처 | 거래/잔고 (Asset, Trading) | 시세/재무 (`CompanyInfoService`, `MarketDataService` indices) |

**(A) 사용자별 토큰 캐시 성능:**

| 상황 | 지연 | 동작 |
|------|------|------|
| Cache hit | ~50ms | 메모리 캐시 반환 |
| Cache miss | ~500ms | DB 조회 + 복호화 + OAuth `POST /oauth2/tokenP` |

**(B) 앱 레벨 비활성화 조건:**
quote 키가 비어 있으면 `isQuoteEnabled()=false`가 되어 시세/재무 필드가 `null`로 반환되고 안내(notice)가 포함됩니다.

> **분리 이유:** 시세/재무 API는 mock 도메인에서 제공되지 않습니다. 따라서 (B)는 real 도메인을 사용하며 `CompanyInfoService`와 `MarketDataService` indices에서만 쓰입니다.

---

## 3. KisApiClient (공통 호출)

`KisApiClient`는 KIS 호출의 공통 헤더와 도메인 처리를 담당합니다.

**`convertTrId`:** real/virtual 도메인에 따라 `VTTC` ↔ `TTTC` 접두사를 교체합니다. `FHKST*` / `FHKUP*` 시세 TR_ID는 변경하지 않습니다.

**공통 헤더:**

| 헤더 | 값 |
|------|-----|
| `authorization` | `Bearer {KIS_TOKEN}` |
| `appkey` | appKey |
| `appsecret` | appSecret |
| `tr_id` | TR_ID |
| `custtype` | `P` |

**RestTemplate 타임아웃:** connect 5s, read 18s.

---

## 4. TR_ID 매핑

| TR_ID | 기능 | 엔드포인트 |
|-------|------|------------|
| `VTTC8434R` | inquire-balance (보유/현금) | `/uapi/domestic-stock/v1/trading/inquire-balance` |
| `VTTC0802U` | order-cash BUY | `/uapi/domestic-stock/v1/trading/order-cash` |
| `VTTC0801U` | order-cash SELL | `/uapi/domestic-stock/v1/trading/order-cash` (동일) |
| `VTTC0081R` | inquire-daily-ccld (거래내역 3개월) | `/uapi/domestic-stock/v1/trading/inquire-daily-ccld` |
| `VTTC8908R` | inquire-psbl-order (매수가능 조회) | `/uapi/domestic-stock/v1/trading/inquire-psbl-order` (모의 trading 도메인) |
| `FHKST01010100` | inquire-price (현재가/PER/PBR/EPS/BPS/시가총액) | quote real 도메인 |
| `FHKST01010200` | inquire-asking-price-exp-ccn (실시간 호가 10단계) | quote real 도메인 |
| `FHKST66430200` | income-statement | quote real 도메인 |
| `FHKST66430300` | financial-ratio | quote real 도메인 |
| `FHKST66430600` | stability-ratio | quote real 도메인 |
| `FHKUP03500100` | inquire-index-price (지수) | quote real 도메인 |

> **주의 (버그 수정):** 거래내역 조회는 `VTTC0081R`이 올바른 값입니다. 이전 버전에서 `VTTC8001R`을 사용한 버그가 있었으며, 현재는 `VTTC0081R`로 수정되었습니다.

> **미체결 주문 (`GET /trading/pending-orders`):** 검증되지 않은 신규 미체결 전용 TR(예: `VTTC8036R`)을 도입하지 않습니다. 거래내역과 동일한 `inquire-daily-ccld`(`VTTC0081R`) 결과를 재사용하여, 그중 미체결(잔량>0 또는 `orderStatus`가 `PENDING`/`PARTIAL`)인 행만 필터링해 제공합니다. 실데이터 기반·저위험 방식이며 예외/빈결과 시 빈 리스트를 반환합니다.

> **배당 수령·현금 입출금 내역 (미지원, 공식 확인 2026-06):** KIS 국내주식 OpenAPI에는 개인 **현금 입출금 내역(ledger)** 전용 TR이 없습니다(`ksdinfo/mand-deposit`=예탁원 의무예치일정, `pension/inquire-deposit`=퇴직연금 예수금뿐). 개인 **배당 수령 내역** 전용 TR도 없습니다. 배당 관련으로는 종목 기준 **예탁원정보(배당일정) `HHKDB669102C0`**(`ksdinfo_dividend`, 배당기준일·주당배당금·배당률)와 **배당률 상위 순위**(`국내주식-106`)만 제공됩니다. 따라서 거래내역 화면의 "기타(배당금)" 합계는 데이터 소스가 없어 제거했고, 매매 손익은 `TTTC8715R`(기간별매매손익)/`TTTC8494R`(잔고 실현손익)로만 확인 가능합니다. 향후 '배당 캘린더'가 필요하면 `HHKDB669102C0`로 별도 구현하세요. (근거: 공식 `koreainvestment/open-trading-api` 레포)

---

## 5. DART 연동 (DartApiClient)

| 항목 | 값 |
|------|-----|
| base URL | `https://opendart.fss.or.kr/api` |
| API 키 | env `DART_API_KEY` (비어 있으면 `isEnabled=false`, DART 필드 `null`) |

**주요 메서드:**

| 메서드 | 설명 |
|--------|------|
| `getCorpCode` | 6자리 stock code → 8자리 corp code 변환. `corpCode.xml` ZIP을 StAX로 파싱, `ConcurrentHashMap` 캐시 |
| `getCompanyProfile` | `/company.json` |
| `getDisclosureList` | `/list.json` |

**status 코드:** `"000"`=정상, `"013"`=데이터 없음.

---

## 6. Jasypt 자격증명 암호화

사용자별 KIS 자격증명(`user_kis_accounts.app_key` / `app_secret`)은 Jasypt로 암호화되어 `ENC(...)` 형식으로 저장됩니다.

| 항목 | 값 |
|------|-----|
| 알고리즘 | `PBEWITHHMACSHA512ANDAES_256` |
| iterations | 1000 |
| IV generator | `RandomIvGenerator` |
| 출력 인코딩 | base64 |
| password | env `JASYPT_PASSWORD` |

> 이전의 `PBEWithMD5AndDES` 방식이 아닙니다.

`KisAuthService`는 캐시 miss 시 자격증명을 복호화하며, 복호화 실패 시 plaintext로 폴백합니다(MVP 한정).

---

## 7. 예외 처리 (KisApiException)

`KisApiException`의 팩토리 메서드:

| 메서드 | 용도 |
|--------|------|
| `clientError` | 4xx 클라이언트 오류 |
| `serverError` | 5xx 서버 오류 |
| `networkError` | 네트워크 오류 |
| `oauthFailed` | OAuth 토큰 발급 실패 (`KIS_OAUTH_FAILED=4004` 참조) |

---

## 8. 관련 문서

- [../README.md](../README.md) — 프로젝트 개요 및 실행 방법
- [API_DESIGN.md](API_DESIGN.md) — 전체 REST API 명세
- [AUTHENTICATION_FLOW.md](AUTHENTICATION_FLOW.md) — 앱 JWT 인증 흐름
- [ARCHITECTURE.md](ARCHITECTURE.md) — 시스템 아키텍처
- [STATUS.md](STATUS.md) — 구현 현황
