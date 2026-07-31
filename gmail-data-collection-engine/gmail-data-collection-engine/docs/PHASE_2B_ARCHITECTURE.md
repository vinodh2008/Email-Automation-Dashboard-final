# Utservio Phase 2B — Consolidated Architecture

## Executive Summary

Phase 2B transforms Utservio from a "collect emails + manual approval" system into an **automated email response pipeline**. The core flow becomes:

```
Email → CategoryMatcher → Workflow → AI Tasks → Decision → Approval → Send
```

All processing is async via a database task queue. Categories are channel-agnostic. AI tasks are first-class database entities.

---

## 1. RUNTIME FLOW (Single Path)

```
┌─────────────────────────────────────────────────────────────────┐
│                        SYNC (Fast, Non-Blocking)                │
│                                                                 │
│  Gmail API → SyncOrchestrator → Save Email → Enqueue Event      │
│                                              ↓                  │
│                                    task_queue (pending)         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    BACKGROUND WORKER (APScheduler)               │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ STEP 1: VALIDATION                                       │   │
│  │ ValidationService.validate(email)                        │   │
│  │ → Check: format, sender legitimacy, spam score           │   │
│  │ → If score < 50: reject, log, stop                       │   │
│  │ → If score >= 50: continue                               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ STEP 2: CATEGORY MATCHING                                │   │
│  │ CategoryMatcher.classify(email)                           │   │
│  │ → Scan active categories by priority                     │   │
│  │ → Match by: rules, keyword, sender domain                │   │
│  │ → Assign best-match category (e.g., "REFUND")            │   │
│  │ → If no match: assign default category or escalate       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ STEP 3: WORKFLOW EXECUTION                               │   │
│  │ WorkflowExecutor.execute(email, category)                 │   │
│  │ → Load workflows linked to this category                 │   │
│  │ → Evaluate trigger rules (AND/OR engine)                 │   │
│  │ → If rules match: execute action pipeline                │   │
│  │ → Actions: label, archive, categorize, AI tasks          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ STEP 4: AI TASK EXECUTION                                │   │
│  │ AITaskService.execute(email, category, tasks)             │   │
│  │ → For each task in execution_order:                      │   │
│  │   ├─ classify: assign category (already done)            │   │
│  │   ├─ summarize: condense email thread                    │   │
│  │   ├─ extract: pull entities (order #, dates, amounts)    │   │
│  │   ├─ generate_reply: draft response                      │   │
│  │   └─ route: suggest department                           │   │
│  │ → Fetch knowledge context from knowledge_source          │   │
│  │ → Call AI provider (with failover)                       │   │
│  │ → Store AI output                                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ STEP 5: DECISION                                         │   │
│  │ DecisionService.decide(email, ai_output, category)       │   │
│  │ → Load decision rules for category                       │   │
│  │ → Evaluate: confidence, risk level, email value          │   │
│  │ → If auto-approve: skip approval, go to send             │   │
│  │ → If escalate: create approval record, notify admin      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ STEP 6: APPROVAL (if escalation needed)                  │   │
│  │ ApprovalService.create(email, ai_output)                 │   │
│  │ → Create AIApproval record (pending_review)              │   │
│  │ → Notify admin via SSE                                   │   │
│  │ → Admin reviews, edits, approves/rejects                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ STEP 7: EMAIL SENDING                                    │   │
│  │ EmailSenderService.send(approved_draft)                  │   │
│  │ → Call Gmail API to send reply                           │   │
│  │ → Log sent event                                         │   │
│  │ → Update email status                                    │   │
│  │ → Broadcast SSE event                                    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. DATABASE SCHEMA CHANGES

### 2.1 New Tables

#### A. Task Queue (Async Processing)
```sql
CREATE TABLE task_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    queue_name VARCHAR(50) NOT NULL,          -- 'email_processing', 'ai_generation', 'email_sending'
    task_type VARCHAR(50) NOT NULL,           -- 'validate', 'classify', 'generate_reply', 'send'
    entity_type VARCHAR(50) NOT NULL,         -- 'email', 'approval'
    entity_id UUID NOT NULL,                  -- email_id, approval_id
    payload JSONB NOT NULL DEFAULT '{}',      -- full context to avoid re-fetching
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed, dead_letter
    priority INT NOT NULL DEFAULT 5,          -- 1-10 (higher = process first)
    retry_count INT NOT NULL DEFAULT 0,
    max_retries INT NOT NULL DEFAULT 3,
    scheduled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_tq_status_priority ON task_queue(status, priority DESC, scheduled_at);
