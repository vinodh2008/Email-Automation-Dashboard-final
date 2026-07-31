from fastapi import APIRouter
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.health import router as health_router
from app.api.v1.workflows import router as workflows_router
from app.api.v1.automation import router as automation_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.auth import router as auth_router
from app.api.v1.system_monitoring import router as system_monitoring_router
from app.api.v1.events import router as events_router
from app.api.v1.prompt_templates import router as prompt_templates_router
from app.api.v1.ai_approvals import router as ai_approvals_router
from app.api.v1.ai_providers import router as ai_providers_router
from app.api.v1.email_templates import router as email_templates_router
from app.api.v1.logs import router as logs_router
from app.api.v1.users import router as users_router
from app.api.v1.roles import router as roles_router
from app.api.v1.company_settings import router as company_settings_router
from app.api.v1.ai_defaults import router as ai_defaults_router
from app.api.v1.feature_flags import router as feature_flags_router
from app.api.v1.audit_log import router as audit_log_router
from app.api.v1.notification_settings import router as notification_settings_router
from app.api.v1.business_categories import router as business_categories_router
from app.api.v1.business_prompts import router as business_prompts_router
from app.api.v1.prompt_variables import router as prompt_variables_router
from app.api.v1.category_workflow_mappings import router as category_workflow_mappings_router
from app.api.v1.prompt_sandbox import router as prompt_sandbox_router
from app.api.v1.prompt_builder import router as prompt_builder_router
from app.api.v1.task_queue import router as task_queue_router
from app.api.v1.ai_tasks import router as ai_tasks_router
from app.api.v1.category_channels import router as category_channels_router
from app.api.v1.knowledge_sources import router as knowledge_sources_router
from app.api.v1.decision_rules import router as decision_rules_router
from app.api.v1.email_classifications import router as email_classifications_router
from app.api.v1.email_sends import router as email_sends_router
from app.api.v1.category_pipeline import router as category_pipeline_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(dashboard_router)
api_v1_router.include_router(health_router)
api_v1_router.include_router(workflows_router)
api_v1_router.include_router(automation_router)
api_v1_router.include_router(notifications_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(system_monitoring_router)
api_v1_router.include_router(events_router)
api_v1_router.include_router(prompt_templates_router)
api_v1_router.include_router(ai_approvals_router)
api_v1_router.include_router(ai_providers_router)
api_v1_router.include_router(email_templates_router)
api_v1_router.include_router(logs_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(roles_router)
api_v1_router.include_router(company_settings_router)
api_v1_router.include_router(ai_defaults_router)
api_v1_router.include_router(feature_flags_router)
api_v1_router.include_router(audit_log_router)
api_v1_router.include_router(notification_settings_router)
api_v1_router.include_router(business_categories_router)
api_v1_router.include_router(business_prompts_router)
api_v1_router.include_router(prompt_variables_router)
api_v1_router.include_router(category_workflow_mappings_router)
api_v1_router.include_router(prompt_sandbox_router)
api_v1_router.include_router(prompt_builder_router)
api_v1_router.include_router(task_queue_router)
api_v1_router.include_router(ai_tasks_router)
api_v1_router.include_router(category_channels_router)
api_v1_router.include_router(knowledge_sources_router)
api_v1_router.include_router(decision_rules_router)
api_v1_router.include_router(email_classifications_router)
api_v1_router.include_router(email_sends_router)
api_v1_router.include_router(category_pipeline_router)
