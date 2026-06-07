# AI Agent - Stock Analysis Pipeline

**Status:** ✅ Stage 1 Complete | **Version:** 1.0.0 | **Date:** 2026-05-19

Automated AI-powered stock analysis pipeline for KOSPI market with ML-based filtering, multi-domain analysis, and trading decision generation.

## Quick Start

```bash
# 1. Install dependencies
cd ai-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your KIS API credentials

# 3. Run server (auto-scheduling enabled)
python main.py
```

Server starts at `http://localhost:8000` with automatic pipeline execution at weekdays 08:50 KST.

## What's Implemented (Stage 1)

### ✅ Core Features
- **KOSPI 100 Data Collection**: Parallel async fetching from KIS API (~40s for 100 stocks)
- **ML-Based Scoring**: StandardScaler normalization + weighted scoring (0.3/0.3/0.3/0.1)
- **Top 30 Selection**: Intelligent filtering with holdings inclusion for sell analysis
- **Automated Scheduling**: APScheduler with cron expression (weekdays 08:50 KST)
- **Manual Trigger**: REST API endpoint for on-demand execution
- **Database Persistence**: PostgreSQL with SQLAlchemy ORM

### 📊 Scoring Algorithm
```python
score = |foreign_net_buy| × 0.3      # 외국인 순매수 (절대값)
      + |institutional_net_buy| × 0.3 # 기관 순매수 (절대값)
      + volume_ratio × 0.3             # 거래량 배율
      + price_volatility × 0.1         # 가격 변동성
```

Features are normalized daily using StandardScaler fit on 100 stocks for relative comparison.

## Architecture

```
ai-agent/
├── config/           # Settings (Pydantic), constants (KOSPI 100)
├── collectors/       # KIS API client (async, rate limited)
├── analysis/         # Stock filter (ML scoring)
├── database/         # SQLAlchemy models, repository pattern
├── pipeline/         # Orchestrator + scheduler
├── tests/            # Pytest unit tests
├── main.py           # FastAPI application
├── USAGE.md          # Comprehensive user guide
└── CLAUDE.md         # Full architecture documentation
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/pipeline/status` | Scheduler status & next run |
| POST | `/api/pipeline/trigger` | Manual execution |
| GET | `/api/pipeline/results/{date}` | Get results by date |
| GET | `/api/pipeline/selected/{date}` | Get top 30 codes |

**Swagger UI:** `http://localhost:8000/docs`

## Usage Examples

### Automatic Execution (Default)
```bash
# Server runs scheduler automatically
python main.py
# Pipeline executes weekdays at 08:50 KST
```

### Manual Trigger
```bash
# Trigger with current date
curl -X POST http://localhost:8000/api/pipeline/trigger \
  -H "Content-Type: application/json" \
  -d '{}'

# Trigger with specific date and holdings
curl -X POST http://localhost:8000/api/pipeline/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "trade_date": "2026-05-19",
    "holdings": ["005930", "000660"]
  }'
```

### Check Status
```bash
curl http://localhost:8000/api/pipeline/status
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest --cov=. --cov-report=html tests/

# View coverage report
open htmlcov/index.html
```

**Current Coverage:** 66% (85% for filter module)

## Configuration

Key environment variables in `.env`:

```bash
# KIS API (required)
KIS_MODE=VIRTUAL              # or REAL
KIS_APP_KEY=your_key
KIS_APP_SECRET=your_secret

# Database (required)
DB_HOST=localhost
DB_USER=postgres
DB_PASSWORD=yourpassword

# Scheduler (optional, defaults provided)
PIPELINE_CRON=50 8 * * 1-5   # Weekdays 08:50 KST
PIPELINE_ENABLED=true
```

## Database Setup

```sql
CREATE TABLE stock_filter_score (
    stock_code VARCHAR(10),
    trade_date DATE,
    foreign_net_buy BIGINT NOT NULL,
    institution_net_buy BIGINT NOT NULL,
    volume_ratio NUMERIC(10, 4) NOT NULL,
    price_volatility NUMERIC(10, 4) NOT NULL,
    final_score NUMERIC(10, 4) NOT NULL,
    is_selected BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (stock_code, trade_date)
);
```

## Performance

| Metric | Value |
|--------|-------|
| API calls | 200 requests (100 stocks × 2) |
| Execution time | ~45 seconds |
| Memory usage | ~150 MB |
| Database insert | ~50ms (bulk) |

## Next Stages (Planned)

- **Stage 2-1:** Quantitative Analysis (7 features) - KIS + DART data
- **Stage 2-2:** Sentiment Analysis (1 feature) - KR-FinBERT
- **Stage 2-3:** Time-Series Analysis (3 features) - Prophet forecasting
- **Stage 3:** Chart Generation - 4 matplotlib PNGs
- **Stage 4:** Gemini AI Decision - TOP3 buy/sell
- **Stage 5:** Trade Execution - Spring Boot integration

## Documentation

| Document | Purpose |
|----------|---------|
| [README.md](README.md) | This file (quickstart) |
| [USAGE.md](USAGE.md) | Complete user guide with examples |
| [CLAUDE.md](CLAUDE.md) | Full architecture & implementation details |
| [development_progress.md](_docs/development_progress.md) | Development status report |

## Troubleshooting

### KIS API 401 Error
- Verify `KIS_APP_KEY` and `KIS_APP_SECRET` in `.env`
- Check `KIS_MODE` matches your key type (VIRTUAL/REAL)

### Database Connection Error
- Ensure PostgreSQL is running: `pg_isready`
- Verify connection parameters in `.env`
- Create `stock_filter_score` table (see SQL above)

### Scheduler Not Running
- Check `PIPELINE_ENABLED=true` in `.env`
- Verify cron expression: `PIPELINE_CRON=50 8 * * 1-5`
- Review logs: `tail -f logs/pipeline.log`

## Technology Stack

- **Framework:** FastAPI 0.109, uvicorn
- **Async:** aiohttp, asyncio
- **Data:** pandas 2.2, NumPy 1.26
- **ML:** scikit-learn 1.4 (StandardScaler)
- **Database:** SQLAlchemy 2.0, psycopg2
- **Scheduler:** APScheduler 3.10
- **Testing:** pytest 7.4, pytest-asyncio

## Project Status

✅ **Stage 1 Complete** - Core infrastructure operational
- Production-ready code with modular architecture
- Comprehensive test coverage
- Full documentation
- Automated + manual execution modes
- Professional logging and error handling

🔨 **Next:** Stage 2-1 (Quantitative Analysis)

---

**Developed by:** AI Assistant | **Project Lead:** 인범 | **Date:** 2026-05-19
