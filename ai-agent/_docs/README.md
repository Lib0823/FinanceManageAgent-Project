# AI Agent 문서 가이드

## 📚 문서 구조 (4개 핵심 문서)

AI Agent 프로젝트의 모든 문서가 다음 4개로 통합되었습니다:

| 문서 | 용도 | 독자 |
|------|------|------|
| **README.md** | 📖 문서 네비게이션 가이드 | 모든 개발자 |
| **API_REFERENCE.md** | 🔧 API 서버 개발 완전 참조 | Backend 개발자 |
| **SYSTEM_ARCHITECTURE.md** | 🏗️ 시스템 구조 및 6단계 플로우 | 시스템 아키텍트, AI 개발자 |
| **USER_GUIDE.md** | 📱 사용자 가이드 | 최종 사용자, 운영자 |

---

## 🎯 목적별 문서 찾기

### 1️⃣ API 서버 개발을 시작하는 경우
**필독 순서**:
1. `API_REFERENCE.md` (1순위) - DB 스키마, 엔드포인트, 쿼리 예시
2. `SYSTEM_ARCHITECTURE.md` (2순위) - 데이터 플로우 이해

**빠른 시작**:
```
API_REFERENCE.md → Section 1 (빠른 시작)
→ Spring Boot Controller 예시 복사
→ Section 2 (DB 스키마) 참고하여 Entity 생성
→ Section 3 (쿼리 예시) 참고하여 Repository 구현
```

### 2️⃣ AI Agent 파이프라인을 이해하는 경우
**필독 순서**:
1. `SYSTEM_ARCHITECTURE.md` (1순위) - 6단계 상세 플로우
2. `API_REFERENCE.md` (2순위) - 각 Stage가 어느 테이블에 저장되는지
3. `CHANGELOG.md` (3순위) - 최근 구현 상태

**주요 섹션**:
- Stage 0: 휴장일 체크 (2026-06-01 추가)
- Stage 1: 종목 필터링 (KOSPI 100 → TOP 30)
- Stage 2: 3-Way 분석 (정량/감성/시계열)
- Stage 4: Gemini AI 결정
- Stage 5~6: Safety Filter 및 거래 실행

### 3️⃣ 웹 화면 데이터 요구사항을 확인하는 경우
**필독 순서**:
1. `API_REFERENCE.md` → Section 4 (웹 화면 데이터 요구사항)
2. `API_REFERENCE.md` → Section 3 (API 엔드포인트)

**화면별 참조 섹션**:
- 시장 전체 종합 분석: `API_REFERENCE.md` 4.1
- 종목별 감성 분석: `API_REFERENCE.md` 4.2
- 종목별 분석 요약: `API_REFERENCE.md` 4.3
- 종목별 시계열 예측: `API_REFERENCE.md` 4.4

### 4️⃣ 전체 시스템 아키텍처를 파악하는 경우
**필독 순서**:
1. `SYSTEM_ARCHITECTURE.md` (1순위) - 시스템 개요, 컴포넌트 구조
2. `API_REFERENCE.md` → Section 5 (데이터 흐름)
3. `USER_GUIDE.md` (선택) - 실제 사용 흐름

**아키텍처 다이어그램**:
```
Vue3 ←→ Spring Boot ←→ PostgreSQL
  ↓         ↑             ↑
FastAPI ────┴─────────────┘
  ↓
KIS API / DART / News
```

### 5️⃣ 시스템을 처음 사용하는 경우
**필독 순서**:
1. `USER_GUIDE.md` (1순위) - 설치, 설정, 실행 방법
2. `SYSTEM_ARCHITECTURE.md` → 시스템 개요 섹션
3. `CHANGELOG.md` (선택) - 최신 기능 확인

---

## 🚀 빠른 참조 (Quick Reference)

| 찾고자 하는 내용 | 참조 문서 |
|---------------|----------|
| DB 테이블 스키마 | `API_REFERENCE.md` Section 2 |
| API 엔드포인트 | `API_REFERENCE.md` Section 3 |
| Stage별 알고리즘 | `SYSTEM_ARCHITECTURE.md` Section 3 |
| 웹 화면 데이터 | `API_REFERENCE.md` Section 4 |
| 에러 처리 로직 | `SYSTEM_ARCHITECTURE.md` Section 6 |
| 실행 방법 | `USER_GUIDE.md` |
| 최근 변경사항 | `CHANGELOG.md` |

---

## 🗂️ 폐기된 문서 (통합 완료)

다음 문서들은 위 5개 핵심 문서로 통합되어 삭제되었습니다:

| 폐기 파일 | 통합된 위치 |
|----------|------------|
| ~~API_QUERIES.md~~ | `API_REFERENCE.md` Section 3 |
| ~~API_SERVER_DEV_GUIDE.md~~ | `API_REFERENCE.md` Section 1 |
| ~~DATABASE_SCHEMA.md~~ | `API_REFERENCE.md` Section 2 |
| ~~DATA_FLOW_AND_API.md~~ | `SYSTEM_ARCHITECTURE.md` Section 4 |
| ~~IMPLEMENTATION_SPEC.md~~ | `SYSTEM_ARCHITECTURE.md` Section 3 |
| ~~SYSTEM_OVERVIEW.md~~ | `SYSTEM_ARCHITECTURE.md` Section 1~2 |
| ~~WEB_DISPLAY_REQUIREMENTS.md~~ | `API_REFERENCE.md` Section 4 |

---

**문서 버전**: 2.0 (2026-06-01 대규모 통합)
**작성자**: AI Agent 개발팀
