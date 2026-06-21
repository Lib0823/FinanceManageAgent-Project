# 프로젝트 문서 지도 (Documentation Map)

`FinanceManage_Agent` 모노레포의 **최상위 문서 진입점**입니다. AI 에이전트와 사람 모두 이 문서에서 시작해 전체 시스템 구조 → 모듈별 진행 상황 → 각 모듈 상세 문서로 길을 찾을 수 있도록 구성했습니다.

> 이 시스템은 매일 KOSPI 상위 100종목을 ML 스코어링으로 30종목으로 추리고, 3-way 분석(정량·감성·시계열)을 거쳐 Gemini AI가 매수/매도를 판단한 뒤 KIS 모의투자 API로 주문을 실행하는 AI 주식 자동매매 시스템입니다.

---

## 1. 어디서부터 읽어야 하나 (Reading Path)

| 당신이 ... 라면 | 시작 문서 | 다음 |
|----------------|----------|------|
| **처음 온 사람 / 실행해보려는 사람** | [`../README.md`](../README.md) (실행 방법) | 모듈별 `_docs/USER_GUIDE.md` |
| **AI 에이전트 / Claude Code** | [`../CLAUDE.md`](../CLAUDE.md) (프로젝트 지침) | 작업 대상 모듈 `_docs/README.md` |
| **전체 시스템 구조를 파악하려는 사람** | [`ARCHITECTURE.md`](ARCHITECTURE.md) (시스템 데이터 흐름·통신) | 모듈별 `_docs/SYSTEM_ARCHITECTURE.md` |
| **통합/연동 진행 상황을 보려는 사람** | [`../MVP_INTEGRATION_STATUS.md`](../MVP_INTEGRATION_STATUS.md) | 모듈별 STATUS / `_docs/mvp_progress.md` |
| **DB 스키마를 보려는 사람** | [`../database/README.md`](../database/README.md) | [`../database/schema.sql`](../database/schema.sql) |

---

## 2. 모듈별 문서 진입점

각 모듈은 동일한 규약(README 인덱스 → ARCHITECTURE → STATUS → 기능 설계서)으로 `_docs/`에 문서를 두고 있습니다. 모듈 내부를 작업할 때는 먼저 해당 `_docs/README.md`를 읽으세요.

| 모듈 | 역할 | 문서 진입점 | 비고 |
|------|------|------------|------|
| `web-app/` | Vue 3 프론트엔드 (PWA) | [`web-app/_docs/README.md`](../web-app/_docs/README.md) | 화면·라우팅·API 연동 |
| `api-server/` | Spring Boot 백엔드 / 매매 실행 | [`api-server/_docs/README.md`](../api-server/_docs/README.md) | 인증·KIS 연동·REST API |
| `ai-agent/` | FastAPI ML 파이프라인 / AI 판단 | [`ai-agent/_docs/README.md`](../ai-agent/_docs/README.md) | 일일 분석 파이프라인 |
| `database/` | PostgreSQL 스키마 / ERD | [`database/README.md`](../database/README.md) | 17개 테이블 + 2개 뷰 |

### 모듈 `_docs/` 안의 주요 문서 (참고)

- **api-server**: `README.md`, `SYSTEM_ARCHITECTURE.md`, `API_DESIGN.md`, `AUTHENTICATION_FLOW.md`, `KIS_API_GUIDE.md`
- **ai-agent**: `README.md`, `SYSTEM_ARCHITECTURE.md`, `API_REFERENCE.md`, `USER_GUIDE.md`
- **web-app**: `_docs/README.md` (정리 진행 중)

> 위 모듈 `_docs/`는 각 모듈 전담 에이전트가 관리합니다. 이 디렉터리(`_docs/`)의 문서는 그 위를 묶는 최상위 문서입니다.

---

## 3. 최상위 문서 (이 디렉터리)

| 파일 | 내용 |
|------|------|
| `README.md` | 이 문서 — 전체 문서 지도 / 길찾기 |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | 시스템 전체 데이터 흐름, 서비스 통신, 일일 파이프라인 다이어그램 |
| `architecture.png` | 시스템 아키텍처 이미지 |
| `analysis_flow.png` | 분석 파이프라인 흐름 이미지 |
| `data_struct.png` | 데이터 구조 이미지 |
| `story_board.png` | 화면 스토리보드 이미지 |
| `mvp_progress.md` | 화면/기능 단위 상세 진행 현황 (최신, 2026-05-22) |
| `dev_note.txt` | 개발 메모 (고도화 백로그) |

---

## 4. 루트 레벨 문서

| 파일 | 독자 | 역할 |
|------|------|------|
| [`../README.md`](../README.md) | 사람 | 프로젝트 소개 + 실행 방법 (온보딩) |
| [`../CLAUDE.md`](../CLAUDE.md) | AI (Claude Code) | 프로젝트 지침 + 아키텍처 요약 + 문서 길찾기 |
| [`../MVP_INTEGRATION_STATUS.md`](../MVP_INTEGRATION_STATUS.md) | 사람/AI | 통합·연동 관점의 전체 진행 상황 허브 |

> **README vs CLAUDE.md**: `README.md`는 사람 온보딩(무엇을, 어떻게 실행하나)에, `CLAUDE.md`는 AI 작업 지침(어디에 무엇이 있고 어떤 규약을 따르나)에 집중합니다.
