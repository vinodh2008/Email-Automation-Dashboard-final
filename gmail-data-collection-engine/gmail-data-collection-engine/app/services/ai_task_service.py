"""
AITaskService — Execute AI tasks with knowledge injection and provider failover.
Phase 2B: Manages per-category AI task execution pipeline.
"""
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

logger = logging.getLogger("ai_task_service")


class AITaskService:
    def __init__(self, db: Session):
        self.db = db

    def get_tasks_for_category(self, category_id: str) -> List[Dict[str, Any]]:
        """Get all AI tasks for a category, ordered by execution_order."""
        try:
            from app.models.ai_task import AITask
            tasks = self.db.query(AITask).filter(
                AITask.business_category_id == category_id,
                AITask.is_enabled == True
            ).order_by(AITask.execution_order.asc()).all()
            
            return [{
                "id": str(t.id),
                "task_type": t.task_type,
                "name": t.name,
                "description": t.description,
                "prompt_template_id": str(t.prompt_template_id) if t.prompt_template_id else None,
                "model_override": t.model_override,
                "temperature_override": t.temperature_override,
                "max_tokens_override": t.max_tokens_override,
                "execution_order": t.execution_order,
                "config": t.config,
            } for t in tasks]
        except Exception as e:
            logger.error(f"[AI_TASK] Failed to get tasks for category {category_id}: {e}")
            return []

    def execute_task(self, task_id: str, email_id: str, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Execute a single AI task on an email."""
        try:
            from app.models.ai_task import AITask
            from app.models.email import Email
            from app.models.business_category import BusinessCategory
            from app.services.ai_service import AIService
            from app.services.prompt_builder_service import PromptBuilderService
            from app.services.variable_resolver import VariableResolver
            
            task = self.db.query(AITask).filter(AITask.id == task_id).first()
            if not task:
                logger.error(f"[AI_TASK] Task {task_id} not found")
                return None
            
            email = self.db.query(Email).filter(Email.id == email_id).first()
            if not email:
                logger.error(f"[AI_TASK] Email {email_id} not found")
                return None
            
            category = self.db.query(BusinessCategory).filter(
                BusinessCategory.id == task.business_category_id
            ).first()
            
            prompt_content = ""
            if task.prompt_template_id:
                from app.models.business_prompt_template import BusinessPromptTemplate
                template = self.db.query(BusinessPromptTemplate).filter(
                    BusinessPromptTemplate.id == task.prompt_template_id
                ).first()
                if template:
                    prompt_content = template.prompt_content
            
            if not prompt_content:
                prompt_content = self._get_default_prompt(task.task_type)
            
            variable_values = {
                "email_sender": email.sender_email or "",
                "email_subject": email.subject or "",
                "email_body": email.body_text or email.snippet or "",
                "customer_name": (email.sender_email or "").split("@")[0],
                "company_name": "Utservio",
            }
            
            resolver = VariableResolver(self.db)
            resolution = resolver.resolve(prompt_content, variable_values)
            rendered_prompt = resolution.get("rendered_prompt", prompt_content)
            
            knowledge_context = self._get_knowledge_context(str(task.business_category_id))
            if knowledge_context:
                rendered_prompt += f"\n\n--- Knowledge Context ---\n{knowledge_context}"
            
            ai_service = AIService(db=self.db)
            category_config = {}
            if category:
                category_config = {
                    "model": task.model_override or category.ai_model,
                    "temperature": task.temperature_override or category.ai_temperature,
                    "max_tokens": task.max_tokens_override or category.ai_max_tokens,
                }
            
            generated_content = ai_service.generate_reply(rendered_prompt)
            
            return {
                "task_id": str(task.id),
                "task_type": task.task_type,
                "email_id": email_id,
                "generated_content": generated_content,
                "prompt_used": rendered_prompt[:500],
                "knowledge_used": bool(knowledge_context),
                "category_config": category_config,
                "status": "success",
            }
            
        except Exception as e:
            logger.error(f"[AI_TASK] Failed to execute task {task_id}: {e}")
            return {
                "task_id": task_id,
                "email_id": email_id,
                "status": "failed",
                "error": str(e),
            }

    def execute_task_chain(self, email_id: str, category_id: str) -> List[Dict[str, Any]]:
        """Execute all enabled AI tasks for a category in execution_order."""
        tasks = self.get_tasks_for_category(category_id)
        results = []
        
        for task_info in tasks:
            result = self.execute_task(task_info["id"], email_id)
            if result:
                results.append(result)
        
        return results

    def _get_default_prompt(self, task_type: str) -> str:
        """Get default prompt template for a task type."""
        prompts = {
            "classify": "Classify this email into a business category. Subject: {{email_subject}}\nFrom: {{email_sender}}\nBody: {{email_body}}",
            "summarize": "Summarize this email concisely:\nSubject: {{email_subject}}\nFrom: {{email_sender}}\nBody: {{email_body}}",
            "generate_reply": "Draft a professional response to this email:\nSubject: {{email_subject}}\nFrom: {{email_sender}}\nBody: {{email_body}}",
            "extract": "Extract key entities (order numbers, dates, amounts, names) from this email:\nSubject: {{email_subject}}\nBody: {{email_body}}",
            "route": "Suggest which department should handle this email:\nSubject: {{email_subject}}\nBody: {{email_body}}",
        }
        return prompts.get(task_type, "Process this email: {{email_subject}}\n{{email_body}}")

    def _get_knowledge_context(self, category_id: str) -> Optional[str]:
        """Retrieve knowledge context for a category (Phase 2B: simple text search)."""
        try:
            from app.models.knowledge_source import KnowledgeSource
            sources = self.db.query(KnowledgeSource).filter(
                KnowledgeSource.business_category_id == category_id,
                KnowledgeSource.is_active == True,
                KnowledgeSource.embedding_status == "ready"
            ).limit(3).all()
            
            if not sources:
                return None
            
            context_parts = []
            for source in sources:
                if source.content_text:
                    context_parts.append(f"[{source.name}]: {source.content_text[:500]}")
            
            return "\n\n".join(context_parts) if context_parts else None
        except Exception as e:
            logger.error(f"[AI_TASK] Failed to get knowledge context: {e}")
            return None

    def create_task(self, category_id: str, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new AI task for a category."""
        try:
            from app.models.ai_task import AITask
            import uuid
            
            task = AITask(
                business_category_id=uuid.UUID(category_id),
                task_type=task_data["task_type"],
                name=task_data["name"],
                description=task_data.get("description"),
                prompt_template_id=uuid.UUID(task_data["prompt_template_id"]) if task_data.get("prompt_template_id") else None,
                model_override=task_data.get("model_override"),
                temperature_override=task_data.get("temperature_override"),
                max_tokens_override=task_data.get("max_tokens_override"),
                execution_order=task_data.get("execution_order", 0),
                config=task_data.get("config", {}),
            )
            self.db.add(task)
            self.db.commit()
            return {"id": str(task.id), "status": "created"}
        except Exception as e:
            self.db.rollback()
            logger.error(f"[AI_TASK] Failed to create task: {e}")
            return None

    def update_task(self, task_id: str, task_data: Dict[str, Any]) -> bool:
        """Update an AI task."""
        try:
            from app.models.ai_task import AITask
            task = self.db.query(AITask).filter(AITask.id == task_id).first()
            if not task:
                return False
            for key, val in task_data.items():
                if hasattr(task, key) and val is not None:
                    setattr(task, key, val)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"[AI_TASK] Failed to update task {task_id}: {e}")
            return False

    def delete_task(self, task_id: str) -> bool:
        """Delete an AI task."""
        try:
            from app.models.ai_task import AITask
            task = self.db.query(AITask).filter(AITask.id == task_id).first()
            if not task:
                return False
            self.db.delete(task)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"[AI_TASK] Failed to delete task {task_id}: {e}")
            return False