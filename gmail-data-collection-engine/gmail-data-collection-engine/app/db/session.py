from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings
import logging

# Configure module logger
logger = logging.getLogger(__name__)

# Create PostgreSQL engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Log runtime DB connection (never log credentials)
logger.info("Database engine initialized successfully")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def ensure_full_schema():
    try:
        with engine.begin() as conn:
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

            logger.info("Database full schema verification complete.")
    except Exception as e:
        logger.warning(f"Database schema auto-check notice: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
