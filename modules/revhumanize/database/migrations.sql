-- ═══════════════════════════════════════════════════════════════════════════
-- Humanization Pipeline - Database Migrations
-- ═══════════════════════════════════════════════════════════════════════════

-- Review Queue Table
CREATE TABLE IF NOT EXISTS review_queue (
    id SERIAL PRIMARY KEY,
    content_id VARCHAR(100) UNIQUE NOT NULL,
    title VARCHAR(500),
    content TEXT NOT NULL,
    
    -- Quality metrics
    qa_score FLOAT,
    voice_consistency_score FLOAT,
    ymyl_verification_score FLOAT,
    ai_probability FLOAT,
    
    -- Validation results
    tier1_issues JSONB,
    tier2_issues JSONB,
    tier3_issues JSONB,
    voice_violations JSONB,
    ymyl_failures JSONB,
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    assigned_to VARCHAR(100),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    reviewed_by VARCHAR(100),
    
    -- Review notes
    reviewer_notes TEXT,
    fixed_content TEXT
);

-- Indexes for review queue
CREATE INDEX IF NOT EXISTS idx_review_queue_status ON review_queue(status);
CREATE INDEX IF NOT EXISTS idx_review_queue_created_at ON review_queue(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_review_queue_priority ON review_queue(priority DESC);

-- Audit Log Table
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Who/What/Where
    "user" VARCHAR(100),
    action VARCHAR(100),
    entity_type VARCHAR(50),
    entity_id VARCHAR(100),
    
    -- Details
    changes JSONB,
    metadata JSONB,
    ip_address VARCHAR(50),
    user_agent TEXT,
    
    -- Result
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

-- Indexes for audit log
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log("user");
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);

-- Webhook Log Table
CREATE TABLE IF NOT EXISTS webhook_log (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Webhook details
    url VARCHAR(500) NOT NULL,
    event VARCHAR(100),
    payload JSONB,
    
    -- Delivery
    status_code INTEGER,
    response TEXT,
    success BOOLEAN DEFAULT FALSE,
    attempts INTEGER DEFAULT 0,
    
    -- Related
    content_id VARCHAR(100)
);

-- Indexes for webhook log
CREATE INDEX IF NOT EXISTS idx_webhook_log_created_at ON webhook_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_webhook_log_event ON webhook_log(event);
CREATE INDEX IF NOT EXISTS idx_webhook_log_success ON webhook_log(success);
CREATE INDEX IF NOT EXISTS idx_webhook_log_content_id ON webhook_log(content_id);

-- ═══════════════════════════════════════════════════════════════════════════
-- Initial Data / Seed
-- ═══════════════════════════════════════════════════════════════════════════

-- Log migration
INSERT INTO audit_log ("user", action, entity_type, success, metadata)
VALUES ('system', 'database_migration', 'schema', TRUE, '{"version": "1.0.0", "date": "2025-01-04"}');
