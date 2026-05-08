# API 설계서 (MVP 전체)

> **중요**: 이 문서는 Spring Boot API Server의 REST API 명세입니다.
> 한국투자증권(KIS) Open API 연동 방법은 다음 문서를 참고하세요:
> - [KIS API 통합 가이드](KIS_INTEGRATION_GUIDE.md) ⭐ **필독** (인증, 아키텍처, 매핑 통합 문서)

## KIS API 사용 여부 요약

| API 카테고리 | KIS API 사용 | 비고 |
|-------------|-------------|------|
| 인증 API | ❌ | 자체 JWT 인증 |
| 사용자 API | ❌ | RDB 조회 |
| **자산 API** | **✅** | KIS 잔고조회 (`VTTC8434R`) |
| 시장 정보 API | ✅ | FastAPI 경유 (KIS 시세 조회) |
| AI 분석 API | ❌ | RDB 조회 (스케줄러 저장 데이터) |
| 투자 봇 API | ❌ | RDB 조회 |
| **매매 API** | **✅** | KIS 주문 API (`VTTC0802U`, `VTTC0801U`, `VTTC0803U`) |
| 알림 API | ❌ | RDB 조회 |
| 설정 API | ❌ | RDB 조회/수정 |

## 목차
1. [인증 API](#1-인증-api) ✅ 구현 완료
2. [사용자 API](#2-사용자-api) ⭐ 부분 구현 (거래 설정)
3. [자산 API](#3-자산-api) ✅ KIS API 연동 완료
4. [시장 정보 API](#4-시장-정보-api) ⭐ FastAPI 경유
5. [AI 분석 API](#5-ai-분석-api)
6. [투자 봇 API](#6-투자-봇-api)
7. [매매 API](#7-매매-api) ✅ KIS API 연동 완료
8. [알림 API](#8-알림-api)
9. [설정 API](#9-설정-api)
10. [공통 응답 구조](#공통-응답-구조)

---

## 1. 인증 API

### POST /api/auth/login
사용자 로그인 (JWT 토큰 발급)

**Request Body:**
```json
{
  "username": "testuser",
  "password": "password123"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "accessToken": "eyJhbGc...",
    "refreshToken": "eyJhbGc...",
    "tokenType": "Bearer",
    "expiresIn": 3600000,
    "user": {
      "id": 1,
      "username": "testuser",
      "email": "test@example.com",
      "name": "홍길동"
    }
  }
}
```

**Error Responses:**
- 401: Invalid credentials
- 404: User not found

---

### POST /api/auth/register
신규 회원가입 (기본정보 + 금융정보)

**Request Body:**
```json
{
  "username": "newuser",
  "password": "password123",
  "passwordConfirm": "password123",
  "email": "newuser@example.com",
  "name": "홍길동",
  "phone": "01012345678",
  "birthDate": "1990-01-01",
  "kisAccount": {
    "accountNumber": "50112345",
    "appKey": "PSxxxxx",
    "appSecret": "xxxxxx"
  }
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "message": "Registration successful",
  "data": {
    "userId": 1,
    "username": "newuser",
    "email": "newuser@example.com"
  }
}
```

**Error Responses:**
- 400: Validation error (password mismatch, invalid data)
- 409: Username or email already exists

---

### POST /api/auth/reset-password
비밀번호 재설정 (본인 인증 후)

**Request Body:**
```json
{
  "username": "testuser",
  "phone": "01012345678",
  "newPassword": "newpassword123",
  "passwordConfirm": "newpassword123"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Password reset successful",
  "data": null
}
```

**Error Responses:**
- 400: Password mismatch or validation error
- 404: User not found or phone number mismatch

---

### GET /api/auth/check-username?username={username}
아이디 중복 확인

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Username is available",
  "data": {
    "available": true
  }
}
```

---

### GET /api/auth/check-email?email={email}
이메일 중복 확인

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Email is available",
  "data": {
    "available": true
  }
}
```

---

### POST /api/auth/refresh
Access Token 갱신

**Request Body:**
```json
{
  "refreshToken": "eyJhbGc..."
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Token refreshed",
  "data": {
    "accessToken": "eyJhbGc...",
    "tokenType": "Bearer",
    "expiresIn": 3600000
  }
}
```

---

## 2. 사용자 API

### GET /api/users/me
내 정보 조회

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "User information retrieved",
  "data": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "name": "홍길동",
    "phone": "01012345678",
    "birthDate": "1990-01-01",
    "kisAccount": {
      "accountNumber": "50112345",
      "isVerified": true
    },
    "createdAt": "2024-01-01T00:00:00"
  }
}
```

---

### PUT /api/users/me
내 정보 수정

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Request Body:**
```json
{
  "name": "김철수",
  "email": "newemail@example.com",
  "phone": "01098765432"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "User information updated",
  "data": {
    "id": 1,
    "username": "testuser",
    "email": "newemail@example.com",
    "name": "김철수",
    "phone": "01098765432"
  }
}
```

---

### DELETE /api/users/me
회원 탈퇴

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Account deleted successfully",
  "data": null
}
```

---

### GET /api/users/trade-config ⭐ 신규 (MVP 구현 완료)
거래 설정 조회

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Trade configuration retrieved successfully",
  "data": {
    "id": 1,
    "orderAmount": 1000000,
    "maxHoldings": 10,
    "orderType": "market",
    "isActive": false
  }
}
```

**설명:**
- `orderAmount`: 1회 주문 금액 (원)
- `maxHoldings`: 최대 보유 종목수
- `orderType`: 주문 유형 (`market`: 시장가, `limit`: 지정가)
- `isActive`: 자동 거래 활성화 여부

---

### PUT /api/users/trade-config ⭐ 신규 (MVP 구현 완료)
거래 설정 수정

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Request Body:**
```json
{
  "orderAmount": 2000000,
  "maxHoldings": 15,
  "orderType": "limit",
  "isActive": true
}
```

**Validation:**
- `orderAmount`: 필수, 0 이상
- `maxHoldings`: 필수, 1 이상
- `orderType`: 필수, `market` 또는 `limit`
- `isActive`: 필수, boolean

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Trade configuration updated successfully",
  "data": {
    "id": 1,
    "orderAmount": 2000000,
    "maxHoldings": 15,
    "orderType": "limit",
    "isActive": true
  }
}
```

**Error Responses:**
- 400: Validation error
- 404: Trade configuration not found

---

## 3. 자산 API

> **MVP 구현 상태**: GET /assets/holdings ✅, GET /assets/balance ✅ (KIS API 연동)

### GET /api/assets/holdings ✅ MVP 구현 완료
보유 주식 조회 (KIS API 연동)

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Holdings retrieved successfully",
  "data": {
    "output1": [
      {
        "pdno": "005930",
        "prdt_name": "삼성전자",
        "hldg_qty": "10",
        "pchs_avg_pric": "71500",
        "prpr": "72000",
        "evlu_pfls_amt": "5000",
        "evlu_pfls_rt": "0.70",
        "pchs_amt": "715000",
        "evlu_amt": "720000"
      }
    ]
  }
}
```

**KIS API 필드 매핑:**
- `pdno`: 종목코드
- `prdt_name`: 종목명
- `hldg_qty`: 보유수량
- `pchs_avg_pric`: 평균매입가
- `prpr`: 현재가
- `evlu_pfls_amt`: 평가손익금액
- `evlu_pfls_rt`: 평가손익률
- `pchs_amt`: 매입금액
- `evlu_amt`: 평가금액

---

### GET /api/assets/balance ✅ MVP 구현 완료
잔고 조회 (KIS API 연동)

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Balance retrieved successfully",
  "data": {
    "balance": {
      "output2": [
        {
          "ord_psbl_cash": "5000000",
          "wdrw_psbl_tot_amt": "4800000"
        }
      ]
    }
  }
}
```

**KIS API 필드 매핑:**
- `ord_psbl_cash`: 주문 가능 현금
- `wdrw_psbl_tot_amt`: 출금 가능 금액

---

### GET /api/assets/summary
자산 요약 조회 (MVP 미구현)

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Asset summary retrieved",
  "data": {
    "totalAsset": 100000000,
    "totalChange": 2000000,
    "changePercent": 0.02,
    "updatedAt": "2024-11-09 15:30:00",
    "breakdown": {
      "cash": {
        "amount": 30000000,
        "change": 500000,
        "changePercent": 0.0169
      },
      "stocks": {
        "amount": 50000000,
        "change": 1200000,
        "changePercent": 0.0246
      },
      "bonds": {
        "amount": 10000000,
        "change": 200000,
        "changePercent": 0.0204
      },
      "coins": {
        "amount": 10000000,
        "change": 100000,
        "changePercent": 0.0101
      }
    }
  }
}
```

---

### GET /api/assets/breakdown?type={cash|stocks|bonds|coins}
자산 구성 상세 조회

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Query Parameters:**
- `type`: 자산 유형 (cash, stocks, bonds, coins)

**Response (200 OK) - stocks 예시:**
```json
{
  "success": true,
  "message": "Asset breakdown retrieved",
  "data": {
    "type": "stocks",
    "totalAmount": 50000000,
    "holdings": [
      {
        "symbol": "AMZN",
        "name": "아마존",
        "quantity": 100,
        "avgPrice": 180000,
        "currentPrice": 185000,
        "evaluationAmount": 18500000,
        "profit": 500000,
        "profitPercent": 0.0278
      },
      {
        "symbol": "AAPL",
        "name": "애플",
        "quantity": 200,
        "avgPrice": 150000,
        "currentPrice": 155000,
        "evaluationAmount": 31000000,
        "profit": 1000000,
        "profitPercent": 0.0333
      }
    ]
  }
}
```

---

### GET /api/assets/trend?days={7|30|90}
자산 추이 조회

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Query Parameters:**
- `days`: 조회 기간 (기본값: 7)

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Asset trend retrieved",
  "data": {
    "period": 7,
    "data": [
      {
        "date": "2024-11-03",
        "totalAsset": 98000000
      },
      {
        "date": "2024-11-04",
        "totalAsset": 98500000
      },
      {
        "date": "2024-11-09",
        "totalAsset": 100000000
      }
    ]
  }
}
```

---

## 4. 시장 정보 API

### GET /api/market/indices
주요 지수 조회

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Market indices retrieved",
  "data": {
    "domestic": [
      {
        "label": "코스피",
        "value": 2500.25,
        "change": 15.5,
        "changePercent": 0.62
      },
      {
        "label": "코스닥",
        "value": 850.12,
        "change": -3.2,
        "changePercent": -0.37
      }
    ],
    "overseas": [
      {
        "label": "S&P 500",
        "value": 4500.75,
        "change": 12.5,
        "changePercent": 0.28
      },
      {
        "label": "나스닥",
        "value": 14500.25,
        "change": 45.8,
        "changePercent": 0.32
      }
    ],
    "coin": [
      {
        "label": "비트코인",
        "value": 50000000,
        "change": 1000000,
        "changePercent": 2.04
      }
    ]
  }
}
```

---

### GET /api/market/exchange-rates
환율 조회

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Exchange rates retrieved",
  "data": [
    {
      "currency": "USD",
      "country": "미국",
      "rate": 1350.50,
      "change": 5.5,
      "changePercent": 0.41,
      "history": [1345, 1347, 1348, 1350, 1350.5]
    },
    {
      "currency": "JPY",
      "country": "일본",
      "rate": 900.25,
      "change": -2.3,
      "changePercent": -0.25,
      "history": [902, 901, 900.5, 900.25]
    }
  ]
}
```

---

### GET /api/news/top?limit={3}
속보 TOP3 조회

**Query Parameters:**
- `limit`: 조회 개수 (기본값: 3)

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Top news retrieved",
  "data": [
    {
      "id": 1,
      "title": "삼성전자, 실적 발표",
      "description": "3분기 매출 예상치 상회",
      "image": "https://example.com/news1.jpg",
      "source": "연합뉴스",
      "date": "2024-11-09",
      "url": "https://example.com/news/1"
    }
  ]
}
```

---

### GET /api/news/{id}
뉴스 상세 조회

**Path Parameters:**
- `id`: 뉴스 ID

**Response (200 OK):**
```json
{
  "success": true,
  "message": "News detail retrieved",
  "data": {
    "id": 1,
    "title": "삼성전자, 실적 발표",
    "content": "전체 뉴스 내용...",
    "image": "https://example.com/news1.jpg",
    "source": "연합뉴스",
    "date": "2024-11-09",
    "url": "https://example.com/news/1"
  }
}
```

---

### GET /api/news?symbol={symbol}&limit={5}
종목별 뉴스 조회

**Query Parameters:**
- `symbol`: 종목 심볼 (예: AMZN)
- `limit`: 조회 개수 (기본값: 5)

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Stock news retrieved",
  "data": [
    {
      "id": 2,
      "title": "아마존, 클라우드 사업 성장",
      "description": "AWS 매출 증가",
      "source": "Bloomberg",
      "date": "2024-11-09",
      "url": "https://example.com/news/2"
    }
  ]
}
```

---

## 5. AI 분석 API

### GET /api/ai/recommendations
AI 추천 종목 조회

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "AI recommendations retrieved",
  "data": [
    {
      "symbol": "AMZN",
      "title": "아마존",
      "tag": "성장주",
      "description": "AWS 사업 호조로 지속 성장 예상",
      "logo": "https://example.com/logos/amzn.png"
    }
  ]
}
```

---

### GET /api/ai/analysis
AI 시장 분석 조회 (30종목 히트맵, Gemini TOP3)

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "AI market analysis retrieved",
  "data": {
    "heatmapUrl": "/static/charts/heatmap_today.png",
    "quantFeaturesUrl": "/static/charts/quant_features_today.png",
    "sentimentUrl": "/static/charts/sentiment_today.png",
    "forecastUrl": "/static/charts/prophet_forecast_today.png",
    "geminiTop3": [
      {
        "rank": 1,
        "symbol": "AMZN",
        "name": "아마존",
        "action": "buy",
        "reason": "AWS 사업 호조 및 매출 성장세 지속",
        "features": {
          "foreignNetBuy": 1200000000,
          "institutionalNetBuy": 800000000,
          "volumeAvgMultiple": 1.5,
          "priceVolatility": 0.02,
          "per": 25.3,
          "roe": 0.15,
          "operatingMargin": 0.08
        }
      }
    ],
    "updatedAt": "2024-11-09 08:50:00"
  }
}
```

---

## 6. 투자 봇 API

### GET /api/bot/status
봇 상태 조회

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Bot status retrieved",
  "data": {
    "enabled": true,
    "totalInvestment": 10000000,
    "totalValuation": 10500000,
    "profitPercent": 5.0,
    "lastExecutedAt": "2024-11-09 08:50:00"
  }
}
```

---

### PUT /api/bot/config
봇 설정 변경

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Request Body:**
```json
{
  "enabled": true,
  "totalInvestment": 10000000,
  "market": "domestic"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Bot config updated",
  "data": {
    "enabled": true,
    "totalInvestment": 10000000,
    "market": "domestic"
  }
}
```

---

### GET /api/bot/holdings
보유 종목 및 AI 분석 조회

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Bot holdings retrieved",
  "data": [
    {
      "symbol": "AMZN",
      "name": "아마존",
      "quantity": 50,
      "avgPrice": 180000,
      "currentPrice": 185000,
      "purchasePrice": 9000000,
      "profit": 250000,
      "profitPercent": 2.78,
      "logo": "https://example.com/logos/amzn.png",
      "analysis": {
        "points": [
          {
            "title": "지속적인 매출 성장",
            "content": "AWS, 전자상거래 등 다양한 사업 부문에서 성장세"
          },
          {
            "title": "혁신과 확장성",
            "content": "AI, 물류 자동화 등 미래 산업 혁신"
          }
        ]
      }
    }
  ]
}
```

