from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from app.run import run_once
from app.api.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()


app = FastAPI(title="LinkedIn Agent API", lifespan=lifespan)


class RunRequest(BaseModel):
    target_date: Optional[str] = None


@app.post("/run")
async def trigger_run(request: RunRequest, background_tasks: BackgroundTasks):
    """Manually trigger the agent run."""
    def _run():
        result = run_once(request.target_date)
        print(f"Run {result.get('run_id')} completed with status {result.get('status')}")
        
    background_tasks.add_task(_run)
    return {"message": "Run triggered in background."}


@app.get("/health")
async def health_check():
    return {"status": "ok"}
