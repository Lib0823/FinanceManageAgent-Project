# Dorothy Integration Guide for FinanceManage Agent Project

## 🎯 Overview

This guide explains how to use Dorothy to manage and develop the FinanceManage Agent Project efficiently. Dorothy acts as an orchestrator framework that maximizes AI agent productivity for your financial trading system.

## 📂 Project Structure After Integration

```
FinanceManage_Agent-Project/
├── dorothy-config.json         # Dorothy integration configuration
├── dorothy-integration.sh      # Unified management script
├── DOROTHY_INTEGRATION_GUIDE.md # This guide
├── web-app/                    # Vue3 Frontend
├── api-server/                 # Spring Boot Backend
├── ai-agent/                   # FastAPI AI Pipeline
└── database/                   # PostgreSQL Schema

Dorothy/
└── skills/
    └── finance-manager/        # FinanceManage skill for Dorothy
        └── SKILL.md           # Skill documentation

~/.claude/projects/financemanage-agent-project/
└── memory/                     # Project memory for Claude Code
    ├── MEMORY.md              # Main memory file
    ├── session.log            # Service session logs
    ├── analysis.log           # Analysis execution logs
    └── trades.log             # Trading activity logs
```

## 🚀 Quick Start

### 1. Initial Setup
```bash
# Navigate to project directory
cd /Users/inbeom/IdeaProjects/FinanceManage_Agent-Project

# Run setup (already completed)
./dorothy-integration.sh setup
```

### 2. Start Services
```bash
# Start all services
./dorothy-integration.sh start

# Check service status
./dorothy-integration.sh status
```

### 3. Access Applications
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8080/api
- **AI Agent**: http://localhost:8000
- **PostgreSQL**: localhost:5432

## 💻 Dorothy Commands

Dorothy provides these commands for managing your project:

### Service Management
```bash
# Start all services
/finance-start

# Stop all services
/finance-stop

# Check status
/finance-status
```

### Development Commands
```bash
# Start frontend dev server
/finance-dev frontend start

# Run backend tests
/finance-dev backend test

# View AI agent logs
/finance-dev ai logs
```

### Trading Operations
```bash
# Trigger stock analysis
/finance-analyze              # Analyze all top 30
/finance-analyze 005930       # Analyze specific stock

# Trading commands
/finance-trade status         # Show current holdings
/finance-trade buy 005930 10  # Buy stocks
/finance-trade sell 005930 5  # Sell stocks
/finance-trade history        # View trade history
```

### Chart Management
```bash
# View charts
/finance-chart heatmap       # View heatmap
/finance-chart sentiment     # View sentiment analysis
/finance-chart forecast      # View Prophet forecast
/finance-chart all          # View all charts
```

## 🧠 Memory System

Dorothy integrates with Claude Code's native memory system:

### Memory Location
```
~/.claude/projects/financemanage-agent-project/memory/
```

### Memory Files
- **MEMORY.md**: Main project context and key information
- **session.log**: Service start/stop logs
- **analysis.log**: Stock analysis execution history
- **trades.log**: Trading activity records

### Using Memory in Dorothy
1. Dorothy automatically reads MEMORY.md at session start
2. Updates are saved after significant operations
3. Access memory directly: `./dorothy-integration.sh memory show`
4. Edit memory: `./dorothy-integration.sh memory edit`

## 📊 Daily Trading Pipeline

The system runs automatically at **08:50 KST on weekdays**:

1. **Stock Filtering**: KOSPI 100 → Top 30 using ML scoring
2. **Data Collection**: KIS API, DART financials, News RSS
3. **3-Way Analysis**:
   - Quantitative features
   - Sentiment analysis (KR-FinBERT)
   - Time-series forecasting (Prophet)
4. **Chart Generation**: 4 matplotlib charts
5. **AI Decision**: Gemini API → Buy/Sell TOP3
6. **Trade Execution**: If enabled, execute via KIS API

## 🛠️ Development Workflow

### 1. Frontend Development
```bash
# Start Vue dev server with hot reload
./dorothy-integration.sh dev frontend start

# Build for production
./dorothy-integration.sh dev frontend build

# Run tests
./dorothy-integration.sh dev frontend test
```

### 2. Backend Development
```bash
# Start Spring Boot with hot reload
./dorothy-integration.sh dev backend start

# Run tests
./dorothy-integration.sh dev backend test

# Build JAR
./dorothy-integration.sh dev backend build
```

### 3. AI Agent Development
```bash
# Start FastAPI with auto-reload
./dorothy-integration.sh dev ai start

# Install dependencies
./dorothy-integration.sh dev ai install

# Run pytest
./dorothy-integration.sh dev ai test
```

## 📝 Configuration

### Dorothy Configuration
Edit `dorothy-config.json` to customize:
- Service ports
- Docker settings
- MCP server configurations
- Workflow schedules

### Environment Variables
Create `.env` file in project root:
```env
# KIS API (Mock Trading)
KIS_APP_KEY=your_app_key
KIS_APP_SECRET=your_app_secret

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=finance_manage
DB_USER=postgres
DB_PASSWORD=postgres

# Gemini AI
GEMINI_API_KEY=your_gemini_key
```

## 🐛 Troubleshooting

### Services Not Starting
```bash
# Check Docker status
docker ps

# View service logs
./dorothy-integration.sh logs all

# Restart services
./dorothy-integration.sh restart
```

### Analysis Failures
```bash
# Check AI agent logs
./dorothy-integration.sh logs ai

# Verify API keys
cat .env

# Manual trigger
./dorothy-integration.sh analyze
```

### Database Issues
```bash
# Check PostgreSQL logs
./dorothy-integration.sh logs db

# Connect to database
docker exec -it financemanage_postgres psql -U postgres
```

### Chart Generation Problems
```bash
# Check static directory
ls -la ai-agent/static/charts/

# Verify matplotlib
docker exec -it financemanage_ai pip list | grep matplotlib

# Check Korean font
docker exec -it financemanage_ai fc-list | grep Nanum
```

## 📚 Advanced Features

### Custom MCP Servers
Dorothy can be extended with custom MCP servers for FinanceManage:

1. **finance-orchestrator**: Orchestrates trading operations
2. **data-collector**: Manages API data collection
3. **chart-generator**: Handles visualization

### Integration with Dorothy's MCP Servers
- **mcp-orchestrator**: Coordinates multi-agent tasks
- **mcp-telegram**: Send trade notifications
- **mcp-vault**: Secure API key storage
- **mcp-kanban**: Track development tasks

### Session Persistence
Dorothy maintains session context between restarts:
- Trade decisions are logged
- Analysis results are preserved
- Configuration changes are tracked

## 🔗 Useful Links

- **Frontend**: http://localhost:5173
- **Backend Swagger**: http://localhost:8080/swagger-ui
- **AI Agent Docs**: http://localhost:8000/docs
- **Charts**: http://localhost:8000/static/charts/

## 💡 Tips & Best Practices

1. **Always use Dorothy commands** for consistency
2. **Check memory** at session start for context
3. **Update memory** after significant changes
4. **Use Docker Compose** for full system testing
5. **Monitor logs** during development
6. **Backup configuration** before major changes

## 📞 Support

For issues or questions:
1. Check logs: `./dorothy-integration.sh logs all`
2. Review memory: `./dorothy-integration.sh memory show`
3. Restart services: `./dorothy-integration.sh restart`

---

**Note**: This integration enhances your development workflow by combining Dorothy's orchestration capabilities with Claude Code's AI assistance, creating a powerful environment for financial trading system development.