---

## 7. 매매 API

> **MVP 구현 상태**: POST /trading/buy ✅, POST /trading/sell ✅, GET /trading/history ✅ (KIS API 연동)

### POST /api/trading/buy ✅ MVP 구현 완료
매수 주문 (KIS API 연동)

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Request Body:**
```json
{
  "stockCode": "005930",
  "stockName": "삼성전자",
  "quantity": 10,
  "price": 71500
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Buy order executed successfully",
  "data": {
    "orderNumber": "2024010100001",
    "stockCode": "005930",
    "stockName": "삼성전자",
    "quantity": 10,
    "price": 71500
  }
}
```

---

### POST /api/trading/sell ✅ MVP 구현 완료
매도 주문 (KIS API 연동)

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Request Body:**
```json
{
  "stockCode": "005930",
  "stockName": "삼성전자",
  "quantity": 5,
  "price": 72000
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Sell order executed successfully",
  "data": {
    "orderNumber": "2024010100002",
    "stockCode": "005930",
    "stockName": "삼성전자",
    "quantity": 5,
    "price": 72000
  }
}
```

---

### GET /api/trading/history ✅ MVP 구현 완료
거래 내역 조회

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Trade history retrieved successfully",
  "data": [
    {
      "id": 1,
      "userId": 1,
      "orderNumber": "2024010100001",
      "stockCode": "005930",
      "stockName": "삼성전자",
      "orderType": "BUY",
      "orderStatus": "COMPLETED",
      "quantity": 10,
      "orderPrice": 71500,
      "executedPrice": 71500,
      "orderedAt": "2024-11-01T09:00:00",
      "executedAt": "2024-11-01T09:00:05",
      "createdAt": "2024-11-01T09:00:00"
    }
  ]
}
```

---

### GET /api/trading/orders/pending
미체결 주문 조회 (MVP 미구현)

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Pending orders retrieved",
  "data": [
    {
      "orderId": 1,
      "symbol": "AMZN",
      "name": "아마존",
      "type": "buy",
      "quantity": 10,
      "price": 185000,
      "currency": "원",
      "orderedAt": "2024-11-09 10:00:00",
      "status": "pending"
    }
  ]
}
```

