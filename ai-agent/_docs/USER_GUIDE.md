# AI Agent 사용자 가이드

## 📌 실행 방식 이해

### WAS(Web Application Server) 모드
AI Agent는 **종료되지 않고 계속 실행되는 FastAPI 서버**입니다:

```
FastAPI Server (port 8000) 시작
  ↓
APScheduler BackgroundScheduler 초기화
  ↓
매일 평일 08:50 KST 자동 파이프라인 실행
  ↓
서버는 계속 실행 중 (종료하지 않음)
```

**특징:**
- ✅ 한 번 실행하면 백그라운드에서 계속 동작
- ✅ 스케줄러가 자동으로 매일 08:50에 파이프라인 실행
- ✅ API 엔드포인트로 상태 조회 및 수동 실행 가능
- ✅ Docker 컨테이너로 배포 시 자동 재시작

## 🚀 초기 설정

### 1. 환경 변수 설정

```bash
# .env.example을 복사하여 .env 파일 생성
cd /path/to/ai-agent
cp .env.example .env

# 필수 환경 변수 입력
vi .env  # 또는 nano .env
```

**필수 환경 변수:**

```bash
# KIS API (한국투자증권 모의투자)
KIS_MODE=VIRTUAL                                    # VIRTUAL(모의투자) 또는 REAL(실전투자)
KIS_APP_KEY=PS로시작하는32자리모의투자앱키           # KIS Developers에서 발급
KIS_APP_SECRET=32자리모의투자시크릿키                # KIS Developers에서 발급

# Database (PostgreSQL)
DB_HOST=localhost                                   # Docker 사용 시: postgres
DB_PORT=5432
DB_NAME=financemanage
DB_USER=postgres
DB_PASSWORD=yourpassword                            # 실제 비밀번호로 변경

# Gemini AI (Google AI Studio)
GEMINI_API_KEY=AIza로시작하는구글제미나이API키        # 무료 티어 사용 가능

# Scheduler (기본값 사용 가능)
PIPELINE_CRON=50 8 * * 1-5                          # 평일 08:50 (변경 가능)
PIPELINE_TIMEZONE=Asia/Seoul
PIPELINE_ENABLED=true                               # false로 설정 시 스케줄러 비활성화

# Logging (기본값 사용 가능)
LOG_LEVEL=INFO                                      # DEBUG, INFO, WARNING, ERROR
LOG_FILE=logs/pipeline.log
```

### 2. 의존성 설치

```bash
# Python 가상환경 생성 (선택사항)
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 3. 로그 디렉토리 생성

```bash
mkdir -p logs
```

### 4. 데이터베이스 준비

```bash
# PostgreSQL이 실행 중인지 확인
psql -h localhost -U postgres -d financemanage -c "SELECT 1;"

# 테이블 생성 (database/schema.sql 참조)
```

## 🎮 서버 실행

### 로컬 개발 모드

```bash
# 개발 모드 (자동 재시작 활성화)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 또는
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**실행 로그 예시:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Starting AI Agent application...
INFO:     PipelineScheduler initialized with cron: 50 8 * * 1-5 (Asia/Seoul)
INFO:     Pipeline scheduler started: 50 8 * * 1-5 Asia/Seoul
INFO:     Application started successfully
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 프로덕션 모드

```bash
# 프로덕션 모드 (workers 사용)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# 또는 Gunicorn 사용
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker 모드

```bash
# Docker Compose로 전체 시스템 실행
cd /path/to/FinanceManage_Agent-Project
docker-compose up -d

# AI Agent만 재시작
docker-compose restart ai-agent

# 로그 확인
docker-compose logs -f ai-agent
```

## 📡 API 엔드포인트

### 1. 서버 상태 확인

```bash
# 기본 상태
curl http://localhost:8000/

# 응답 예시:
{
  "service": "AI Agent - Stock Analysis Pipeline",
  "version": "1.0.0",
  "status": "running"
}
```

```bash
# Health check
curl http://localhost:8000/health

# 응답 예시:
{
  "status": "healthy"
}
```

### 2. 스케줄러 상태 확인

```bash
curl http://localhost:8000/api/pipeline/status

