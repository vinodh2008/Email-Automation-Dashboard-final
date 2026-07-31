from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings
import logging

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

logger.info("Database engine initialized successfully")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def ensure_full_schema():
    conn = engine.connect()
    trans = conn.begin()
    try:
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto";'))

        # 1. user_roles & users
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_roles (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(50) UNIQUE NOT NULL,
                permissions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                role_id UUID NOT NULL REFERENCES user_roles(id) ON DELETE RESTRICT,
                email VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL DEFAULT 'User',
                hashed_password VARCHAR(255) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT true,
                last_login TIMESTAMPTZ NULL,
                is_deleted BOOLEAN NOT NULL DEFAULT false,
                deleted_at TIMESTAMPTZ NULL,
                deleted_by UUID NULL,
                version INT NOT NULL DEFAULT 1,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """))

        # 2. mailbox_accounts
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mailbox_accounts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                provider VARCHAR NOT NULL DEFAULT 'gmail',
                account_identifier VARCHAR NOT NULL,
                auth_mode VARCHAR NOT NULL DEFAULT 'desktop_oauth',
                last_history_id VARCHAR NULL,
                last_sync_at TIMESTAMPTZ NULL,
                sync_status VARCHAR NOT NULL DEFAULT 'connected',
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """))
        conn.execute(text("ALTER TABLE mailbox_accounts ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;"))
        conn.execute(text("ALTER TABLE mailbox_accounts ADD COLUMN IF NOT EXISTS sync_lock_token VARCHAR NULL;"))
        conn.execute(text("ALTER TABLE mailbox_accounts ADD COLUMN IF NOT EXISTS sync_locked_at TIMESTAMPTZ NULL;"))
        conn.execute(text("ALTER TABLE mailbox_accounts ADD COLUMN IF NOT EXISTS sync_lock_expires_at TIMESTAMPTZ NULL;"))
        conn.execute(text("ALTER TABLE mailbox_accounts ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;"))

        # 3. workflows & workflow_executions
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS workflows (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                mailbox_account_id UUID NOT NULL REFERENCES mailbox_accounts(id) ON DELETE CASCADE,
                name VARCHAR(150) NOT NULL,
                description VARCHAR NULL,
                trigger_conditions_json JSONB NOT NULL,
                actions_json JSONB NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS workflow_executions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
                email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
                status VARCHAR(20) NOT NULL,
                execution_logs_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                executed_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """))

        # 4. templates & system_settings
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS templates (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NULL REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS system_settings (
                key VARCHAR(100) PRIMARY KEY,
                value_json JSONB NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """))

        # 5. indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_workflows_mailbox_id ON workflows(mailbox_account_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_workflow_executions_workflow_id ON workflow_executions(workflow_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_workflow_executions_email_id ON workflow_executions(email_id);"))

        # 6. prompt_templates
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS prompt_templates (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NULL REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(150) NOT NULL,
                purpose VARCHAR(255) NULL,
                description TEXT NULL,
                prompt_content TEXT NOT NULL,
                variables_json TEXT NULL DEFAULT '[]',
                status VARCHAR(30) NOT NULL DEFAULT 'draft',
                usage_count INT NOT NULL DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_prompt_templates_user_id ON prompt_templates(user_id);"))

        # 7. ai_approvals
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_approvals (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
                email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
                prompt_template_id UUID NULL REFERENCES prompt_templates(id) ON DELETE SET NULL,
                generated_content TEXT NOT NULL,
                edited_content TEXT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'pending_review',
                reviewed_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
                reviewed_at TIMESTAMPTZ NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ai_approvals_workflow_id ON ai_approvals(workflow_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ai_approvals_email_id ON ai_approvals(email_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ai_approvals_status ON ai_approvals(status);"))

        # 8. ai_providers
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_providers (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NULL REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(150) NOT NULL,
                provider_type VARCHAR(50) NOT NULL,
                model VARCHAR(150) NOT NULL,
                api_key_encrypted TEXT NULL,
                base_url VARCHAR(500) NULL,
                is_enabled BOOLEAN NOT NULL DEFAULT true,
                is_primary BOOLEAN NOT NULL DEFAULT false,
                priority INT NOT NULL DEFAULT 0,
                max_tokens INT NULL DEFAULT 800,
                temperature DOUBLE PRECISION NULL DEFAULT 0.7,
                status VARCHAR(30) NOT NULL DEFAULT 'inactive',
                last_tested_at TIMESTAMPTZ NULL,
                last_error TEXT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ai_providers_user_id ON ai_providers(user_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ai_providers_provider_type ON ai_providers(provider_type);"))
        conn.execute(text("ALTER TABLE ai_providers ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;"))

        # 9. email_templates
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS email_templates (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NULL REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                subject VARCHAR(500) NULL,
                body_html TEXT NOT NULL,
                body_text TEXT NULL,
                category VARCHAR(100) NULL,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_email_templates_user_id ON email_templates(user_id);"))

        # 10. system_logs
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                level VARCHAR(20) NOT NULL,
                category VARCHAR(50) NOT NULL,
                message TEXT NOT NULL,
                details JSONB NULL,
                user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_system_logs_level ON system_logs(level);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_system_logs_category ON system_logs(category);"))

        # 11. Enterprise Admin Console: ai_providers monitoring columns
        conn.execute(text("ALTER TABLE ai_providers ADD COLUMN IF NOT EXISTS total_requests INT NOT NULL DEFAULT 0;"))
        conn.execute(text("ALTER TABLE ai_providers ADD COLUMN IF NOT EXISTS successful_requests INT NOT NULL DEFAULT 0;"))
        conn.execute(text("ALTER TABLE ai_providers ADD COLUMN IF NOT EXISTS failed_requests INT NOT NULL DEFAULT 0;"))
        conn.execute(text("ALTER TABLE ai_providers ADD COLUMN IF NOT EXISTS total_tokens_used BIGINT NOT NULL DEFAULT 0;"))
        conn.execute(text("ALTER TABLE ai_providers ADD COLUMN IF NOT EXISTS avg_latency_ms INT NULL;"))
        conn.execute(text("ALTER TABLE ai_providers ADD COLUMN IF NOT EXISTS health_score FLOAT NULL DEFAULT 100.0;"))

        # 12. Enterprise Admin Console: system_settings metadata columns
        conn.execute(text("ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS description VARCHAR(500) NULL;"))
        conn.execute(text("ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS category VARCHAR(50) NULL DEFAULT 'general';"))
        conn.execute(text("ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS updated_by UUID NULL;"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_system_settings_category ON system_settings(category);"))

        # 13. Enterprise Admin Console: admin_audit_log table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS admin_audit_log (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                user_email VARCHAR(255),
                action VARCHAR(100) NOT NULL,
                entity_type VARCHAR(50) NOT NULL,
                entity_id VARCHAR(100),
                old_value JSONB,
                new_value JSONB,
                ip_address VARCHAR(45),
                user_agent VARCHAR(500),
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_admin_audit_log_user_id ON admin_audit_log(user_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_admin_audit_log_created_at ON admin_audit_log(created_at DESC);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_admin_audit_log_entity_type ON admin_audit_log(entity_type);"))

        # 14. Sprint 6 Phase 2A: Business Categories (created first, no FK to prompt templates)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS business_categories (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(150) NOT NULL UNIQUE,
                code VARCHAR(50) NOT NULL UNIQUE,
                description TEXT NULL,
                priority INT NOT NULL DEFAULT 0,
                display_order INT NOT NULL DEFAULT 0,
                color VARCHAR(7) NULL DEFAULT '#6366F1',
                icon VARCHAR(50) NULL,
                owner_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'active',
                default_prompt_template_id UUID NULL,
                default_workflow_id UUID NULL REFERENCES workflows(id) ON DELETE SET NULL,
                is_default BOOLEAN NOT NULL DEFAULT false,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
                updated_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                ai_model VARCHAR(150) NULL,
                ai_temperature FLOAT NULL,
                ai_max_tokens INT NULL,
                ai_timeout INT NULL,
                ai_retry_count INT NULL,
                matching_strategy VARCHAR(50) NULL,
                confidence_threshold FLOAT NULL,
                knowledge_source_id UUID NULL,
                validation_policy_id UUID NULL,
                rule_set_id UUID NULL,
                decision_engine_id UUID NULL,
                approval_flow_id UUID NULL
            );
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_business_categories_code ON business_categories(code);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_business_categories_priority ON business_categories(priority);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_business_categories_display_order ON business_categories(display_order);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_business_categories_status ON business_categories(status);"))

        # 14b. Business Category Metrics (separate from configuration)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS business_category_metrics (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                business_category_id UUID NOT NULL UNIQUE REFERENCES business_categories(id) ON DELETE CASCADE,
                emails_processed INT NOT NULL DEFAULT 0,
                drafts_generated INT NOT NULL DEFAULT 0,
                approval_rate FLOAT NULL,
                avg_generation_time_ms INT NULL,
                avg_tokens_used INT NULL,
                last_used_at TIMESTAMPTZ NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """))

        # 15. Sprint 6 Phase 2A: Business Prompt Templates
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS business_prompt_templates (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                business_category_id UUID NULL,
                name VARCHAR(150) NOT NULL,
                purpose VARCHAR(255) NULL,
                description TEXT NULL,
                prompt_content TEXT NOT NULL,
                variables_json TEXT NULL DEFAULT '[]',
                current_version INT NOT NULL DEFAULT 1,
                published_version INT NULL,
                testing_status VARCHAR(30) NOT NULL DEFAULT 'untested',
                status VARCHAR(30) NOT NULL DEFAULT 'draft',
                usage_count INT NOT NULL DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
                updated_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bpt_category ON business_prompt_templates(business_category_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bpt_status ON business_prompt_templates(status);"))

        # 15b. Add FK constraints after both tables exist (use savepoints to handle already-existing)
        try:
            conn.execute(text("SAVEPOINT sp_fk1"))
            conn.execute(text("ALTER TABLE business_prompt_templates ADD CONSTRAINT fk_bpt_category FOREIGN KEY (business_category_id) REFERENCES business_categories(id) ON DELETE SET NULL;"))
            conn.execute(text("RELEASE SAVEPOINT sp_fk1"))
        except Exception:
            conn.execute(text("ROLLBACK TO SAVEPOINT sp_fk1"))
        try:
            conn.execute(text("SAVEPOINT sp_fk2"))
            conn.execute(text("ALTER TABLE business_categories ADD CONSTRAINT fk_bc_default_prompt FOREIGN KEY (default_prompt_template_id) REFERENCES business_prompt_templates(id) ON DELETE SET NULL;"))
            conn.execute(text("RELEASE SAVEPOINT sp_fk2"))
        except Exception:
            conn.execute(text("ROLLBACK TO SAVEPOINT sp_fk2"))

        # 16. Sprint 6 Phase 2A: Prompt Template Versions
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS prompt_template_versions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                base_template_id UUID NOT NULL REFERENCES business_prompt_templates(id) ON DELETE CASCADE,
                version_number INT NOT NULL,
                name VARCHAR(150) NOT NULL,
                purpose VARCHAR(255) NULL,
                description TEXT NULL,
                prompt_content TEXT NOT NULL,
                variables_json TEXT NULL DEFAULT '[]',
                status VARCHAR(30) NOT NULL DEFAULT 'draft',
                change_summary TEXT NULL,
                sandbox_result JSONB NULL,
                published_at TIMESTAMPTZ NULL,
                published_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
                archived_at TIMESTAMPTZ NULL,
                archived_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
                rollback_from_version INT NULL,
                created_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE(base_template_id, version_number)
            );
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ptv_base_template ON prompt_template_versions(base_template_id);"))

        # 17. Sprint 6 Phase 2A: Prompt Variables
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS prompt_variables (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(100) NOT NULL UNIQUE,
                display_name VARCHAR(150) NOT NULL,
                description TEXT NULL,
                data_type VARCHAR(30) NOT NULL DEFAULT 'STRING',
                scope VARCHAR(30) NOT NULL DEFAULT 'GLOBAL',
                source_adapter VARCHAR(50) NOT NULL DEFAULT 'ManualAdapter',
                source_config JSONB NULL,
                default_value TEXT NULL,
                is_required BOOLEAN NOT NULL DEFAULT false,
                validation_regex TEXT NULL,
                sample_value TEXT NULL,
                category VARCHAR(50) NULL DEFAULT 'email',
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_pv_scope ON prompt_variables(scope);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_pv_source_adapter ON prompt_variables(source_adapter);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_pv_category ON prompt_variables(category);"))

        # 18. Sprint 6 Phase 2A: Category-Workflow Mappings
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS category_workflow_mappings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                business_category_id UUID NOT NULL REFERENCES business_categories(id) ON DELETE CASCADE,
                workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
                priority INT NOT NULL DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE(business_category_id, workflow_id)
            );
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cwm_category ON category_workflow_mappings(business_category_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cwm_workflow ON category_workflow_mappings(workflow_id);"))

        # 19. Sprint 6 Phase 2A: Prompt Sandbox Sessions
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS prompt_sandbox_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                template_id UUID NULL REFERENCES business_prompt_templates(id) ON DELETE SET NULL,
                template_version INT NULL,
                variable_values JSONB NOT NULL DEFAULT '{}',
                variables_snapshot JSONB NULL,
                rendered_prompt TEXT NULL,
                validation_result JSONB NULL,
                variables_used JSONB NULL,
                variables_missing JSONB NULL,
                variables_unknown JSONB NULL,
                prompt_length_chars INT NULL,
                estimated_tokens INT NULL,
                warnings JSONB NULL DEFAULT '[]',
                status VARCHAR(30) NOT NULL DEFAULT 'pending',
                created_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_pss_template ON prompt_sandbox_sessions(template_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_pss_created_by ON prompt_sandbox_sessions(created_by);"))

        # 20. Sprint 6 Phase 2A: Add business_category_id to workflows
        conn.execute(text("ALTER TABLE workflows ADD COLUMN IF NOT EXISTS business_category_id UUID REFERENCES business_categories(id) ON DELETE SET NULL;"))

        # Phase 2B: Task Queue
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS task_queue (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                queue_name VARCHAR(50) NOT NULL,
                task_type VARCHAR(50) NOT NULL,
                entity_type VARCHAR(50) NOT NULL,
                entity_id UUID NOT NULL,
                payload JSONB NOT NULL DEFAULT '{}',
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                priority INT NOT NULL DEFAULT 5,
                retry_count INT NOT NULL DEFAULT 0,
                max_retries INT NOT NULL DEFAULT 3,
                scheduled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                started_at TIMESTAMPTZ,
                completed_at TIMESTAMPTZ,
                error_message TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tq_status_priority ON task_queue(status, priority DESC, scheduled_at);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tq_queue_name ON task_queue(queue_name, status);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tq_entity ON task_queue(entity_type, entity_id);"))

        # Phase 2B: AI Tasks
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_tasks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                business_category_id UUID NOT NULL REFERENCES business_categories(id) ON DELETE CASCADE,
                task_type VARCHAR(30) NOT NULL,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                prompt_template_id UUID REFERENCES business_prompt_templates(id) ON DELETE SET NULL,
                model_override VARCHAR(150),
                temperature_override FLOAT,
                max_tokens_override INT,
                is_enabled BOOLEAN NOT NULL DEFAULT true,
                execution_order INT NOT NULL DEFAULT 0,
                config JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE(business_category_id, task_type)
            );
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_at_category ON ai_tasks(business_category_id);"))

        # Phase 2B: Category Channel Configs
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS category_channel_configs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                business_category_id UUID NOT NULL REFERENCES business_categories(id) ON DELETE CASCADE,
                channel VARCHAR(30) NOT NULL,
                is_enabled BOOLEAN NOT NULL DEFAULT false,
                workflow_id UUID REFERENCES workflows(id) ON DELETE SET NULL,
                prompt_template_id UUID REFERENCES business_prompt_templates(id) ON DELETE SET NULL,
                channel_config JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE(business_category_id, channel)
            );
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ccc_category ON category_channel_configs(business_category_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ccc_channel ON category_channel_configs(channel);"))

        # Phase 2B: Knowledge Sources
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS knowledge_sources (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                business_category_id UUID NOT NULL REFERENCES business_categories(id) ON DELETE CASCADE,
                name VARCHAR(150) NOT NULL,
                description TEXT,
                source_type VARCHAR(30) NOT NULL,
                file_path TEXT,
                file_size_bytes INT,
                mime_type VARCHAR(100),
                content_text TEXT,
                embedding_status VARCHAR(20) DEFAULT 'pending',
                embedding_model VARCHAR(50),
                chunk_count INT DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_by UUID REFERENCES users(id) ON DELETE SET NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ks_category ON knowledge_sources(business_category_id);"))

        # Phase 2B: Decision Rules
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS decision_rules (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                business_category_id UUID NOT NULL REFERENCES business_categories(id) ON DELETE CASCADE,
                name VARCHAR(150) NOT NULL,
                description TEXT,
                is_enabled BOOLEAN NOT NULL DEFAULT true,
                priority INT NOT NULL DEFAULT 0,
                min_confidence FLOAT DEFAULT 0.9,
                max_risk_level VARCHAR(20) DEFAULT 'low',
                max_email_value FLOAT,
                sender_whitelist JSONB DEFAULT '[]',
                category_codes JSONB DEFAULT '[]',
                action VARCHAR(30) NOT NULL DEFAULT 'escalate',
                approval_chain JSONB DEFAULT '[]',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_dr_category ON decision_rules(business_category_id);"))

        # Phase 2B: Email Classifications
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS email_classifications (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
                business_category_id UUID NOT NULL REFERENCES business_categories(id) ON DELETE SET NULL,
                confidence FLOAT NOT NULL,
                matching_method VARCHAR(30) NOT NULL,
                matching_details JSONB DEFAULT '{}',
                classified_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                classified_by VARCHAR(30) NOT NULL DEFAULT 'system'
            );
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ec_email ON email_classifications(email_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ec_category ON email_classifications(business_category_id);"))

        # Phase 2B: Email Sends
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS email_sends (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
                ai_approval_id UUID REFERENCES ai_approvals(id) ON DELETE SET NULL,
                gmail_message_id VARCHAR(100),
                thread_id VARCHAR(100),
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                sent_at TIMESTAMPTZ,
                error_message TEXT,
                retry_count INT DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_es_email ON email_sends(email_id);"))

        # Phase 2B: Extend emails table
        conn.execute(text("ALTER TABLE emails ADD COLUMN IF NOT EXISTS business_category_id UUID REFERENCES business_categories(id);"))
        conn.execute(text("ALTER TABLE emails ADD COLUMN IF NOT EXISTS classification_confidence FLOAT;"))
        conn.execute(text("ALTER TABLE emails ADD COLUMN IF NOT EXISTS ai_draft_status VARCHAR(20) DEFAULT 'none';"))
        conn.execute(text("ALTER TABLE emails ADD COLUMN IF NOT EXISTS ai_draft_content TEXT;"))
        conn.execute(text("ALTER TABLE emails ADD COLUMN IF NOT EXISTS summary TEXT;"))
        conn.execute(text("ALTER TABLE emails ADD COLUMN IF NOT EXISTS extracted_entities JSONB;"))

        # Phase 2B: Extend ai_approvals
        conn.execute(text("ALTER TABLE ai_approvals ADD COLUMN IF NOT EXISTS auto_approved BOOLEAN DEFAULT false;"))
        conn.execute(text("ALTER TABLE ai_approvals ADD COLUMN IF NOT EXISTS confidence_score FLOAT;"))
        conn.execute(text("ALTER TABLE ai_approvals ADD COLUMN IF NOT EXISTS decision_rule_id UUID REFERENCES decision_rules(id);"))
        conn.execute(text("ALTER TABLE ai_approvals ADD COLUMN IF NOT EXISTS knowledge_context_used JSONB;"))
        conn.execute(text("ALTER TABLE ai_approvals ADD COLUMN IF NOT EXISTS ai_task_id UUID REFERENCES ai_tasks(id);"))

        # Phase 2B: Extend business_categories
        conn.execute(text("ALTER TABLE business_categories ADD COLUMN IF NOT EXISTS risk_level VARCHAR(20) DEFAULT 'medium';"))
        conn.execute(text("ALTER TABLE business_categories ADD COLUMN IF NOT EXISTS default_auto_approve BOOLEAN DEFAULT false;"))

        # 21-26. Seed default settings (parameterized, no SQL injection)
        seed_data = [
            ("company_settings", '{"company_name":"My Company","support_email":"","default_signature":"Best regards,","default_language":"en","timezone":"UTC","business_hours":{"monday":{"enabled":true,"start":"09:00","end":"17:00"},"tuesday":{"enabled":true,"start":"09:00","end":"17:00"},"wednesday":{"enabled":true,"start":"09:00","end":"17:00"},"thursday":{"enabled":true,"start":"09:00","end":"17:00"},"friday":{"enabled":true,"start":"09:00","end":"17:00"}},"branding":{"logo_url":"","primary_color":"#4F46E5"}}', "Company profile, branding, and business hours", "company"),
            ("ai_defaults", '{"default_tone":"professional","creativity_level":0.7,"response_length":"medium","default_language":"en","require_human_approval":true,"max_retry_count":3,"max_tokens":4000,"default_model":"","fallback_enabled":true}', "Global AI behavior defaults for all workflows", "ai"),
            ("feature_flags", '{"email_summarization":false,"draft_reply_generation":false,"rag_enabled":false,"business_rules_engine":false,"email_sending":false,"auto_approval":false,"advanced_analytics":false,"multi_language_support":false}', "Platform feature toggles", "features"),
            ("notification_settings", '{"provider_failure_alerts":true,"sync_error_alerts":true,"approval_reminders":true,"daily_digest":false,"digest_email":""}', "System notification preferences", "notifications"),
        ]
        for key, json_val, desc, cat in seed_data:
            conn.execute(
                text("INSERT INTO system_settings (key, value_json, description, category) "
                     "SELECT :key, CAST(:json_val AS jsonb), :desc, :cat "
                     "WHERE NOT EXISTS (SELECT 1 FROM system_settings WHERE key = :key)"),
                {"key": key, "json_val": json_val, "desc": desc, "cat": cat}
            )

        # 27. Seed default prompt variables
        default_variables = [
            ("customer_name", "Customer Name", "STRING", "GLOBAL", "EmailAdapter", "customer", "true", "John Doe"),
            ("email_sender", "Sender Email", "EMAIL", "GLOBAL", "EmailAdapter", "email", "true", "john@example.com"),
            ("email_subject", "Email Subject", "STRING", "GLOBAL", "EmailAdapter", "email", "true", "Refund Request"),
            ("email_body", "Email Body", "LONG_TEXT", "GLOBAL", "EmailAdapter", "email", "true", "I would like a refund..."),
            ("company_name", "Company Name", "STRING", "GLOBAL", "CompanyAdapter", "company", "true", "Utservio"),
            ("support_email", "Support Email", "EMAIL", "GLOBAL", "CompanyAdapter", "company", "false", "support@utservio.com"),
            ("current_date", "Current Date", "DATE", "GLOBAL", "StaticAdapter", "system", "false", "2026-07-30"),
        ]
        for name, display, dtype, scope, adapter, cat, req, sample in default_variables:
            conn.execute(
                text("INSERT INTO prompt_variables (name, display_name, data_type, scope, source_adapter, category, is_required, sample_value) "
                     "SELECT :name, :display, :dtype, :scope, :adapter, :cat, :req, :sample "
                     "WHERE NOT EXISTS (SELECT 1 FROM prompt_variables WHERE name = :name)"),
                {"name": name, "display": display, "dtype": dtype, "scope": scope, "adapter": adapter, "cat": cat, "req": req, "sample": sample}
            )

        # 28. Seed default business category
        conn.execute(
            text("INSERT INTO business_categories (name, code, description, priority, display_order, is_default, status) "
                 "SELECT 'General Inquiries', 'GENERAL', 'Default category for unmatched emails', 999, 999, true, 'active' "
                 "WHERE NOT EXISTS (SELECT 1 FROM business_categories WHERE code = 'GENERAL')")
        )

        trans.commit()
        logger.info("Database full schema verification complete.")
    except Exception as e:
        try:
            trans.rollback()
        except Exception:
            pass
        logger.warning(f"Database schema auto-check notice: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
