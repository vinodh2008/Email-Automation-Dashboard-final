import logging
import traceback
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.service import BaseService
from app.models.email import Email
from app.models.workflow import Workflow, WorkflowExecution
from app.repositories.workflow_repository import WorkflowRepository
from app.repositories.workflow_execution_repository import WorkflowExecutionRepository
from app.schemas.workflow_execution import WorkflowExecutionCreate

logger = logging.getLogger("workflow_execution")

class WorkflowExecutionService(BaseService):
    """
    Service responsible for loading active workflows, evaluating email conditions,
    executing defined actions, and logging the results. 
    """
    def __init__(self, db: Session):
        super().__init__(db)
        self.workflow_repo = WorkflowRepository(db)
        self.execution_repo = WorkflowExecutionRepository(db)
        self._active_workflows_cache: Dict[str, List[Workflow]] = {}

    def _get_active_workflows(self, mailbox_account_id: str) -> List[Workflow]:
        """Caches active workflows in memory for the duration of the sync run to avoid N+1 queries."""
        if mailbox_account_id not in self._active_workflows_cache:
            workflows = self.db.query(Workflow).filter(
                Workflow.mailbox_account_id == mailbox_account_id,
                Workflow.is_active == True
            ).all()
            self._active_workflows_cache[mailbox_account_id] = workflows
        return self._active_workflows_cache[mailbox_account_id]

    def process_email(self, email: Email) -> None:
        """
        Evaluates a newly synced email against all active workflows.
        Isolates failures so one bad workflow doesn't break the others.
        """
        mailbox_id = str(email.mailbox_account_id)
        workflows = self._get_active_workflows(mailbox_id)
        
        for workflow in workflows:
            # Avoid duplicate execution for the same email and workflow
            existing = self.db.query(WorkflowExecution).filter(
                WorkflowExecution.workflow_id == workflow.id,
                WorkflowExecution.email_id == email.id
            ).first()
            if existing:
                continue

            try:
                self._evaluate_and_execute(email, workflow)
            except Exception as e:
                logger.error(f"[WORKFLOW] Failed executing workflow {workflow.id} on email {email.id}: {e}")
                self.db.rollback()  # Rollback any partial action mutations
                self._log_failed_execution(email, workflow, str(e), traceback.format_exc())

    def _evaluate_and_execute(self, email: Email, workflow: Workflow) -> None:
        """Evaluates rules and executes actions if matched."""
        if not self._evaluate_rules(email, workflow.trigger_conditions_json):
            return  # Email did not match the conditions

        logger.info(f"[WORKFLOW] Email {email.id} matched workflow '{workflow.name}'")
        
        # Execute Actions
        action_logs = self._execute_actions(email, workflow.actions_json, workflow_id=str(workflow.id))
        
        # Save Execution Audit Log
        exec_create = WorkflowExecutionCreate(
            workflow_id=workflow.id,
            email_id=email.id,
            status="success",
            execution_logs_json={"actions": action_logs}
        )
        self.execution_repo.create(exec_create)

    def _log_failed_execution(self, email: Email, workflow: Workflow, error_msg: str, stack: str) -> None:
        """Safe logging for failed executions."""
        try:
            exec_create = WorkflowExecutionCreate(
                workflow_id=workflow.id,
                email_id=email.id,
                status="failed",
                execution_logs_json={"error": error_msg, "stack": stack}
            )
            self.execution_repo.create(exec_create)
        except Exception as e:
            logger.error(f"[WORKFLOW] Critical error logging execution failure: {e}")
            self.db.rollback()

    # ---------------------------------------------------------
    # Rules Evaluator (Step 3)
    # ---------------------------------------------------------
    def _evaluate_rules(self, email: Email, conditions: Dict[str, Any]) -> bool:
        """
        Evaluates deterministic JSON rules recursively to support nested conditions.
        """
        if not conditions:
            return False
            
        operator = conditions.get("operator", "AND").upper()
        rules = conditions.get("rules", [])
        
        if not rules:
            return False

        results = []
        for rule in rules:
            if "rules" in rule: # Nested condition
                results.append(self._evaluate_rules(email, rule))
            else:
                field = rule.get("field")
                op = rule.get("operator")
                val = rule.get("value")
                results.append(self._evaluate_single_rule(email, field, op, val))

        if operator == "OR":
            return any(results)
        return all(results)

    def _evaluate_single_rule(self, email: Email, field: str, op: str, val: Any) -> bool:
        """Evaluates a single atomic condition."""
        email_val = None
        
        if field == "subject": email_val = email.subject
        elif field == "sender": email_val = email.sender_email
        elif field == "recipient": 
            recipients = (email.to_recipients or []) + (email.cc_recipients or []) + (email.bcc_recipients or [])
            # Assuming recipients might be dicts or strings depending on parser
            email_val = " ".join([r.get("email", r.get("address", "")) if isinstance(r, dict) else str(r) for r in recipients])
        elif field == "label" or field == "labels": email_val = " ".join(email.labels or [])
        elif field == "body": email_val = (email.body_text or "") + " " + (email.snippet or "")
        elif field == "category": email_val = email.retention_category or ""
        elif field == "has_attachment": return bool(email.has_attachments) == (str(val).lower() == 'true' or val is True)
        
        if email_val is None:
            email_val = ""
        
        if isinstance(email_val, list):
            email_val = " ".join(email_val)
            
        email_val = str(email_val).lower()
        val = str(val).lower() if val is not None else ""

        if op == "equals": return email_val == val
        elif op == "contains": return val in email_val
        elif op == "starts_with": return email_val.startswith(val)
        elif op == "ends_with": return email_val.endswith(val)
        
        return False

    # ---------------------------------------------------------
    # Actions Evaluator (Step 4)
    # ---------------------------------------------------------
    def _execute_actions(self, email: Email, actions: Dict[str, Any], workflow_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Executes safe, predefined actions. No external API calls.
        """
        action_list = actions.get("actions", [])
        if not action_list and "type" in actions:
            action_list = [actions]
                
        logs = []
        
        for action in action_list:
            a_type = action.get("type")
            a_val = action.get("value")
            
            if a_type == "add_label":
                labels = list(email.labels) if email.labels else []
                if a_val and a_val not in labels:
                    labels.append(a_val)
                    email.labels = labels
                    flag_modified(email, "labels")
                logs.append({"action": "add_label", "result": f"Added '{a_val}'"})
                
            elif a_type == "mark_important":
                labels = list(email.labels) if email.labels else []
                if "IMPORTANT" not in labels:
                    labels.append("IMPORTANT")
                    email.labels = labels
                    flag_modified(email, "labels")
                logs.append({"action": "mark_important", "result": "Success"})
                
            elif a_type == "archive":
                email.record_status = "archived"
                logs.append({"action": "archive", "result": "Success"})

            elif a_type == "move_to_category":
                if a_val:
                    email.retention_category = a_val
                    logs.append({"action": "move_to_category", "result": f"Category set to '{a_val}'"})
                else:
                    logs.append({"action": "move_to_category", "result": "Failed: missing category value"})

            elif a_type == "generate_ai_reply":
                try:
                    from app.services.ai_service import AIService
                    from app.models.prompt_template import PromptTemplate
                    from app.models.ai_approval import AIApproval
                    
                    ai_service = AIService(db=self.db)
                    prompt_template_id = action.get("prompt_template_id")
                    require_approval = action.get("require_approval", True)
                    
                    prompt_str = "Draft a polite and helpful response to the following customer email:\nSubject: {{email_subject}}\nFrom: {{email_sender}}\n\n{{email_body}}"
                    if prompt_template_id:
                        pt = self.db.query(PromptTemplate).filter(PromptTemplate.id == prompt_template_id).first()
                        if pt and pt.prompt_content:
                            prompt_str = pt.prompt_content
                            pt.usage_count = (pt.usage_count or 0) + 1
                            
                    context = {
                        "email_sender": email.sender_email or "",
                        "email_subject": email.subject or "",
                        "email_body": email.body_text or email.snippet or ""
                    }
                    rendered_prompt = ai_service.render_prompt(prompt_str, context)
                    generated_reply = ai_service.generate_reply(rendered_prompt)
                    
                    if require_approval:
                        approval = AIApproval(
                            workflow_id=workflow_id,
                            email_id=email.id,
                            prompt_template_id=prompt_template_id,
                            generated_content=generated_reply,
                            status="pending_review"
                        )
                        self.db.add(approval)
                        self.db.flush()
                        logs.append({"action": "generate_ai_reply", "result": f"Generated AI Draft queued for approval (ID: {approval.id})"})
                    else:
                        logs.append({"action": "generate_ai_reply", "result": f"Generated AI Draft (Auto-send disabled without review)"})
                except Exception as ai_err:
                    logger.error(f"[WORKFLOW] Failed AI reply action: {ai_err}")
                    logs.append({"action": "generate_ai_reply", "result": f"Failed: {ai_err}"})

            elif a_type == "log_execution":
                logs.append({"action": "log_execution", "result": a_val or "Logged via Workflow"})
                
            else:
                logs.append({"action": a_type, "result": "Skipped unknown action"})
                
        return logs