# 응답 예시:
{
  "scheduler_running": true,
  "next_run_time": "2025-05-30T08:50:00+09:00",
  "latest_execution_date": "2025-05-29"
}
```

**응답 필드:**
- `scheduler_running`: 스케줄러 동작 여부
- `next_run_time`: 다음 자동 실행 시간 (ISO 8601 형식)
- `latest_execution_date`: 마지막 파이프라인 실행 날짜

### 3. 수동 파이프라인 실행 ⚠️ 실제 실행됨

**중요:** 이 API는 **실제로 파이프라인을 즉시 실행**합니다!

"테스트용"이라고 표시한 이유:
- ✅ 스케줄러: 매일 08:50 자동 실행
- ✅ 이 API: 개발/디버깅/긴급 실행용 (원할 때 즉시 실행)
- ⚠️ **파이프라인 로직은 완전히 동일**하게 실행됨

```bash
# 기본 실행 (오늘 날짜, 현재 보유 종목 자동 조회)
curl -X POST http://localhost:8000/api/pipeline/trigger \
  -H "Content-Type: application/json" \
  -d '{}'

# 특정 날짜로 실행
curl -X POST http://localhost:8000/api/pipeline/trigger \
  -H "Content-Type: application/json" \
  -d '{"trade_date": "2025-05-29"}'

# 보유 종목 지정하여 실행
curl -X POST http://localhost:8000/api/pipeline/trigger \
  -H "Content-Type: application/json" \
  -d '{"holdings": ["005930", "000660"]}'
```

**요청 파라미터:**
- `trade_date` (선택): 거래일자 (YYYY-MM-DD 형식)
- `holdings` (선택): 보유 종목 코드 리스트

**응답 예시 (성공):**
```json
{
  "message": "Pipeline executed successfully",
  "result": {
    "success": true,
    "trade_date": "2025-05-29",
    "total_stocks": 100,
    "selected_stocks": 30,
    "selected_codes": ["005930", "000660", "051910", ...],
    "execution_time_seconds": 45.23
  }
}
```

**응답 예시 (실패):**
```json
{
  "message": "Pipeline execution failed",
  "result": {
    "success": false,
    "error": "KIS API authentication failed",
    "stage": "Stage1_Filtering",
    "execution_time_seconds": 5.12
  }
}
```

### 4. 파이프라인 결과 조회

```bash
# 특정 날짜의 필터링 결과 전체 조회
curl http://localhost:8000/api/pipeline/results/2025-05-29

# 응답 예시:
{
  "trade_date": "2025-05-29",
  "total_stocks": 100,
  "selected_stocks": 30,
  "results": [
    {
      "stock_code": "005930",
      "stock_name": "삼성전자",
      "foreign_net_buy": 123456789,
      "institution_net_buy": 987654321,
      "volume_ratio": 1.52,
      "price_volatility": 0.023,
      "final_score": 0.87,
      "is_selected": true
    },
    ...
  ]
}
```

```bash
# 선택된 종목 코드만 조회
curl http://localhost:8000/api/pipeline/selected/2025-05-29

# 응답 예시:
{
  "trade_date": "2025-05-29",
  "selected_stocks": 30,
  "stock_codes": ["005930", "000660", "051910", ...]
}
```

## 🧪 테스트 및 디버깅

### 1. 스케줄러 비활성화 테스트

```bash
# .env 파일 수정
PIPELINE_ENABLED=false

# 서버 재시작
# → 스케줄러가 시작되지 않음, 수동 실행만 가능
```

### 2. 개발 중 즉시 실행 테스트

```bash
# 로그 레벨을 DEBUG로 변경
LOG_LEVEL=DEBUG

# 서버 실행 후 수동 트리거
curl -X POST http://localhost:8000/api/pipeline/trigger -d '{}'

# 로그 파일 확인
tail -f logs/pipeline.log
```

### 3. 특정 Stage만 테스트

```python
# Python 인터랙티브 셸에서
from pipeline import PipelineOrchestrator
from datetime import date

orchestrator = PipelineOrchestrator()

# Stage 1만 실행
result = await orchestrator.run_stage1_filtering(
    trade_date=date(2025, 5, 29),
    holdings=["005930"]
)
print(result)
```

### 4. API 문서 확인

```bash
# Swagger UI 접속
open http://localhost:8000/docs

# ReDoc 접속
open http://localhost:8000/redoc
```

## 📊 모니터링

### 실시간 로그 확인

```bash
# 로컬 실행
tail -f logs/pipeline.log

# Docker 실행
docker logs -f ai-agent

# Docker Compose 실행
docker-compose logs -f ai-agent
```

### 주요 로그 패턴

```
# 정상 실행
INFO - Scheduled pipeline execution triggered
INFO - Stage 1: Filtering 100 stocks...
INFO - Stage 1: Selected 30 stocks
INFO - Scheduled pipeline completed successfully: 30 stocks selected