---

### GET /api/trading/orders/reserved
예약 주문 조회

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Reserved orders retrieved",
  "data": [
    {
      "orderId": 2,
      "symbol": "AAPL",
      "name": "애플",
      "type": "sell",
      "quantity": 5,
      "price": 155000,
      "currency": "원",
      "reservedAt": "2024-11-09 22:30:00",
      "status": "reserved"
    }
  ]
}
```

---

### POST /api/trading/orders
주문 등록 (매수/매도)

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Request Body:**
```json
{
  "symbol": "AMZN",
  "type": "buy",
  "orderType": "market",
  "quantity": 10,
  "price": 185000,
  "time": "22:30 ~ 05:00"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "message": "Order placed successfully",
  "data": {
    "orderId": 3,
    "symbol": "AMZN",
    "type": "buy",
    "quantity": 10,
    "price": 185000,
    "status": "pending"
  }
}
```

---

### DELETE /api/trading/orders/{orderId}
주문 취소

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Path Parameters:**
- `orderId`: 주문 ID

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Order cancelled successfully",
  "data": null
}
```

---

### GET /api/trading/history?startDate={date}&endDate={date}&page={0}&size={20}
거래 내역 조회

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Query Parameters:**
- `startDate`: 시작일 (YYYY-MM-DD, 기본값: 1개월 전)
- `endDate`: 종료일 (YYYY-MM-DD, 기본값: 오늘)
- `page`: 페이지 번호 (기본값: 0)
- `size`: 페이지 크기 (기본값: 20)

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Trading history retrieved",
  "data": {
    "content": [
      {
        "id": 1,
        "symbol": "AMZN",
        "name": "아마존",
        "type": "buy",
        "quantity": 10,
        "price": 180000,
        "totalAmount": 1800000,
        "executedAt": "2024-10-15 10:30:00"
      },
      {
        "id": 2,
        "symbol": "AAPL",
        "name": "애플",
        "type": "sell",
        "quantity": 5,
        "price": 150000,
        "totalAmount": 750000,
        "executedAt": "2024-10-20 15:45:00"
      }
    ],
    "totalPages": 5,
    "totalElements": 100,
    "currentPage": 0,
    "size": 20
  }
}
```

---

### GET /api/trading/summary?startDate={date}&endDate={date}
거래 요약 조회

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Query Parameters:**
- `startDate`: 시작일 (YYYY-MM-DD)
- `endDate`: 종료일 (YYYY-MM-DD)

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Trading summary retrieved",
  "data": {
    "totalBuyAmount": 10000000,
    "totalSellAmount": 8000000,
    "totalProfit": 500000,
    "profitPercent": 6.25,
    "buyCount": 15,
    "sellCount": 10
  }
}
```

