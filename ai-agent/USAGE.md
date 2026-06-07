# AI Agent Usage Guide

Complete guide for running the AI Agent pipeline (Stage 1: Stock Filtering).

## Quick Start

### 1. Environment Setup

```bash
cd ai-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required environment variables:
```bash
# KIS API (모의투자)
KIS_MODE=VIRTUAL
KIS_APP_KEY=your_kis_app_key
KIS_APP_SECRET=your_kis_app_secret

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=financemanage
DB_USER=postgres
DB_PASSWORD=yourpassword

# Scheduler (optional, defaults provided)
PIPELINE_CRON=50 8 * * 1-5  # Weekdays 08:50 KST
PIPELINE_TIMEZONE=Asia/Seoul
PIPELINE_ENABLED=true
```

### 3. Database Setup

Ensure PostgreSQL is running and `stock_filter_score` table exists:

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

## Running the Pipeline

### Method 1: Automatic Scheduling (Recommended for Production)

Start FastAPI server with built-in scheduler:

```bash
python main.py
```

Or with uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Default Schedule:** Weekdays 08:50 KST (before market open)

The pipeline will run automatically according to `PIPELINE_CRON` setting.

### Method 2: Manual Trigger via API

#### Trigger with default settings (today's date)

```bash
curl -X POST http://localhost:8000/api/pipeline/trigger \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### Trigger with specific date

```bash
curl -X POST http://localhost:8000/api/pipeline/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "trade_date": "2026-05-19"
  }'
```

#### Trigger with holdings inclusion

```bash
curl -X POST http://localhost:8000/api/pipeline/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "trade_date": "2026-05-19",
    "holdings": ["005930", "000660", "051910"]
  }'
```

### Method 3: Python Script (For Testing/Development)

Create `run_pipeline.py`:

```python
import asyncio
from datetime import date
from pipeline import PipelineOrchestrator

async def main():
    orchestrator = PipelineOrchestrator()
    result = await orchestrator.run_stage1_filtering(
        trade_date=date.today(),
        holdings=None  # Optional
    )
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

Run:

```bash
python run_pipeline.py
```

## API Endpoints

### Health Check

```bash
# Check if service is running
GET http://localhost:8000/health
```

### Pipeline Status

```bash
# Get scheduler status and latest execution
GET http://localhost:8000/api/pipeline/status
```

Response:
```json
{
  "scheduler_running": true,
  "next_run_time": "2026-05-20T08:50:00+09:00",
  "latest_execution_date": "2026-05-19"
}
```

### Get Pipeline Results

```bash
# Get full results for a specific date
GET http://localhost:8000/api/pipeline/results/2026-05-19
```

Response:
```json
{
  "trade_date": "2026-05-19",
  "total_stocks": 100,
  "selected_stocks": 30,
  "results": [
    {
      "stock_code": "005930",
      "trade_date": "2026-05-19",
      "foreign_net_buy": 123456789,
      "institutional_net_buy": 98765432,
      "volume_ratio": 2.34,
      "price_volatility": 0.056,
      "final_score": 1.87,
      "is_selected": true
    },
    ...
  ]
}
```

### Get Selected Stocks Only

```bash
# Get only selected stock codes
GET http://localhost:8000/api/pipeline/selected/2026-05-19
```

Response:
```json
{
  "trade_date": "2026-05-19",
  "selected_stocks": 30,
  "stock_codes": [
    "005930",
    "000660",
    "051910",
    ...
  ]
}
```

## Testing

### Run Unit Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_filter.py -v

# With coverage report
pytest --cov=. --cov-report=html tests/
```

### Test Coverage

After running with coverage, open `htmlcov/index.html` in browser.

## Monitoring and Logs

### Log Files

Logs are written to `logs/pipeline.log` by default.

```bash
# View logs in real-time
tail -f logs/pipeline.log

# Search for errors
grep ERROR logs/pipeline.log

# View scheduler logs
grep "Scheduled pipeline" logs/pipeline.log
```

### Log Levels

