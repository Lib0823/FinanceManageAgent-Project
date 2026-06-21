#!/bin/bash
# FastAPI Development Server Runner (로컬 실행)
# 환경변수는 저장소 최상위의 단일 .env 파일에서 읽는다 (Docker/로컬 공통 소스).

cd "$(dirname "$0")"

# 루트 .env 로드 (없으면 모듈 .env로 폴백)
ROOT_ENV="../.env"
if [ -f "$ROOT_ENV" ]; then
    set -a; . "$ROOT_ENV"; set +a
    echo "[run_dev] loaded $ROOT_ENV"
elif [ -f .env ]; then
    set -a; . ./.env; set +a
    echo "[run_dev] loaded ai-agent/.env (fallback)"
else
    echo "[run_dev] WARNING: .env not found — KIS 키 없으면 기동되지 않습니다"
fi

# 로컬 DB 접속값 파생: compose는 environment:로 DB_*를 주입하지만,
# 로컬에서는 루트 .env의 POSTGRES_* 값으로부터 ai-agent가 읽는 DB_* 를 만든다.
export DB_HOST="${DB_HOST:-localhost}"
export DB_PORT="${DB_PORT:-5432}"
export DB_NAME="${DB_NAME:-${POSTGRES_DB:-financemanage}}"
export DB_USER="${DB_USER:-${POSTGRES_USER:-admin}}"
export DB_PASSWORD="${DB_PASSWORD:-${POSTGRES_PASSWORD:-admin1234}}"

# 가상환경 (Prophet 때문에 필수)
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Virtual environment not found. Creating..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

echo "Starting FastAPI server at http://localhost:8000"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
