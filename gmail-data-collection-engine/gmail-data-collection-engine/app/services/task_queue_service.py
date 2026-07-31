"""
TaskQueueService — Database-backed async task queue.
Phase 2B: Core infrastructure for non-blocking email processing pipeline.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger("task_queue_service")


class TaskQueueService:
    def __init__(self, db: Session):
        self.db = db

    def enqueue(
        self,
        queue_name: str,
        task_type: str,
        entity_type: str,
        entity_id: str,
        payload: Optional[Dict[str, Any]] = None,
        priority: int = 5,
        delay_seconds: int = 0,
    ) -> str:
        """Enqueue a new task. Returns the task ID."""
        try:
            from app.models.task_queue import TaskQueue
            import uuid
            
            scheduled_at = datetime.now(timezone.utc)
            if delay_seconds > 0:
                from datetime import timedelta
                scheduled_at = scheduled_at + timedelta(seconds=delay_seconds)
            
            task = TaskQueue(
                queue_name=queue_name,
                task_type=task_type,
                entity_type=entity_type,
                entity_id=entity_id,
                payload=payload or {},
                priority=priority,
                scheduled_at=scheduled_at,
                status="pending",
            )
            self.db.add(task)
            self.db.commit()
            logger.info(f"[TASK_QUEUE] Enqueued task: {task_type} for {entity_type}:{entity_id} (priority={priority})")
            return str(task.id)
        except Exception as e:
            self.db.rollback()
            logger.error(f"[TASK_QUEUE] Failed to enqueue task: {e}")
            raise

    def dequeue(self, queue_name: Optional[str] = None, limit: int = 1) -> List[Dict[str, Any]]:
        """Fetch pending tasks and mark them as processing. Returns list of task dicts."""
        try:
            from app.models.task_queue import TaskQueue
            
            query = self.db.query(TaskQueue).filter(
                TaskQueue.status == "pending",
                TaskQueue.scheduled_at <= datetime.now(timezone.utc),
            )
            if queue_name:
                query = query.filter(TaskQueue.queue_name == queue_name)
            
            tasks = query.order_by(
                TaskQueue.priority.desc(),
                TaskQueue.scheduled_at.asc()
            ).limit(limit).all()
            
            result = []
            for task in tasks:
                task.status = "processing"
                task.started_at = datetime.now(timezone.utc)
                result.append({
                    "id": str(task.id),
                    "queue_name": task.queue_name,
                    "task_type": task.task_type,
                    "entity_type": task.entity_type,
                    "entity_id": str(task.entity_id),
                    "payload": task.payload or {},
                    "priority": task.priority,
                    "retry_count": task.retry_count,
                })
            
            if result:
                self.db.commit()
                logger.info(f"[TASK_QUEUE] Dequeued {len(result)} task(s)")
            
            return result
        except Exception as e:
            self.db.rollback()
            logger.error(f"[TASK_QUEUE] Failed to dequeue: {e}")
            return []

    def complete(self, task_id: str, result: Optional[Dict[str, Any]] = None) -> bool:
        """Mark a task as completed."""
        try:
            from app.models.task_queue import TaskQueue
            task = self.db.query(TaskQueue).filter(TaskQueue.id == task_id).first()
            if not task:
                return False
            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc)
            if result:
                task.payload = {**(task.payload or {}), "result": result}
            self.db.commit()
            logger.info(f"[TASK_QUEUE] Task {task_id} completed")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"[TASK_QUEUE] Failed to complete task {task_id}: {e}")
            return False

    def fail(self, task_id: str, error_message: str) -> bool:
        """Mark a task as failed. Auto-retry if under max_retries."""
        try:
            from app.models.task_queue import TaskQueue
            task = self.db.query(TaskQueue).filter(TaskQueue.id == task_id).first()
            if not task:
                return False
            
            task.retry_count += 1
            task.error_message = error_message
            
            if task.retry_count >= task.max_retries:
                task.status = "dead_letter"
                logger.warning(f"[TASK_QUEUE] Task {task_id} moved to dead_letter after {task.retry_count} retries")
            else:
                task.status = "pending"
                task.started_at = None
                logger.info(f"[TASK_QUEUE] Task {task_id} scheduled for retry ({task.retry_count}/{task.max_retries})")
            
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"[TASK_QUEUE] Failed to fail task {task_id}: {e}")
            return False

    def retry(self, task_id: str) -> bool:
        """Manually retry a failed/dead_letter task."""
        try:
            from app.models.task_queue import TaskQueue
            task = self.db.query(TaskQueue).filter(TaskQueue.id == task_id).first()
            if not task or task.status not in ("failed", "dead_letter"):
                return False
            task.status = "pending"
            task.retry_count = 0
            task.error_message = None
            task.started_at = None
            task.scheduled_at = datetime.now(timezone.utc)
            self.db.commit()
            logger.info(f"[TASK_QUEUE] Task {task_id} manually retried")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"[TASK_QUEUE] Failed to retry task {task_id}: {e}")
            return False

    def cancel(self, task_id: str) -> bool:
        """Cancel a pending task."""
        try:
            from app.models.task_queue import TaskQueue
            task = self.db.query(TaskQueue).filter(TaskQueue.id == task_id).first()
            if not task or task.status != "pending":
                return False
            task.status = "cancelled"
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            return False

    def get_stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        try:
            result = self.db.execute(text("""
                SELECT status, COUNT(*) as cnt FROM task_queue GROUP BY status
            """))
            stats = {row.status: row.cnt for row in result}
            return {
                "pending": stats.get("pending", 0),
                "processing": stats.get("processing", 0),
                "completed": stats.get("completed", 0),
                "failed": stats.get("failed", 0),
                "dead_letter": stats.get("dead_letter", 0),
                "cancelled": stats.get("cancelled", 0),
            }
        except Exception as e:
            logger.error(f"[TASK_QUEUE] Failed to get stats: {e}")
            return {}

    def get_pending_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List pending tasks."""
        try:
            from app.models.task_queue import TaskQueue
            tasks = self.db.query(TaskQueue).filter(
                TaskQueue.status == "pending"
            ).order_by(TaskQueue.priority.desc(), TaskQueue.scheduled_at.asc()).limit(limit).all()
            
            return [{
                "id": str(t.id),
                "queue_name": t.queue_name,
                "task_type": t.task_type,
                "entity_type": t.entity_type,
                "entity_id": str(t.entity_id),
                "status": t.status,
                "priority": t.priority,
                "retry_count": t.retry_count,
                "scheduled_at": t.scheduled_at.isoformat() if t.scheduled_at else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            } for t in tasks]
        except Exception as e:
            logger.error(f"[TASK_QUEUE] Failed to get pending tasks: {e}")
            return []

    def cleanup_completed(self, older_than_hours: int = 24) -> int:
        """Delete completed tasks older than specified hours."""
        try:
            from app.models.task_queue import TaskQueue
            from datetime import timedelta
            cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
            deleted = self.db.query(TaskQueue).filter(
                TaskQueue.status == "completed",
                TaskQueue.completed_at < cutoff
            ).delete()
            self.db.commit()
            return deleted
        except Exception as e:
            self.db.rollback()
            logger.error(f"[TASK_QUEUE] Failed to cleanup: {e}")
            return 0