"""FastAPI application for AI Agent pipeline."""
import logging
import sys
import math
from datetime import date, datetime
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from pipeline import PipelineScheduler, PipelineOrchestrator
from database import DatabaseRepository
from config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


# Global instances
scheduler: Optional[PipelineScheduler] = None
orchestrator: Optional[PipelineOrchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan event handler for startup/shutdown."""
    global scheduler, orchestrator

    # Startup
    logger.info("Starting AI Agent application...")

    # Initialize orchestrator (reused for manual API calls)
    orchestrator = PipelineOrchestrator()
    logger.info("PipelineOrchestrator initialized (OAuth token will be cached)")

    # Initialize scheduler
    scheduler = PipelineScheduler()
    scheduler.start()
    logger.info("Application started successfully")

    yield

    # Shutdown
    logger.info("Shutting down AI Agent application...")
    if scheduler:
        scheduler.stop()
    logger.info("Application shut down successfully")


app = FastAPI(
    title="AI Agent - Stock Analysis Pipeline",
    description="Automated stock filtering and analysis pipeline",
    version="1.0.0",
    lifespan=lifespan
)


# Request/Response models
class ManualTriggerRequest(BaseModel):
    """Request model for manual pipeline trigger."""
    trade_date: Optional[str] = None  # Format: YYYY-MM-DD
    holdings: Optional[List[str]] = None


class PipelineStatusResponse(BaseModel):
    """Response model for pipeline status."""
    scheduler_running: bool
    next_run_time: Optional[str]
    latest_execution_date: Optional[str]


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "AI Agent - Stock Analysis Pipeline",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/pipeline/trigger")
async def trigger_pipeline_manual(
    request: ManualTriggerRequest,
    background_tasks: BackgroundTasks
):
    """
    Manually trigger complete pipeline execution.

    Args:
        request: Optional trade_date and holdings

    Returns:
        Execution results
    """
    global orchestrator

    if orchestrator is None:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")

    logger.info(f"Manual trigger request received: {request.dict()}")

    # Parse trade date if provided
    trade_date_obj = None
    if request.trade_date:
        try:
            trade_date_obj = date.fromisoformat(request.trade_date)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date format: {request.trade_date}. Use YYYY-MM-DD"
            )

    # Execute pipeline using global orchestrator (OAuth token cached)
    try:
        result = await orchestrator.run_complete_pipeline(
            trade_date=trade_date_obj,
            holdings=request.holdings
        )

        # Convert date objects and invalid float values for JSON serialization
        def convert_dates(obj):
            """
            Recursively convert date/datetime objects to ISO format strings
            and invalid float values (inf, -inf, NaN) to None.
            """
            # Check datetime first (subclass of date)
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, date):
                return obj.isoformat()
            elif isinstance(obj, float):
                # Handle invalid float values
                if math.isinf(obj) or math.isnan(obj):
                    return None
                return obj
            elif isinstance(obj, dict):
                return {k: convert_dates(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_dates(item) for item in obj]
            return obj

        result = convert_dates(result)

        if result['success']:
            return JSONResponse(
                status_code=200,
                content={
                    "message": "Pipeline executed successfully",
                    "result": result
                }
            )
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "message": "Pipeline execution failed",
                    "result": result
                }
            )

    except Exception as e:
        logger.exception(f"Error during manual pipeline execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pipeline/status", response_model=PipelineStatusResponse)
async def get_pipeline_status():
    """
    Get current pipeline status.

    Returns:
        Scheduler status and latest execution date
    """
    global scheduler

    if scheduler is None:
        raise HTTPException(status_code=500, detail="Scheduler not initialized")

    # Get next run time
    next_run = scheduler.get_next_run_time()
    next_run_str = next_run.isoformat() if next_run else None

    # Get latest execution date from database
    db_repo = DatabaseRepository()
    latest_date = db_repo.get_latest_filter_date()
    latest_date_str = latest_date.isoformat() if latest_date else None

    return PipelineStatusResponse(
        scheduler_running=scheduler.scheduler.running,
        next_run_time=next_run_str,
        latest_execution_date=latest_date_str
    )


@app.get("/api/pipeline/results/{trade_date}")
async def get_pipeline_results(trade_date: str):
    """
    Get pipeline results for a specific trade date.

    Args:
        trade_date: Trade date in YYYY-MM-DD format

    Returns:
        Filter scores and selected stocks
    """
    try:
        trade_date_obj = date.fromisoformat(trade_date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format: {trade_date}. Use YYYY-MM-DD"
        )

    db_repo = DatabaseRepository()
    df = db_repo.get_filter_scores(trade_date_obj)

    if df is None or df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No results found for {trade_date}"
        )

    # Convert DataFrame to JSON-serializable format
    results = df.to_dict('records')

    return {
        "trade_date": trade_date,
        "total_stocks": len(results),
        "selected_stocks": len(df[df['is_selected'] == True]),
        "results": results
    }


@app.get("/api/pipeline/selected/{trade_date}")
async def get_selected_stocks(trade_date: str):
    """
    Get list of selected stock codes for a specific date.

    Args:
        trade_date: Trade date in YYYY-MM-DD format

    Returns:
        List of selected stock codes
    """
    try:
        trade_date_obj = date.fromisoformat(trade_date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format: {trade_date}. Use YYYY-MM-DD"
        )

    db_repo = DatabaseRepository()
    selected_codes = db_repo.get_selected_stocks(trade_date_obj)

    if not selected_codes:
        raise HTTPException(
            status_code=404,
            detail=f"No selected stocks found for {trade_date}"
        )

    return {
        "trade_date": trade_date,
        "selected_stocks": len(selected_codes),
        "stock_codes": selected_codes
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