---

## 8. 알림 API

### GET /api/notifications?page={0}&size={20}
알림 목록 조회

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Query Parameters:**
- `page`: 페이지 번호 (기본값: 0)
- `size`: 페이지 크기 (기본값: 20)

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Notifications retrieved",
  "data": {
    "content": [
      {
        "id": 1,
        "type": "trade",
        "title": "테슬라 3주 예약 매도 체결",
        "description": "체결가 $248.50",
        "time": "5분 전",
        "read": false,
        "createdAt": "2024-11-09 15:25:00"
      },
      {
        "id": 2,
        "type": "ai",
        "title": "AI 매매 신호",
        "description": "NVIDIA 매수 추천",
        "time": "30분 전",
        "read": true,
        "createdAt": "2024-11-09 15:00:00"
      }
    ],
    "totalPages": 3,
    "totalElements": 50,
    "unreadCount": 5
  }
}
```

---

### PUT /api/notifications/{id}/read
알림 읽음 처리

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Path Parameters:**
- `id`: 알림 ID

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Notification marked as read",
  "data": null
}
```

---

## 9. 설정 API

### GET /api/settings
설정 조회

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Settings retrieved",
  "data": {
    "notifications": {
      "trade": true,
      "ai": true,
      "price": true,
      "news": false
    },
    "display": {
      "theme": "dark",
      "language": "ko",
      "assetOrder": ["stocks_overseas", "stocks_domestic", "coins", "bonds"]
    }
  }
}
```

---

### PUT /api/settings
설정 변경

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Request Body:**
```json
{
  "notifications": {
    "trade": true,
    "ai": false,
    "price": true,
    "news": true
  },
  "display": {
    "theme": "light",
    "language": "en",
    "assetOrder": ["stocks_domestic", "stocks_overseas", "coins", "bonds"]
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Settings updated",
  "data": {
    "notifications": {
      "trade": true,
      "ai": false,
      "price": true,
      "news": true
    },
    "display": {
      "theme": "light",
      "language": "en",
      "assetOrder": ["stocks_domestic", "stocks_overseas", "coins", "bonds"]
    }
  }
}
```

---

## 공통 응답 구조

### 성공 응답
```json
{
  "success": true,
  "message": "Operation successful message",
  "data": { /* Response data */ }
}
```

### 에러 응답
```json
{
  "success": false,
  "message": "Error message",
  "data": null
}
```

### HTTP 상태 코드
- `200 OK`: 요청 성공
- `201 Created`: 리소스 생성 성공
- `400 Bad Request`: 잘못된 요청 (validation 실패)
- `401 Unauthorized`: 인증 실패
- `403 Forbidden`: 권한 없음
- `404 Not Found`: 리소스 없음
- `409 Conflict`: 중복 리소스
- `500 Internal Server Error`: 서버 오류

---

## 데이터베이스 테이블 매핑

### 회원가입 시 생성되는 데이터:
1. **users** 테이블: username, email, password (BCrypt), name, phone, birth_date
2. **user_kis_accounts** 테이블: user_id, account_number, app_key, app_secret
3. **user_trade_config** 테이블: user_id, order_amount (default), max_holdings (default), is_active (false)

### 로그인 시 생성되는 데이터:
1. **refresh_tokens** 테이블: user_id, token, expires_at

---

## Validation 규칙

### 회원가입:
- username: 4-20자, 영문+숫자
- password: 8자 이상, 영문+숫자+특수문자
- email: 이메일 형식
- phone: 010으로 시작하는 11자리 숫자
- birthDate: YYYY-MM-DD 형식

### 비밀번호 재설정:
- newPassword: 기존 비밀번호와 동일 규칙
- passwordConfirm: newPassword와 일치

---

## 보안 고려사항

1. 비밀번호는 BCrypt로 암호화 저장
2. JWT Access Token: 1시간 유효
3. JWT Refresh Token: 24시간 유효
4. KIS API Key/Secret은 암호화 저장 권장
5. 비밀번호 재설정 시 본인 인증 필수 (현재 phone 번호 일치 확인)

---

## MVP 범위 제외 사항

- SMS 인증번호 발송 (실제 SMS 발송 기능은 제외, 프론트엔드 UI만 구현)
- 이메일 인증
- 소셜 로그인
- 2FA
- 실시간 WebSocket 알림 (polling 방식으로 대체)
- 채권/코인 실제 거래 (데이터 표시만)