CREATE INDEX ix_tq_queue_name ON task_queue(queue_name, status);
CREATE INDEX ix_tq_entity ON task_queue(entity_type, entity_id);
```

#### B. AI Tasks (Per-Category AI Configuration)
```sql
CREATE TABLE ai_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_category_id UUID NOT NULL REFERENCES business_categories(id) ON DELETE CASCADE,
    task_type VARCHAR(30) NOT NULL,           -- 'classify', 'summarize', 'extract', 'generate_reply', 'route'
    name VARCHAR(100) NOT NULL,
    description TEXT,
    prompt_template_id UUID REFERENCES business_prompt_templates(id) ON DELETE SET NULL,
    model_override VARCHAR(150),              -- NULL = use category default
    temperature_override FLOAT,
    max_tokens_override INT,
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    execution_order INT NOT NULL DEFAULT 0,   -- lower = runs first
    config JSONB DEFAULT '{}',                -- task-specific config
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(business_category_id, task_type)
);

CREATE INDEX ix_at_category ON ai_tasks(business_category_id);
```

#### C. Category Channel Config (Channel-Specific Behavior)
```sql
CREATE TABLE category_channel_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_category_id UUID NOT NULL REFERENCES business_categories(id) ON DELETE CASCADE,
    channel VARCHAR(30) NOT NULL,             -- 'email', 'whatsapp', 'chat', 'voice'
    is_enabled BOOLEAN NOT NULL DEFAULT false,
    workflow_id UUID REFERENCES workflows(id) ON DELETE SET NULL,
    prompt_template_id UUID REFERENCES business_prompt_templates(id) ON DELETE SET NULL,
    channel_config JSONB DEFAULT '{}',        -- channel-specific settings
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(business_category_id, channel)
);