# 에러 발생
ERROR - KIS API error: [401] Unauthorized
ERROR - Scheduled pipeline failed: Authentication error

# 스케줄러 상태
INFO - Pipeline scheduler started: 50 8 * * 1-5 Asia/Seoul
INFO - Next run time: 2025-05-30 08:50:00+09:00
```

### 성능 메트릭

```bash
# 실행 시간 확인
grep "execution_time_seconds" logs/pipeline.log

# 에러율 확인
grep "ERROR" logs/pipeline.log | wc -l

# 성공률 확인
grep "completed successfully" logs/pipeline.log | wc -l
```

## 🔧 트러블슈팅

### 1. "uvicorn: command not found"

```bash
# PATH에 Python 스크립트 디렉토리 추가
export PATH="$HOME/Library/Python/3.9/bin:$PATH"

# 또는 python -m 사용
python3 -m uvicorn main:app --reload
```

### 2. "KIS API authentication failed"

```bash
# 환경 변수 확인
echo $KIS_APP_KEY
echo $KIS_APP_SECRET

# .env 파일 확인
cat .env | grep KIS

# 올바른 모드 설정 확인
# 모의투자 키는 "PS"로 시작, 실전투자 키는 다른 접두사 사용
```

### 3. "Database connection failed"

```bash
# PostgreSQL 실행 확인
psql -h localhost -U postgres -d financemanage -c "SELECT 1;"

# Docker 사용 시
docker-compose ps postgres

# 포트 확인
netstat -an | grep 5432
```

### 4. "Scheduler not triggering"

```bash
# Cron 표현식 확인 (평일 08:50)
# "50 8 * * 1-5" = 분 시 일 월 요일(1=월요일, 5=금요일)

# 시간대 확인
echo $PIPELINE_TIMEZONE  # Asia/Seoul이어야 함

# 수동 실행으로 파이프라인 자체는 동작하는지 확인
curl -X POST http://localhost:8000/api/pipeline/trigger
```

### 5. "Korean font not rendering in charts"

```bash
# NanumGothic 폰트 설치 (macOS)
brew install font-nanum

# Linux (Debian/Ubuntu)
sudo apt-get install fonts-nanum

# Docker 컨테이너에서는 Dockerfile에 포함되어 있음
```

## 🔐 보안 고려사항

### 1. API 키 관리

```bash
# .env 파일은 절대 Git에 커밋하지 않음
echo ".env" >> .gitignore

# 프로덕션 환경에서는 Secret Manager 사용
# - AWS Secrets Manager
# - Google Cloud Secret Manager
# - HashiCorp Vault
```

### 2. Database 접근 제어

```bash
# 최소 권한 원칙
# - READ 전용 계정으로 DART DB 조회
# - WRITE 권한은 필요한 테이블만
```

### 3. API 인증 (향후)

```python
# FastAPI 미들웨어로 API 키 인증 추가 (Phase 2)
# 현재는 로컬 개발 환경으로 인증 없음
```

## 📈 성능 최적화 팁

### 1. asyncio 병렬 처리 확인

```python
# 로그에서 병렬 처리 확인
# "Fetching data for 100 stocks in parallel..."
# → Semaphore(5)로 초당 5건 제한
```

### 2. 데이터베이스 쿼리 최적화

```sql
-- 인덱스 생성 확인
CREATE INDEX idx_stock_filter_date ON stock_filter_score(trade_date, stock_code);

-- 실행 계획 확인
EXPLAIN ANALYZE SELECT * FROM stock_filter_score WHERE trade_date = '2025-05-29';
```

### 3. Prophet 학습 시간 단축

```python
# config/constants.py에서 조정
LOOKBACK_DAYS = 60  # 120일 → 60일로 단축 (정확도 trade-off)
```

## 🎯 다음 단계

### Phase 2 개발 예정
- [ ] Stage 2-3 구현 완료 (3-Way 분석)
- [ ] Stage 4 구현 (Gemini AI 의사결정)
- [ ] Stage 5-6 구현 (Safety Filter + 거래 실행)
- [ ] 웹앱 연동 (Vue3 대시보드)
- [ ] 백테스팅 기능
- [ ] 멀티 유저 지원

### 학습 리소스
- [FastAPI 공식 문서](https://fastapi.tiangolo.com)
- [APScheduler 문서](https://apscheduler.readthedocs.io)
- [KIS Developers API 가이드](https://apiportal.koreainvestment.com)
- [Prophet 사용법](https://facebook.github.io/prophet)

---

**문서 버전**: 1.0
**최종 수정일**: 2025-05-30
**작성자**: AI Agent 개발팀
