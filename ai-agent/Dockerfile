# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 시스템 의존성: prophet/cmdstanpy 컴파일용 빌드 도구 + matplotlib 한글 폰트(NanumGothic)
# fontconfig: fc-cache 제공 (slim 베이스엔 기본 미포함)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential gcc g++ curl \
        fontconfig fonts-nanum \
    && fc-cache -f \
    && rm -rf /var/lib/apt/lists/*

# 의존성 먼저 설치 (레이어 캐시)
COPY requirements.txt .
# torch는 CPU 전용 휠로 먼저 설치 (기본 pip은 CUDA용 torch ~2GB+를 받음 → GPU 없으니 불필요).
# 이렇게 하면 아래 requirements 설치 시 torch==2.1.2 가 이미 충족되어 재다운로드하지 않음.
RUN pip install torch==2.1.2 --index-url https://download.pytorch.org/whl/cpu
RUN pip install -r requirements.txt

# 앱 소스 복사
COPY . .

# 로그 디렉터리 생성 (logs/ 는 .dockerignore 제외 → main.py의 FileHandler가 import 시 사용)
RUN mkdir -p /app/logs

EXPOSE 8000
# KR-FinBERT 모델은 최초 실행 시 HuggingFace에서 다운로드되어 /root/.cache/huggingface 에 캐시됨
# (docker-compose의 hf-cache 볼륨으로 재시작 간 유지)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
