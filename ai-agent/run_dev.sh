#!/bin/bash
# FastAPI Development Server Runner

# Move to ai-agent directory
cd "$(dirname "$0")"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Virtual environment not found. Creating..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Run FastAPI with uvicorn
echo "Starting FastAPI server at http://localhost:8000"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
