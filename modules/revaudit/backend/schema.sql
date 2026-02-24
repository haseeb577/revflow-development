-- RevAudit Anti-Hallucination Framework
-- Database Schema for Data Provenance & Integrity
-- Created: 2026-02-09

-- ============================================
-- API Call Audit Log
-- Every external API call is logged here
-- ============================================
CREATE TABLE IF NOT EXISTS audit_api_calls (
    id SERIAL PRIMARY KEY,
    audit_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),

    -- What was called
    tool VARCHAR(100) NOT NULL,          -- 'DataForSEO', 'ChatGPT', 'Gemini', 'GBP_API'
    endpoint VARCHAR(500) NOT NULL,       -- Full endpoint URL
    method VARCHAR(10) DEFAULT 'GET',     -- HTTP method

    -- Request details
    request_payload JSONB,                -- What was sent
    request_headers JSONB,                -- Headers (sanitized)

    -- Response details
    response_status INTEGER,              -- HTTP status code
    response_hash VARCHAR(64) NOT NULL,   -- SHA256 of response
    response_size INTEGER,                -- Response size in bytes
    raw_response_path TEXT,               -- Path to stored raw response

    -- Context
    called_by_module VARCHAR(100),        -- 'MODULE_2_RevScore_IQ'
    assessment_id UUID,                   -- Links to assessment
    session_id UUID,                      -- User session
    user_id VARCHAR(100),                 -- Who initiated

    -- Timing
    request_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    response_timestamp TIMESTAMP,
    duration_ms INTEGER,                  -- How long the call took

    -- Metadata
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_api_assessment ON audit_api_calls(assessment_id);
CREATE INDEX IF NOT EXISTS idx_audit_api_tool ON audit_api_calls(tool);
CREATE INDEX IF NOT EXISTS idx_audit_api_timestamp ON audit_api_calls(request_timestamp DESC);

-- ============================================
-- Data Claims Registry
-- Every claim in reports must be registered here
-- ============================================
CREATE TABLE IF NOT EXISTS audit_claims (
    id SERIAL PRIMARY KEY,
    claim_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),

    -- The claim itself
    claim_text TEXT NOT NULL,             -- "Review response rate: 94%"
    claim_type VARCHAR(50),               -- 'metric', 'score', 'recommendation'

    -- Source attribution
    source_audit_id UUID REFERENCES audit_api_calls(audit_id),
    source_tool VARCHAR(100),             -- Where this data came from
    source_field VARCHAR(200),            -- JSON path in response
    source_value TEXT,                    -- Actual value from API

    -- Confidence
    confidence_level VARCHAR(20) NOT NULL, -- 'HIGH', 'MEDIUM', 'LOW', 'UNVERIFIED'
    confidence_reason TEXT,

    -- Context
    assessment_id UUID,
    report_section VARCHAR(100),          -- 'visibility', 'reputation', etc.

    -- Verification
    verified BOOLEAN DEFAULT FALSE,
    verified_by VARCHAR(100),
    verified_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_claims_assessment ON audit_claims(assessment_id);
CREATE INDEX IF NOT EXISTS idx_audit_claims_confidence ON audit_claims(confidence_level);

-- ============================================
-- Hallucination Detection Log
-- Records when potential hallucinations are caught
-- ============================================
CREATE TABLE IF NOT EXISTS audit_hallucination_detections (
    id SERIAL PRIMARY KEY,
    detection_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),

    -- What was caught
    flagged_content TEXT NOT NULL,        -- The suspicious text
    detection_reason VARCHAR(200),        -- Why it was flagged
    detection_rule VARCHAR(100),          -- Which rule caught it

    -- Severity
    severity VARCHAR(20) NOT NULL,        -- 'BLOCKED', 'WARNING', 'INFO'
    action_taken VARCHAR(50),             -- 'blocked', 'flagged', 'allowed_with_warning'

    -- Context
    assessment_id UUID,
    module VARCHAR(100),

    -- Resolution
    resolved BOOLEAN DEFAULT FALSE,
    resolved_by VARCHAR(100),
    resolution_notes TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hallucination_severity ON audit_hallucination_detections(severity);
CREATE INDEX IF NOT EXISTS idx_hallucination_unresolved ON audit_hallucination_detections(resolved) WHERE resolved = FALSE;

-- ============================================
-- User Verification Gates
-- Track user approvals of data
-- ============================================
CREATE TABLE IF NOT EXISTS audit_verifications (
    id SERIAL PRIMARY KEY,
    verification_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),

    -- What was verified
    assessment_id UUID NOT NULL,
    data_type VARCHAR(50),                -- 'api_responses', 'scores', 'report'

    -- Verification status
    status VARCHAR(20) NOT NULL,          -- 'pending', 'approved', 'rejected'

    -- User action
    verified_by VARCHAR(100),
    verification_timestamp TIMESTAMP,
    user_notes TEXT,

    -- What they saw
    data_snapshot JSONB,                  -- Snapshot of data shown to user

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_verification_assessment ON audit_verifications(assessment_id);
CREATE INDEX IF NOT EXISTS idx_verification_status ON audit_verifications(status);

-- ============================================
-- Forbidden Phrases (Anti-Hallucination)
-- Phrases that indicate potential fabrication
-- ============================================
CREATE TABLE IF NOT EXISTS audit_forbidden_phrases (
    id SERIAL PRIMARY KEY,
    phrase TEXT NOT NULL UNIQUE,
    reason TEXT,
    severity VARCHAR(20) DEFAULT 'WARNING',
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert default forbidden phrases
INSERT INTO audit_forbidden_phrases (phrase, reason, severity) VALUES
    ('Based on industry best practices', 'Too vague - needs specific source', 'BLOCKED'),
    ('Typically we see', 'No data source cited', 'BLOCKED'),
    ('It is recommended', 'Who recommends? Needs attribution', 'WARNING'),
    ('Studies show', 'Which studies? Need citation', 'BLOCKED'),
    ('Experts suggest', 'Which experts? Need names', 'BLOCKED'),
    ('Research indicates', 'What research? Need source', 'BLOCKED'),
    ('Generally speaking', 'Too vague for data-driven report', 'WARNING'),
    ('In our experience', 'Anecdotal - needs data backing', 'WARNING'),
    ('Best practice suggests', 'Needs specific source', 'WARNING'),
    ('Industry standards indicate', 'Which standards? Need citation', 'WARNING')
ON CONFLICT (phrase) DO NOTHING;

-- Verification query
DO $$
BEGIN
    RAISE NOTICE '✅ RevAudit Anti-Hallucination Schema Created';
    RAISE NOTICE 'Tables: audit_api_calls, audit_claims, audit_hallucination_detections, audit_verifications, audit_forbidden_phrases';
END $$;
