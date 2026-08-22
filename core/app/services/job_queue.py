import asyncio
import uuid
import time
from typing import Dict, Any, Optional, Callable, Awaitable
from enum import Enum
from app.logger import logger

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class JobRecord:
    def __init__(self, job_id: str, job_type: str, payload: Dict[str, Any]) -> None:
        self.job_id = job_id
        self.job_type = job_type
        self.payload = payload
        self.status = JobStatus.PENDING
        self.progress = 0.0
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.created_at = time.time()
        self.completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status.value,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "completed_at": self.completed_at
        }

class JobQueueService:
    def __init__(self) -> None:
        self.jobs: Dict[str, JobRecord] = {}
        self.queue: asyncio.Queue[JobRecord] = asyncio.Queue()
        self._handlers: Dict[str, Callable[[JobRecord], Awaitable[Dict[str, Any]]]] = {}
        self._worker_task: Optional[asyncio.Task] = None
        self.is_running = False

    def register_handler(self, job_type: str, handler: Callable[[JobRecord], Awaitable[Dict[str, Any]]]) -> None:
        self._handlers[job_type] = handler

    def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("Job queue worker started")

    async def stop(self) -> None:
        self.is_running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await asyncio.wait_for(self._worker_task, timeout=0.2)
            except (asyncio.CancelledError, asyncio.TimeoutError, Exception):
                pass
        logger.info("Job queue worker stopped")

    async def submit_job(self, job_type: str, payload: Optional[Dict[str, Any]] = None) -> JobRecord:
        job_id = str(uuid.uuid4())
        record = JobRecord(job_id=job_id, job_type=job_type, payload=payload or {})
        self.jobs[job_id] = record
        await self.queue.put(record)
        return record

    async def update_progress(self, job_id: str, progress: float) -> None:
        if job_id in self.jobs:
            self.jobs[job_id].progress = max(0.0, min(100.0, progress))

    def get_job(self, job_id: str) -> Optional[JobRecord]:
        return self.jobs.get(job_id)

    async def _worker_loop(self) -> None:
        while self.is_running:
            try:
                record = await self.queue.get()
                record.status = JobStatus.RUNNING

                handler = self._handlers.get(record.job_type)
                if handler:
                    try:
                        record.result = await handler(record)
                        record.status = JobStatus.COMPLETED
                        record.progress = 100.0
                    except Exception as e:
                        record.status = JobStatus.FAILED
                        record.error = str(e)
                        logger.error(f"Job {record.job_id} failed: {e}")
                else:
                    await asyncio.sleep(0.01)
                    record.result = {"message": f"Executed default task for {record.job_type}"}
                    record.status = JobStatus.COMPLETED
                    record.progress = 100.0

                record.completed_at = time.time()
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Job worker error: {e}")

job_queue_service = JobQueueService()
