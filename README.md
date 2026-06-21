# FinanceManage_Agent-Project

<img width="1465" height="883" alt="image" src="https://github.com/user-attachments/assets/457566be-1a0b-4d5b-a5cf-e4b1a4196221" />

AI 기반 주식 자동매매 시스템. 매일 KOSPI 상위 100종목을 분석해 ML 스코어링으로 상위 30종목으로 추리고, 3-way 분석(정량 지표 · 감성 분석 · 시계열 예측)을 거쳐 Gemini AI가 매수/매도를 판단한 뒤 KIS 모의투자 API로 주문을 실행합니다.

## 시스템 구성 (모노레포)

| 디렉터리 | 역할 | 기술 스택 | 포트 |
|---------|------|----------|------|
| `web-app/` | 프론트엔드 SPA (PWA) | Vue 3, Vite, Tailwind CSS | 5173 (dev) |
| `api-server/` | 백엔드 API / 매매 실행 | Spring Boot 4.1, JPA, Spring Security | 7070 |
| `ai-agent/` | ML 파이프라인 / 분석 / AI 판단 | Python, FastAPI, scikit-learn, Prophet, KR-FinBERT | 8000 |
| `database/` | PostgreSQL 스키마 / ERD | PostgreSQL 16 | 5432 |

데이터 흐름과 일일 파이프라인 등 상세 아키텍처는 [`_docs/ARCHITECTURE.md`](_docs/ARCHITECTURE.md)를 참고하세요.

### 문서 길찾기

| 목적 | 문서 |
|------|------|
| 전체 문서 지도 | [`_docs/README.md`](_docs/README.md) |
| 시스템 아키텍처·데이터 흐름 | [`_docs/ARCHITECTURE.md`](_docs/ARCHITECTURE.md) |
| 통합·연동 진행 상황 | [`MVP_INTEGRATION_STATUS.md`](MVP_INTEGRATION_STATUS.md) |
| 화면/기능 단위 진행 현황 | [`_docs/mvp_progress.md`](_docs/mvp_progress.md) |
| 프론트엔드 상세 | [`web-app/_docs/README.md`](web-app/_docs/README.md) |
| 백엔드 상세 | [`api-server/_docs/README.md`](api-server/_docs/README.md) |
| AI 파이프라인 상세 | [`ai-agent/_docs/README.md`](ai-agent/_docs/README.md) |
| DB 스키마 | [`database/README.md`](database/README.md) |
| AI 작업 지침 | [`CLAUDE.md`](CLAUDE.md) |

---

## 사전 요구사항

| 도구 | 버전 |
|------|------|
| Java | 21 (LTS) |
| Node.js | 20+ (LTS) |
| Python | 3.11+ |
| PostgreSQL | 16 |
| Docker / Docker Compose | (선택, DB 구동용 권장) |

> **macOS의 matplotlib 한글 폰트**: ai-agent의 차트 생성에 NanumGothic 폰트가 필요합니다. 미설치 시 차트의 한글이 깨질 수 있습니다 (분석 데이터 자체에는 영향 없음).

---

## 1. 데이터베이스 준비

Docker로 PostgreSQL을 띄우는 것이 가장 간단합니다 (현재 `docker-compose.yml`은 PostgreSQL만 활성화되어 있고, 나머지 서비스는 주석 처리되어 있습니다):

```bash
docker-compose up -d        # PostgreSQL 16 기동 (DB: financemanage / user: admin / pw: admin1234)
```

스키마(17개 테이블 + 2개 뷰)는 다음 중 한 가지 방법으로 적용됩니다:
- **api-server 실행 시 Liquibase가 자동 마이그레이션** (권장 — `api-server/src/main/resources/db/changelog/`)
- 또는 수동 적용 참고용: [`database/schema.sql`](database/schema.sql) (테이블 목록은 [`database/README.md`](database/README.md))

직접 PostgreSQL을 설치해 사용할 경우, `financemanage` 데이터베이스를 만들고 각 모듈의 `.env`에 접속 정보를 맞춰주세요.

---

## 2. 환경 변수 설정

각 모듈에 `.env.example`이 들어 있습니다. 복사 후 실제 키를 채워주세요. **실제 키 파일(`.env`)은 보안상 제출본에 포함되지 않습니다.**

```bash
cp ai-agent/.env.example   ai-agent/.env
cp api-server/.env.example api-server/.env
```

필요한 외부 API 키와 발급처:

| 키 | 용도 | 발급처 |
|----|------|--------|
| `KIS_APP_KEY` / `KIS_APP_SECRET` / `KIS_ACCOUNT_NUMBER` | KIS 모의투자 (주문/잔고) | https://apiportal.koreainvestment.com |
| `KIS_QUOTE_APP_KEY` / `KIS_QUOTE_APP_SECRET` | KIS 시세/재무 조회 (api-server) | 위와 동일 |
| `GEMINI_API_KEY` | AI 매매 판단 (무료 티어) | https://aistudio.google.com/apikey |
| `DART_API_KEY` | 분기 재무 데이터 | https://opendart.fss.or.kr |

> 키 없이도 빌드/기동은 되지만, 실제 시세 조회·매매·AI 판단은 동작하지 않습니다.

---

## 3. 모듈별 실행

세 모듈을 각각 별도 터미널에서 실행합니다.

### api-server (Spring Boot)
Gradle Wrapper가 포함되어 있어 별도 Gradle 설치가 필요 없습니다.

```bash
cd api-server
./gradlew bootRun           # http://localhost:7070
# 빌드만:  ./gradlew build   (산출물: build/libs/*.jar → java -jar 로 실행 가능)
```

### web-app (Vue 3)
```bash
cd web-app
npm install
npm run dev                 # http://localhost:5173
# 프로덕션 빌드: npm run build (정적 산출물: dist/)
```

### ai-agent (FastAPI)
```bash
cd ai-agent
./run_dev.sh                # venv 자동 생성 + 의존성 설치 + http://localhost:8000
```

수동으로 실행할 경우:
```bash
cd ai-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

> ⚠️ **반드시 venv 안에서 실행하세요.** 시스템 python3로 직접 실행하면 Prophet 의존성이 깨져 시계열 예측 결과(`prophet_forecast`)가 NULL로 저장됩니다.

ai-agent의 상세 사용법은 `ai-agent/README.md`, `ai-agent/USAGE.md`를 참고하세요.

---

## 디렉터리 구조

```
FinanceManage_Agent/
├── web-app/        # Vue 3 프론트엔드 (모듈 문서: web-app/_docs/)
├── api-server/     # Spring Boot 백엔드 (Gradle Wrapper 포함, 모듈 문서: api-server/_docs/)
├── ai-agent/       # FastAPI ML 파이프라인 (모듈 문서: ai-agent/_docs/)
├── database/       # PostgreSQL 스키마 (schema.sql + README.md)
├── _docs/          # 최상위 문서 (문서 지도 + 시스템 아키텍처 + 진행 현황)
├── docker-compose.yml
├── CLAUDE.md       # AI(Claude Code) 작업 지침
├── MVP_INTEGRATION_STATUS.md  # 통합·연동 진행 상황
└── README.md       # 이 문서 (사람용 온보딩)
```

## 참고

- 본 시스템은 대학원 최종 프로젝트(MVP)로, 단일 사용자 / KIS 모의투자 / 무료 Gemini 티어를 전제로 합니다.
- 전체 아키텍처와 일일 파이프라인 동작은 `CLAUDE.md`에 정리되어 있습니다.
