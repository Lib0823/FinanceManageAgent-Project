#!/bin/bash

# Dorothy Integration Script for FinanceManage Agent Project
# This script provides unified commands for Dorothy to manage the project

set -e

PROJECT_DIR="/Users/inbeom/IdeaProjects/FinanceManage_Agent-Project"
MEMORY_DIR="$HOME/.claude/projects/financemanage-agent-project/memory"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Ensure project directory exists
cd "$PROJECT_DIR" || {
    log_error "Project directory not found: $PROJECT_DIR"
    exit 1
}

# Main command handler
case "$1" in
    start)
        log_info "Starting FinanceManage Agent Project services..."
        docker-compose up -d

        # Wait for services to be ready
        log_info "Waiting for services to initialize..."
        sleep 10

        # Check service health
        if curl -s http://localhost:8080/actuator/health > /dev/null 2>&1; then
            log_info "Backend API is running ✓"
        else
            log_warn "Backend API may not be ready yet"
        fi

        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            log_info "AI Agent is running ✓"
        else
            log_warn "AI Agent may not be ready yet"
        fi

        log_info "Frontend available at http://localhost:5173"
        log_info "All services started successfully!"

        # Update memory
        echo "$(date): Services started via Dorothy" >> "$MEMORY_DIR/session.log"
        ;;

    stop)
        log_info "Stopping FinanceManage Agent Project services..."
        docker-compose down
        log_info "All services stopped"

        # Update memory
        echo "$(date): Services stopped via Dorothy" >> "$MEMORY_DIR/session.log"
        ;;

    restart)
        $0 stop
        sleep 2
        $0 start
        ;;

    status)
        log_info "Checking service status..."
        docker-compose ps
        ;;

    logs)
        service=${2:-all}
        case "$service" in
            frontend|web-app)
                docker-compose logs -f web-app
                ;;
            backend|api-server)
                docker-compose logs -f api-server
                ;;
            ai|ai-agent)
                docker-compose logs -f ai-agent
                ;;
            db|database|postgres)
                docker-compose logs -f postgres
                ;;
            all)
                docker-compose logs -f
                ;;
            *)
                log_error "Unknown service: $service"
                log_info "Available services: frontend, backend, ai, db, all"
                exit 1
                ;;
        esac
        ;;

    dev)
        component=$2
        action=${3:-start}

        case "$component" in
            frontend)
                cd web-app
                case "$action" in
                    start) npm run dev ;;
                    build) npm run build ;;
                    test) npm run test ;;
                    lint) npm run lint ;;
                    *) log_error "Unknown action: $action" ;;
                esac
                ;;
            backend)
                cd api-server
                case "$action" in
                    start) ./gradlew bootRun ;;
                    build) ./gradlew build ;;
                    test) ./gradlew test ;;
                    clean) ./gradlew clean ;;
                    *) log_error "Unknown action: $action" ;;
                esac
                ;;
            ai)
                cd ai-agent
                case "$action" in
                    start) uvicorn main:app --reload --port 8000 ;;
                    test) pytest ;;
                    install) pip install -r requirements.txt ;;
                    *) log_error "Unknown action: $action" ;;
                esac
                ;;
            *)
                log_error "Unknown component: $component"
                log_info "Available components: frontend, backend, ai"
                exit 1
                ;;
        esac
        ;;

    analyze)
        log_info "Triggering stock analysis..."
        stock_code=${2:-all}

        if [ "$stock_code" = "all" ]; then
            curl -X POST http://localhost:8000/api/analyze/trigger
        else
            curl -X POST http://localhost:8000/api/analyze/stock/$stock_code
        fi

        log_info "Analysis triggered. Check charts at http://localhost:8000/static/charts/"

        # Save to memory
        echo "$(date): Analysis triggered for $stock_code" >> "$MEMORY_DIR/analysis.log"
        ;;

    trade)
        action=$2
        case "$action" in
            status)
                log_info "Fetching current holdings..."
                curl http://localhost:8080/api/holdings
                ;;
            history)
                log_info "Fetching trade history..."
                curl http://localhost:8080/api/trades/history
                ;;
            buy|sell)
                stock_code=$3
                quantity=$4
                if [ -z "$stock_code" ] || [ -z "$quantity" ]; then
                    log_error "Usage: $0 trade $action <stock_code> <quantity>"
                    exit 1
                fi

                curl -X POST http://localhost:8080/api/trades/$action \
                    -H "Content-Type: application/json" \
                    -d "{\"stockCode\": \"$stock_code\", \"quantity\": $quantity}"

                # Save to memory
                echo "$(date): Trade $action - $stock_code x$quantity" >> "$MEMORY_DIR/trades.log"
                ;;
            *)
                log_error "Unknown trade action: $action"
                log_info "Available actions: status, history, buy, sell"
                exit 1
                ;;
        esac
        ;;

    memory)
        action=${2:-show}
        case "$action" in
            show)
                log_info "Project memory contents:"
                ls -la "$MEMORY_DIR"
                ;;
            edit)
                ${EDITOR:-nano} "$MEMORY_DIR/MEMORY.md"
                ;;
            clear)
                log_warn "Clearing session logs..."
                rm -f "$MEMORY_DIR"/*.log
                log_info "Session logs cleared"
                ;;
            *)
                log_error "Unknown memory action: $action"
                log_info "Available actions: show, edit, clear"
                exit 1
                ;;
        esac
        ;;

    setup)
        log_info "Setting up Dorothy integration for FinanceManage..."

        # Create memory directory if not exists
        mkdir -p "$MEMORY_DIR"

        # Initialize memory files if not exist
        if [ ! -f "$MEMORY_DIR/MEMORY.md" ]; then
            log_info "Creating initial memory file..."
            cat > "$MEMORY_DIR/MEMORY.md" << 'EOF'
# FinanceManage Agent Project - Memory

## Quick Commands
- Start: `./dorothy-integration.sh start`
- Stop: `./dorothy-integration.sh stop`
- Status: `./dorothy-integration.sh status`
- Logs: `./dorothy-integration.sh logs [service]`
- Analyze: `./dorothy-integration.sh analyze [stock_code]`
- Trade: `./dorothy-integration.sh trade [action] [params]`

## Last Session
- Started: [Pending]
- Analysis: [Pending]
- Trades: [Pending]
EOF
        fi

        # Make script executable
        chmod +x "$PROJECT_DIR/dorothy-integration.sh"

        log_info "Dorothy integration setup complete!"
        log_info "You can now use Dorothy commands to manage the project"
        ;;

    help|*)
        cat << EOF
Dorothy Integration for FinanceManage Agent Project

Usage: $0 <command> [options]

Commands:
    start           Start all services using docker-compose
    stop            Stop all services
    restart         Restart all services
    status          Show service status
    logs [service]  Show logs (services: frontend, backend, ai, db, all)

    dev <component> <action>
                    Development commands for specific components
                    Components: frontend, backend, ai
                    Actions: start, build, test, lint, clean

    analyze [code]  Trigger stock analysis (default: all top 30)

    trade <action> [params]
                    Trading operations
                    Actions: status, history, buy <code> <qty>, sell <code> <qty>

    memory <action> Memory management
                    Actions: show, edit, clear

    setup           Initial setup for Dorothy integration
    help            Show this help message

Examples:
    $0 start                    # Start all services
    $0 dev frontend start       # Start frontend dev server
    $0 analyze 005930          # Analyze Samsung Electronics
    $0 trade buy 005930 10     # Buy 10 shares of Samsung
    $0 logs ai                 # Show AI agent logs
    $0 memory show             # Show memory contents

Dorothy Skill Commands (use in Dorothy):
    /finance-start              # Start services
    /finance-stop              # Stop services
    /finance-analyze [code]    # Run analysis
    /finance-trade [action]    # Trading operations
    /finance-dev [component]   # Development utilities

EOF
        ;;
esac