CREATE INDEX ix_ccc_category ON category_channel_configs(business_category_id);
CREATE INDEX ix_ccc_channel ON category_channel_configs(channel);
```

#### D. Knowledge Sources (Phase 2B skeleton, Phase 3 RAG)
```sql
CREATE TABLE knowledge_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_category_id UUID NOT NULL REFERENCES business_categories(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    source_type VARCHAR(30) NOT NULL,         -- 'pdf', 'faq', 'policy', 'manual', 'template'
    file_path TEXT,                           -- Supabase Storage path
    file_size_bytes INT,
    mime_type VARCHAR(100),
    content_text TEXT,                        -- extracted text content
    embedding_status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, ready, failed
    embedding_model VARCHAR(50),
    chunk_count INT DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_ks_category ON knowledge_sources(business_category_id);
```

#### E. Decision Rules (Auto-Approval Configuration)
```sql
CREATE TABLE decision_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_category_id UUID NOT NULL REFERENCES business_categories(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    priority INT NOT NULL DEFAULT 0,          -- higher = evaluated first
    
    -- Conditions (ALL must match for rule to apply)
    min_confidence FLOAT DEFAULT 0.9,         -- AI confidence threshold
    max_risk_level VARCHAR(20) DEFAULT 'low', -- low, medium, high
    max_email_value FLOAT,                    -- dollar amount threshold
    sender_whitelist JSONB DEFAULT '[]',      -- verified sender domains
    category_codes JSONB DEFAULT '[]',        -- which categories this applies to
    
    -- Actions
    action VARCHAR(30) NOT NULL DEFAULT 'escalate',  -- 'auto_approve', 'escalate', 'reject'
    approval_chain JSONB DEFAULT '[]',        -- for future multi-step
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_dr_category ON decision_rules(business_category_id);
```

#### F. Email Classification (Audit Trail)
```sql
CREATE TABLE email_classifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    business_category_id UUID NOT NULL REFERENCES business_categories(id) ON DELETE SET NULL,
    confidence FLOAT NOT NULL,
    matching_method VARCHAR(30) NOT NULL,     -- 'rule_based', 'keyword', 'ml', 'default'
    matching_details JSONB DEFAULT '{}',      -- which rules matched
    classified_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    classified_by VARCHAR(30) NOT NULL DEFAULT 'system'  -- 'system', 'admin'
);

CREATE INDEX ix_ec_email ON email_classifications(email_id);
CREATE INDEX ix_ec_category ON email_classifications(business_category_id);
```

#### G. Email Sending Log (Audit Trail)
```sql
CREATE TABLE email_sends (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    ai_approval_id UUID REFERENCES ai_approvals(id) ON DELETE SET NULL,
    gmail_message_id VARCHAR(100),
    thread_id VARCHAR(100),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, sent, failed
    sent_at TIMESTAMPTZ,
    error_message TEXT,
    retry_count INT DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_es_email ON email_sends(email_id);
```

### 2.2 Modified Tables

#### A. `emails` — Add classification tracking
```sql
ALTER TABLE emails ADD COLUMN IF NOT EXISTS business_category_id UUID REFERENCES business_categories(id);
ALTER TABLE emails ADD COLUMN IF NOT EXISTS classification_confidence FLOAT;
ALTER TABLE emails ADD COLUMN IF NOT EXISTS ai_draft_status VARCHAR(20) DEFAULT 'none';  -- none, pending, generated, approved, sent
ALTER TABLE emails ADD COLUMN IF NOT EXISTS ai_draft_content TEXT;
ALTER TABLE emails ADD COLUMN IF NOT EXISTS summary TEXT;
ALTER TABLE emails ADD COLUMN IF NOT EXISTS extracted_entities JSONB;
```

#### B. `ai_approvals` — Extend for decision service
```sql
ALTER TABLE ai_approvals ADD COLUMN IF NOT EXISTS auto_approved BOOLEAN DEFAULT false;
ALTER TABLE ai_approvals ADD COLUMN IF NOT EXISTS confidence_score FLOAT;
ALTER TABLE ai_approvals ADD COLUMN IF NOT EXISTS decision_rule_id UUID REFERENCES decision_rules(id);
ALTER TABLE ai_approvals ADD COLUMN IF NOT EXISTS knowledge_context_used JSONB;
ALTER TABLE ai_approvals ADD COLUMN IF NOT EXISTS ai_task_id UUID REFERENCES ai_tasks(id);
```

#### C. `business_categories` — Add risk level
```sql
ALTER TABLE business_categories ADD COLUMN IF NOT EXISTS risk_level VARCHAR(20) DEFAULT 'medium';  -- low, medium, high
ALTER TABLE business_categories ADD COLUMN IF NOT EXISTS default_auto_approve BOOLEAN DEFAULT false;
```

---

## 3. NEW SERVICES

### 3.1 TaskQueueService
**Purpose:** Manage async task queue (enqueue, dequeue, retry, dead-letter)

```python
class TaskQueueService:
    def enqueue(queue_name, task_type, entity_type, entity_id, payload, priority=5, delay=0)
    def dequeue(queue_name=None, limit=1) -> List[TaskQueueItem]
    def complete(task_id, result=None)
    def fail(task_id, error_message)
    def retry(task_id)
    def dead_letter(task_id)
    def get_stats() -> dict  # pending, processing, completed, failed counts
    def cleanup_completed(older_than_hours=24)
```

### 3.2 CategoryMatcherService
**Purpose:** Classify emails into business categories

```python
class CategoryMatcherService:
    def classify(email_id: str) -> ClassificationResult
        # 1. Load all active categories ordered by priority
        # 2. For each category, evaluate matching rules:
        #    - Subject keywords
        #    - Sender domain
        #    - Body content patterns
        #    - Labels
        # 3. Return best match with confidence score
        # 4. If no match: return default category or None
    
    def get_matching_rules(category_id: str) -> dict
    def update_matching_rules(category_id: str, rules: dict)
```

### 3.3 AITaskService
**Purpose:** Execute AI tasks (classify, summarize, generate_reply, extract, route)

```python
class AITaskService:
    def execute_task(task_id: str, email_id: str, context: dict) -> AITaskResult
        # 1. Load task definition from ai_tasks table
        # 2. Load prompt template (from task or category default)
        # 3. Resolve variables (email fields + context)
        # 4. Inject knowledge context (if knowledge_source exists)
        # 5. Call AI provider with failover
        # 6. Parse and validate output
        # 7. Store result
    
    def execute_task_chain(email_id: str, category_id: str) -> List[AITaskResult]
        # Execute all enabled tasks for category in execution_order
```

### 3.4 KnowledgeService
**Purpose:** Manage knowledge sources and retrieve context for prompts

```python
class KnowledgeService:
    def add_source(category_id, name, source_type, file_path=None, content_text=None)
    def remove_source(source_id)
    def get_sources(category_id) -> List[KnowledgeSource]
    def search_context(category_id, query, limit=3) -> List[str]
        # Phase 2B: simple text search
        # Phase 3: vector similarity search
    
    def index_source(source_id)  # extract text, create chunks
```

### 3.5 ValidationService
**Purpose:** Validate emails before processing

```python
class ValidationService:
    def validate(email_id: str) -> ValidationResult
        # 1. Check email format validity
        # 2. Check sender legitimacy (not bot, not bounce)
        # 3. Check spam score (basic: suspicious links, known spam patterns)
        # 4. Check required fields (subject, body not empty)
        # 5. Return score 0-100 + reasons
    
    def get_rules() -> dict  # configurable validation rules
```

### 3.6 DecisionService
**Purpose:** Decide auto-approve vs escalate to human

```python
class DecisionService:
    def decide(email_id, ai_output, category_id) -> Decision
        # 1. Load decision rules for category (ordered by priority)
        # 2. Evaluate each rule's conditions:
        #    - confidence >= min_confidence
        #    - risk_level <= max_risk_level
        #    - email_value <= max_email_value
        #    - sender in whitelist
        # 3. First matching rule wins
        # 4. Return: auto_approve, escalate, or reject
    
    def get_rules(category_id) -> List[DecisionRule]
    def create_rule(category_id, rule_data)
    def update_rule(rule_id, rule_data)
    def delete_rule(rule_id)
```

### 3.7 ApprovalService (Extend Existing)
**Purpose:** Manage approval workflow

```python
class ApprovalService:
    # Keep existing:
    def get_pending()
    def approve(approval_id, edited_text=None)
    def reject(approval_id)
    
    # Add:
    def create_from_ai_output(email_id, ai_output, category_id, confidence, auto_approved=False)
    def get_stats_by_category(category_id)
```

### 3.8 EmailSenderService
**Purpose:** Send approved email replies via Gmail API

```python
class EmailSenderService:
    def send_reply(approval_id: str) -> SendResult
        # 1. Load approval record
        # 2. Load original email (for thread_id, recipients)
        # 3. Call Gmail API: messages.send with reply
        # 4. Log to email_sends table
        # 5. Update email.ai_draft_status = 'sent'
        # 6. Broadcast SSE event
    
    def send_batch(approval_ids: List[str]) -> List[SendResult]
    def retry_send(send_id: str)
```

---

## 4. MODIFIED SERVICES

### 4.1 SyncOrchestrator (Make Async)
**Current:** Saves email → runs workflows inline (blocking)
**New:** Saves email → enqueues classification task → returns (non-blocking)

```python
# BEFORE (blocking)
class SyncOrchestrator:
    def run_sync(self):
        for email in new_emails:
            db.save(email)
            WorkflowExecutionService.process_email(email)  # BLOCKING

# AFTER (async)
class SyncOrchestrator:
    def run_sync(self):
        for email in new_emails:
            db.save(email)
            TaskQueueService.enqueue(
                queue_name="email_processing",
                task_type="classify",
                entity_type="email",
                entity_id=email.id,
                payload={"email_id": email.id}
            )
        # Returns immediately
```

### 4.2 WorkflowExecutionService (Integrate with Categories)
**Current:** Workflows execute actions directly
**New:** Workflows trigger AI tasks via the task queue

```python
# AFTER
class WorkflowExecutionService:
    def execute_workflow(workflow_id, email_id):
        # 1. Evaluate trigger rules
        # 2. Execute non-AI actions (label, archive, categorize)
        # 3. For AI actions: enqueue AI task
        TaskQueueService.enqueue(
            queue_name="ai_generation",
            task_type="generate_reply",
            entity_type="email",
            entity_id=email_id,
            payload={"workflow_id": workflow_id, "category_id": category_id}
        )
```

### 4.3 PromptBuilderService (Add Knowledge Injection)
**Current:** Renders template + variables
**New:** Also injects knowledge context

```python
# AFTER
class PromptBuilderService:
    def build(self, prompt_content, variable_values, knowledge_context=None):
        resolution = self.resolver.resolve(prompt_content, variable_values)
        
        # Inject knowledge if provided
        if knowledge_context:
            rendered = resolution['rendered_prompt']
            rendered += f"\n\n--- Knowledge Context ---\n{knowledge_context}"
            resolution['rendered_prompt'] = rendered
        
        return resolution
```

### 4.4 AIService (Integrate with AI Tasks)
**Current:** Directly called by workflow actions
**New:** Called by AITaskService with category-specific config

```python
# AFTER
class AIService:
    def generate_reply(self, prompt, category_config=None):
        # Use category-specific model/temperature if provided
        model = category_config.get('model') if category_config else None
        temperature = category_config.get('temperature') if category_config else None
        
        # Provider failover chain (existing logic)
        # ...
```

---

## 5. API ENDPOINTS

### 5.1 New Endpoints

#### Task Queue
```
GET  /api/v1/task-queue/stats              → Queue statistics
GET  /api/v1/task-queue/pending            → List pending tasks
POST /api/v1/task-queue/retry/{task_id}    → Retry failed task
DELETE /api/v1/task-queue/{task_id}        → Cancel task
```

#### AI Tasks
```
GET  /api/v1/ai-tasks?category_id=         → List tasks for category
POST /api/v1/ai-tasks                      → Create task
PUT  /api/v1/ai-tasks/{id}                 → Update task
DELETE /api/v1/ai-tasks/{id}               → Delete task
POST /api/v1/ai-tasks/{id}/test            → Test task with sample email
```

#### Category Channel Config
```
GET  /api/v1/category-channels?category_id=  → List channel configs
POST /api/v1/category-channels               → Create channel config
PUT  /api/v1/category-channels/{id}          → Update channel config
DELETE /api/v1/category-channels/{id}        → Delete channel config
```

#### Knowledge Sources
```
GET  /api/v1/knowledge-sources?category_id=  → List sources
POST /api/v1/knowledge-sources               → Upload/create source
GET  /api/v1/knowledge-sources/{id}          → Get source detail
DELETE /api/v1/knowledge-sources/{id}        → Delete source
POST /api/v1/knowledge-sources/{id}/index    → Trigger indexing
POST /api/v1/knowledge/search                → Search knowledge
```

#### Decision Rules
```
GET  /api/v1/decision-rules?category_id=    → List rules
POST /api/v1/decision-rules                 → Create rule
PUT  /api/v1/decision-rules/{id}            → Update rule
DELETE /api/v1/decision-rules/{id}          → Delete rule
POST /api/v1/decision-rules/test            → Test rule against sample
```

#### Email Classification
```
GET  /api/v1/email-classifications?email_id=  → Get classification
POST /api/v1/email-classifications/reclassify/{email_id}  → Re-classify
```

#### Email Sending
```
POST /api/v1/email-sends/{approval_id}/send   → Send approved reply
POST /api/v1/email-sends/batch                → Batch send
GET  /api/v1/email-sends?email_id=            → Send history
```

### 5.2 Modified Endpoints

#### Business Categories (Extend)
```
GET  /api/v1/business-categories/{id}        → Add: channel_configs, ai_tasks, decision_rules
PUT  /api/v1/business-categories/{id}        → Add: risk_level, default_auto_approve
GET  /api/v1/business-categories/{id}/tasks  → List AI tasks for category
GET  /api/v1/business-categories/{id}/knowledge  → List knowledge sources
GET  /api/v1/business-categories/{id}/decision-rules  → List decision rules
```

#### AI Approvals (Extend)
```
POST /api/v1/ai-approvals/{id}/approve      → Add: trigger email sending
GET  /api/v1/ai-approvals                   → Add: confidence_score, auto_approved filters
```

#### Emails (Extend)
```
GET  /api/v1/emails                         → Add: category, classification_confidence, ai_draft_status filters
GET  /api/v1/emails/{id}                    → Add: classification, knowledge context, send status
```

---

## 6. FRONTEND CHANGES

### 6.1 Business Categories → Workspace (Tabbed)
**Current:** Simple CRUD list
**New:** Tabbed workspace at `/business-categories/{id}`

```
/business-categories
├─ List view (existing)
└─ /business-categories/{id}  → Tabbed workspace
   ├─ Tab: Overview (name, code, color, metrics, risk level)
   ├─ Tab: Workflows (list + create + link to category)
   ├─ Tab: Prompts (existing prompt manager, scoped to category)
   ├─ Tab: AI Tasks (task list, configure model/temp per task)
   ├─ Tab: Knowledge (upload docs, manage sources)
   ├─ Tab: Decision Rules (auto-approve settings)
   └─ Tab: Channels (email config, whatsapp placeholder)
```

### 6.2 Task Queue Dashboard
**Current:** Basic automation activity page
**New:** Real-time queue monitoring

```
/automation
├─ Task Queue Status (pending, processing, completed, failed)
├─ Recent Tasks (with retry/cancel actions)
├─ Worker Health (APScheduler status)
└─ Execution Timeline (existing)
```

### 6.3 Email Monitoring Enhancements
**Current:** Email list with basic status
**New:** Show classification, AI draft, send status

```
/monitoring
├─ Email table: Add columns for Category, Classification Confidence, AI Draft Status
├─ Email detail: Show classification, AI output, knowledge used, send status
└─ Actions: Reclassify, View AI Task, View Approval, View Send
```

### 6.4 Approval Queue Enhancements
**Current:** Basic approve/reject
**New:** Show confidence, knowledge context, send action

```
/approvals
├─ Approval cards: Add confidence score, decision rule that matched
├─ Approve action: Also trigger email send
├─ Send button: One-click send for already-approved drafts
└─ Send status: Show sent/failed/pending
```

---

## 7. IMPLEMENTATION ORDER

### Week 1: Foundation (Async Infrastructure)
1. Create `task_queue` table + `TaskQueueService`
2. Modify `SyncOrchestrator` to enqueue instead of inline execution
3. Add APScheduler job to process task queue
4. Create `email_classifications` table
5. Create `CategoryMatcherService` (basic rule-based matching)
6. Test: Email sync → auto-classify → category assigned

### Week 2: AI Tasks + Knowledge
1. Create `ai_tasks` table + `AITaskService`
2. Create `knowledge_sources` table + `KnowledgeService`
3. Modify `PromptBuilderService` to inject knowledge
4. Modify `WorkflowExecutionService` to trigger AI tasks via queue
5. Test: Email → category → workflow → AI task → draft generated

### Week 3: Decision + Approval + Sending
1. Create `decision_rules` table + `DecisionService`
2. Extend `AIApproval` table + `ApprovalService`
3. Create `email_sends` table + `EmailSenderService`
4. Integrate Gmail API for sending
5. Test: Email → classify → AI → decision → approval → send

### Week 4: Frontend + Polish
1. Build category workspace UI (tabs)
2. Build task queue dashboard
3. Enhance email monitoring with classification
4. Enhance approval queue with send action
5. End-to-end testing
6. Documentation

---

## 8. WHAT STAYS THE SAME

| Component | Status |
|-----------|--------|
| Gmail OAuth flow | ✅ Unchanged |
| SyncOrchestrator (core sync logic) | ✅ Unchanged (just async wrapper) |
| Email parsing | ✅ Unchanged |
| Attachment storage | ✅ Unchanged |
| JWT authentication | ✅ Unchanged |
| RBAC permissions | ✅ Unchanged |
| Workflow rule engine | ✅ Unchanged |
| AI provider failover | ✅ Unchanged |
| SSE event streaming | ✅ Unchanged |
| System logging | ✅ Unchanged |
| Admin audit logging | ✅ Unchanged |
| All Sprint 5 features | ✅ Unchanged |
| All Sprint 6 Phase 2A features | ✅ Unchanged |

---

## 9. WHAT GETS DEPRECATED

| Component | Action |
|-----------|--------|
| Legacy `prompt_templates` table | Deprecate after Phase 2B migration |
| Inline workflow execution | Replace with async queue |
| Direct AI service calls from workflows | Replace with AITaskService |

---

## 10. SUCCESS CRITERIA

**User Story:**
> "As an admin, I create a business category called 'Refund', configure it with a workflow that matches emails containing 'refund' in the subject, attach a prompt template that drafts a refund acknowledgment, set a decision rule to auto-approve high-confidence refunds under $100, and from then on every refund email is automatically classified, drafted, approved, and sent within 30 seconds."

**Technical Metrics:**
- 1000 emails/day processed without errors
- <30 seconds email-to-send latency (99th percentile)
- <5% false positive rate in auto-approval
- All Sprint 5 + Phase 2A features still working
- Zero data loss during async processing

---

## 11. RISK MITIGATION

| Risk | Mitigation |
|------|------------|
| Database queue performance | Index on (status, priority, scheduled_at); batch processing; upgrade to Redis in Phase 3 if needed |
| Gmail API rate limits | Exponential backoff; dead-letter queue; batch sending |
| AI provider failures | Existing failover chain; static fallback draft |
| Auto-approval mistakes | Conservative rules (high confidence + low risk only); admin can override; full audit trail |
| Knowledge base quality | Phase 2B: simple text search; Phase 3: vector search with relevance scoring |
