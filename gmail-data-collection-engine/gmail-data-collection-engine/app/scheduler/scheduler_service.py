"""
SchedulerService — Single Source of Truth for APScheduler Management & Status Metrics.
"""
import logging
import time
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED, EVENT_JOB_MAX_INSTANCES
from app.config import settings
from app.scheduler.jobs import poll_mailboxes_job, process_task_queue_job

logger = logging.getLogger("scheduler_service")


class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)
        
        # --- Runtime Status Metrics ---
        self.execution_count = 0
        self.failure_count = 0
        self.last_run_at = None
        self.last_run_duration_seconds = 0.0
        self.last_error_message = None
        self._job_start_times = {}

    def _event_listener(self, event):
        job_id = event.job_id
        if event.code == EVENT_JOB_EXECUTED:
            self.execution_count += 1
            self.last_run_at = datetime.now(timezone.utc)
            start_time = self._job_start_times.pop(job_id, None)
            if start_time:
                self.last_run_duration_seconds = round(time.time() - start_time, 2)
            logger.info(f"[SCHEDULER_METRICS] Job '{job_id}' executed successfully. Total runs: {self.execution_count}")

        elif event.code == EVENT_JOB_ERROR:
            self.failure_count += 1
            self.last_error_message = str(event.exception)
            logger.error(f"[SCHEDULER_METRICS] Job '{job_id}' failed: {event.exception}")

        elif event.code == EVENT_JOB_MISSED:
            logger.warning(f"[SCHEDULER_METRICS] Job '{job_id}' missed its execution window.")

    def start(self):
        """Initializes jobs and starts APScheduler if enabled."""
        if not settings.scheduler_enabled:
            logger.warning("[SCHEDULER_SERVICE] SCHEDULER_ENABLED is False. Skipping scheduler startup.")
            return

        if self.scheduler.running:
            logger.info("[SCHEDULER_SERVICE] Scheduler is already running.")
            return

        # Add event listeners for metrics
        self.scheduler.add_listener(
            self._event_listener,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED | EVENT_JOB_MAX_INSTANCES
        )

        # Register poll job safely
        job_id = "gmail_incremental_poll"
        if not self.scheduler.get_job(job_id):
            self.scheduler.add_job(
                poll_mailboxes_job,
                'interval',
                minutes=settings.sync_interval_minutes,
                id=job_id,
                max_instances=settings.max_sync_instances,
                coalesce=True,
                misfire_grace_time=settings.sync_misfire_grace_seconds,
                replace_existing=True
            )
            logger.info(f"[SCHEDULER_SERVICE] Registered job '{job_id}' every {settings.sync_interval_minutes} minute(s).")

        # Register task queue processor job
        task_job_id = "task_queue_processor"
        if not self.scheduler.get_job(task_job_id):
            self.scheduler.add_job(
                process_task_queue_job,
                'interval',
                seconds=5,
                id=task_job_id,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=10,
                replace_existing=True
            )
            logger.info(f"[SCHEDULER_SERVICE] Registered job '{task_job_id}' every 5 seconds.")

        self.scheduler.start()
        logger.info("[SCHEDULER_SERVICE] APScheduler started successfully.")

    def shutdown(self):
        """Gracefully shuts down APScheduler."""
        if self.scheduler.running:
            logger.info("[SCHEDULER_SERVICE] Shutting down APScheduler gracefully...")
            self.scheduler.shutdown(wait=False)
            logger.info("[SCHEDULER_SERVICE] APScheduler stopped.")

    def get_status(self) -> dict:
        """Returns comprehensive live runtime status and health metrics."""
        is_running = self.scheduler.running if self.scheduler else False
        
        job = self.scheduler.get_job("gmail_incremental_poll") if is_running else None
        next_run_at = job.next_run_time.isoformat() if job and job.next_run_time else None

        health_state = "healthy"
        if not is_running:
            health_state = "disabled" if not settings.scheduler_enabled else "stopped"
        elif self.failure_count > 0 and self.execution_count == 0:
            health_state = "degraded"

        registered_jobs = []
        if is_running:
            for j in self.scheduler.get_jobs():
                registered_jobs.append({
                    "id": j.id,
                    "name": j.name,
                    "next_run_time": j.next_run_time.isoformat() if j.next_run_time else None,
                    "trigger": str(j.trigger)
                })

        return {
            "is_running": is_running,
            "scheduler_enabled": settings.scheduler_enabled,
            "timezone": settings.scheduler_timezone,
            "sync_interval_minutes": settings.sync_interval_minutes,
            "health_state": health_state,
            "execution_count": self.execution_count,
            "failure_count": self.failure_count,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_run_duration_seconds": self.last_run_duration_seconds,
            "next_run_at": next_run_at,
            "last_error": self.last_error_message,
            "registered_jobs": registered_jobs
        }


# Global singleton instance
scheduler_service = SchedulerService()
