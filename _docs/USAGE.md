# 설치 및 실행 (Usage)

프로젝트 전체를 로컬에서 구동하는 방법입니다. 모듈별 상세 사용법은 각 모듈 `_docs/USAGE.md`를 참고하세요.

- [`ai-agent/_docs/USAGE.md`](../ai-agent/_docs/USAGE.md)
- [`api-server/_docs/USAGE.md`](../api-server/_docs/USAGE.md)
- [`web-app/_docs/USAGE.md`](../web-app/_docs/USAGE.md)

---

## 사전 요구사항

| 도구 | 버전 |
|------|------|
| Java | 21 (LTS) |
| Node.js | 20+ (LTS, `^20.19 || >=22.12`) |
| Python | 3.11+ |
| PostgreSQL | 16 |
| Docker / Docker Compose | (선택, DB 구동용 권장) |

> **matplotlib 한글 폰트**: ai-agent의 차트 생성에는 NanumGothic 폰트가 필요합니다. 미설치 시 차트의 한글이 깨질 수 있습니다(분석 데이터 자체에는 영향 없음).

---

## 1. 데이터베이스 준비

Docker로 PostgreSQL을 띄우는 것이 가장 간단합니다. 현재 `docker-compose.yml`은 **PostgreSQL만 활성화**되어 있고 나머지 서비스는 주석 처리되어 있습니다.

```bash
docker-compose up -d        # PostgreSQL 16 기동 (DB: financemanage / user: admin / pw: admin1234)
```

스키마(17개 테이블 + 2개 뷰)는 다음 중 한 방법으로 적용됩니다.

- **api-server 실행 시 Liquibase가 자동 마이그레이션** (권장 — `api-server/src/main/resources/db/changelog/`)
- 수동 적용 참고용: [`../database/schema.sql`](../database/schema.sql) (테이블 목록은 [`../database/README.md`](../database/README.md))

직접 PostgreSQL을 설치해 쓸 경우 `financemanage` 데이터베이스를 만들고 각 모듈 설정에 접속 정보를 맞춰주세요.

---

## 2. 환경 변수 설정

각 모듈에 `.env.example`이 있습니다. 복사 후 실제 키를 채워주세요. **실제 키 파일(`.env`)은 커밋하지 않습니다.**

```bash
cp ai-agent/.env.example   ai-agent/.env
cp api-server/.env.example api-server/.env
```

필요한 키와 발급처:

| 키 | 용도 | 발급처 |
|----|------|--------|
| `KIS_APP_KEY` / `KIS_APP_SECRET` / `KIS_ACCOUNT_NUMBER` | KIS 모의투자 (주문/잔고) | https://apiportal.koreainvestment.com |
| `KIS_QUOTE_APP_KEY` / `KIS_QUOTE_APP_SECRET` | KIS 시세/재무 조회 (api-server) | 위와 동일 |
| `GEMINI_API_KEY` | AI 매매 판단 (무료 티어) | https://aistudio.google.com/apikey |
| `DART_API_KEY` | 분기 재무 데이터 | https://opendart.fss.or.kr |
| `JWT_SECRET` | JWT 서명 키 (256bit 이상) | 임의 생성 |
| `JASYPT_PASSWORD` | KIS 자격증명 암호화 키 | 임의 생성 |

> 키 없이도 빌드/기동은 되지만, 실제 시세 조회·매매·AI 판단은 동작하지 않습니다(graceful degrade).

---

## 3. 모듈별 실행

세 모듈을 각각 별도 터미널에서 실행합니다.

### api-server (Spring Boot)
Gradle Wrapper가 포함되어 있어 별도 Gradle 설치가 필요 없습니다.

```bash
cd api-server
export JWT_SECRET="<256bit 이상 키>"
export JASYPT_PASSWORD="<암호화 키>"
./gradlew bootRun           # http://localhost:7070/api  (Liquibase 자동 마이그레이션)
# 빌드만: ./gradlew build   (산출물: build/libs/*.jar → java -jar 로 실행 가능)
```
헬스 체크: `GET http://localhost:7070/api/health`

### web-app (Vue 3)
```bash
cd web-app
npm install
npm run dev                 # http://localhost:5173
# 프로덕션 빌드: npm run build (정적 산출물: dist/)
```
API 베이스 URL은 `VITE_API_BASE_URL`(기본값 `http://localhost:7070/api`)로 지정합니다. 개발 모드에서는 라우터 인증 가드가 우회됩니다.

### ai-agent (FastAPI)
```bash
cd ai-agent
./run_dev.sh                # venv 자동 생성 + 의존성 설치 + http://localhost:8000
```

수동 실행:
```bash
cd ai-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

> ⚠️ **반드시 venv 안에서 실행하세요.** 시스템 python3로 직접 실행하면 Prophet 의존성이 깨져 시계열 예측 결과(`prophet_forecast`)가 NULL로 저장됩니다.

분석 파이프라인은 평일 08:50 KST에 자동 실행되며, 수동 트리거는 `POST http://localhost:8000/api/pipeline/trigger`입니다.

---

## 4. 개발용 테스트 계정

`testuser` / `password123` (Liquibase `v1.4-test-data.yaml`로 시드)

---

## 5. 트러블슈팅

| 증상 | 원인 / 해결 |
|------|-------------|
| `prophet_forecast`가 NULL | 시스템 python3로 실행. venv 활성화 후 재실행 |
| api-server 부팅 실패 (`JWT_SECRET`/`JASYPT_PASSWORD`) | 두 환경 변수 설정 후 재실행 |
| web-app에서 API 401 반복 | 토큰 만료 → 자동 리프레시 실패. 재로그인 또는 `VITE_API_BASE_URL` 확인 |
| 차트 한글 깨짐 | NanumGothic 폰트 미설치 (분석 데이터에는 영향 없음) |
| KIS 시세/매매 미동작 | `.env`의 KIS 키 누락 또는 모의투자 계좌 연동 필요 |

모듈별 상세 트러블슈팅은 각 모듈 `_docs/USAGE.md`를 참고하세요.