Configure in `.env`:
```bash
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## Troubleshooting

### KIS API Authentication Error

**Symptom:** `KIS OAuth failed` or `401 Unauthorized`

**Solutions:**
1. Verify `KIS_APP_KEY` and `KIS_APP_SECRET` are correct
2. Check `KIS_MODE` matches your API key type (VIRTUAL vs REAL)
3. Ensure KIS Developers account is active

### Database Connection Error

**Symptom:** `Database error` or `Connection refused`

**Solutions:**
1. Verify PostgreSQL is running: `pg_isready`
2. Check connection parameters in `.env`
3. Test connection: `psql -h localhost -U postgres -d financemanage`
4. Ensure `stock_filter_score` table exists

### Rate Limit Exceeded

**Symptom:** `429 Too Many Requests` or slow API calls

**Solutions:**
1. KIS API limit: 5 requests/second (모의투자)
2. Rate limiting is automatic in `KISClient`
3. Reduce `KOSPI_100` list size for testing

### Scheduler Not Running

**Symptom:** Pipeline doesn't execute automatically

**Solutions:**
1. Check `PIPELINE_ENABLED=true` in `.env`
2. Verify cron expression: `PIPELINE_CRON=50 8 * * 1-5`
3. Check timezone: `PIPELINE_TIMEZONE=Asia/Seoul`
4. View logs for scheduler startup messages

### Empty Results

**Symptom:** `No data found` or empty selected stocks

**Solutions:**
1. Check KIS API is returning data (test with manual call)
2. Verify trade date is a valid trading day (not weekend/holiday)
3. Check KOSPI_100 stock codes are valid
4. Review logs for API errors

## Performance Optimization

### Parallel Execution

KIS API calls are already parallelized with rate limiting:
- 100 stocks × 2 calls = 200 API calls
- Duration: ~40 seconds @ 5 req/sec

### Memory Usage

Expected memory usage: ~100-200 MB
- Pandas DataFrames: ~10 MB for 100 stocks
- KIS API responses: ~50 MB cached
- ML models: ~20 MB (StandardScaler)

### Database Optimization

For large-scale operations:
```sql
-- Add indexes for faster queries
CREATE INDEX idx_filter_date ON stock_filter_score(trade_date);
CREATE INDEX idx_filter_selected ON stock_filter_score(is_selected) WHERE is_selected = true;
```

## Integration with Other Services

### Spring Boot API Server

Pipeline can fetch holdings from API Server:

```python
import aiohttp

async def get_holdings():
    async with aiohttp.ClientSession() as session:
        async with session.get('http://api-server:8080/api/assets/holdings') as resp:
            holdings = await resp.json()
            return [h['stock_code'] for h in holdings]

# Use in pipeline
holdings = await get_holdings()
orchestrator.run_stage1_filtering(holdings=holdings)
```

### Vue3 Frontend

Frontend can trigger and monitor pipeline:

```javascript
// Trigger pipeline
await axios.post('http://localhost:8000/api/pipeline/trigger');

// Get status
const status = await axios.get('http://localhost:8000/api/pipeline/status');

// Get results
const results = await axios.get('http://localhost:8000/api/pipeline/results/2026-05-19');
```

## Production Deployment

### Docker

```bash
# Build image
docker build -t ai-agent:latest .

# Run container
docker run -d \
  --name ai-agent \
  -p 8000:8000 \
  --env-file .env \
  ai-agent:latest
```

### Docker Compose Integration

Add to `docker-compose.yml`:

```yaml
ai-agent:
  build: ./ai-agent
  ports:
    - "8000:8000"
  environment:
    - KIS_MODE=VIRTUAL
    - KIS_APP_KEY=${KIS_APP_KEY}
    - KIS_APP_SECRET=${KIS_APP_SECRET}
    - DB_HOST=postgres
    - DB_NAME=financemanage
  depends_on:
    - postgres
```

### Environment-Specific Configs

Development:
```bash
PIPELINE_ENABLED=false  # Manual trigger only
LOG_LEVEL=DEBUG
```

Production:
```bash
PIPELINE_ENABLED=true
PIPELINE_CRON=50 8 * * 1-5
LOG_LEVEL=INFO
```

## Support

For issues or questions:
1. Check logs: `logs/pipeline.log`
2. Review API documentation: `http://localhost:8000/docs`
3. Consult CLAUDE.md for architecture details
4. See development progress: `_docs/development_progress.md`
