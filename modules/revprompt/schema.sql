-- RevPrompt Unified™ Database Schema
-- PostgreSQL schema for multi-tenant content generation

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS revprompt;

-- Set search path
SET search_path TO revprompt, public;

-- ==========================================
-- CUSTOMERS & LICENSING (Multi-Tenant)
-- ==========================================

CREATE TABLE IF NOT EXISTS customers (
    customer_id SERIAL PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    license_tier VARCHAR(50) NOT NULL, -- STARTER, PROFESSIONAL, ENTERPRISE
    license_key VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) DEFAULT 'active', -- active, suspended, cancelled
    monthly_page_limit INTEGER DEFAULT 1000,
    pages_used_this_month INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    billing_cycle_start DATE,
    api_key VARCHAR(255) UNIQUE
);

CREATE INDEX idx_customers_license_key ON customers(license_key);
CREATE INDEX idx_customers_email ON customers(email);

-- ==========================================
-- GENERATED CONTENT
-- ==========================================

CREATE TABLE IF NOT EXISTS generated_content (
    content_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id),
    page_type VARCHAR(50) NOT NULL,
    business_name VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    location VARCHAR(255),
    voice_profile VARCHAR(50),
    content_html TEXT NOT NULL,
    content_plain TEXT,
    word_count INTEGER,
    metadata JSONB, -- stores generation metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_content_customer ON generated_content(customer_id);
CREATE INDEX idx_content_page_type ON generated_content(page_type);
CREATE INDEX idx_content_created ON generated_content(created_at DESC);

-- ==========================================
-- VALIDATION RESULTS
-- ==========================================

CREATE TABLE IF NOT EXISTS validation_results (
    validation_id SERIAL PRIMARY KEY,
    content_id INTEGER REFERENCES generated_content(content_id),
    customer_id INTEGER REFERENCES customers(customer_id),
    overall_score DECIMAL(5,2),
    spo_score DECIMAL(5,2),
    entity_score DECIMAL(5,2),
    guru_score DECIMAL(5,2),
    dedup_score DECIMAL(5,2),
    passed BOOLEAN DEFAULT FALSE,
    violations JSONB,
    recommendations JSONB,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_validation_content ON validation_results(content_id);
CREATE INDEX idx_validation_customer ON validation_results(customer_id);

-- ==========================================
-- BATCH JOBS
-- ==========================================

CREATE TABLE IF NOT EXISTS batch_jobs (
    job_id VARCHAR(100) PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id),
    total_pages INTEGER NOT NULL,
    completed INTEGER DEFAULT 0,
    failed INTEGER DEFAULT 0,
    in_progress INTEGER DEFAULT 0,
    pending INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending', -- pending, in_progress, completed, failed
    job_config JSONB,
    results JSONB,
    estimated_cost_usd DECIMAL(10,4),
    actual_cost_usd DECIMAL(10,4),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_batch_customer ON batch_jobs(customer_id);
CREATE INDEX idx_batch_status ON batch_jobs(status);

-- ==========================================
-- USAGE TRACKING (for billing)
-- ==========================================

CREATE TABLE IF NOT EXISTS usage_tracking (
    usage_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id),
    event_type VARCHAR(100) NOT NULL, -- generation, validation, batch_job
    event_details JSONB,
    cost_usd DECIMAL(10,4),
    api_calls INTEGER DEFAULT 1,
    tokens_used INTEGER,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_usage_customer ON usage_tracking(customer_id);
CREATE INDEX idx_usage_created ON usage_tracking(created_at DESC);
CREATE INDEX idx_usage_event_type ON usage_tracking(event_type);

-- ==========================================
-- PORTFOLIO SITES (53 sites)
-- ==========================================

CREATE TABLE IF NOT EXISTS portfolio_sites (
    site_id VARCHAR(100) PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id),
    site_name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    location VARCHAR(255),
    wordpress_url VARCHAR(500),
    wordpress_api_key TEXT,
    status VARCHAR(50) DEFAULT 'active',
    total_pages INTEGER DEFAULT 0,
    last_content_generated TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sites_customer ON portfolio_sites(customer_id);
CREATE INDEX idx_sites_domain ON portfolio_sites(domain);

-- ==========================================
-- DEDUPLICATION TRACKING
-- ==========================================

CREATE TABLE IF NOT EXISTS dedup_tracking (
    dedup_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id),
    content_id_1 INTEGER REFERENCES generated_content(content_id),
    content_id_2 INTEGER REFERENCES generated_content(content_id),
    similarity_score DECIMAL(5,4),
    concern_level VARCHAR(50), -- none, low, medium, high
    flagged BOOLEAN DEFAULT FALSE,
    reviewed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dedup_customer ON dedup_tracking(customer_id);
CREATE INDEX idx_dedup_similarity ON dedup_tracking(similarity_score DESC);
CREATE INDEX idx_dedup_flagged ON dedup_tracking(flagged);

-- ==========================================
-- PROMPT TEMPLATES (18 layers x 11 page types)
-- ==========================================

CREATE TABLE IF NOT EXISTS prompt_templates (
    template_id SERIAL PRIMARY KEY,
    page_type VARCHAR(50) NOT NULL,
    layer_id VARCHAR(100) NOT NULL,
    template_text TEXT NOT NULL,
    variables JSONB, -- list of template variables
    priority INTEGER,
    active BOOLEAN DEFAULT TRUE,
    version VARCHAR(20) DEFAULT '1.0',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(page_type, layer_id)
);

CREATE INDEX idx_templates_page_type ON prompt_templates(page_type);
CREATE INDEX idx_templates_layer ON prompt_templates(layer_id);

-- ==========================================
-- DEFAULT DEMO CUSTOMER
-- ==========================================

INSERT INTO customers (
    customer_name, 
    email, 
    license_tier, 
    license_key, 
    status,
    monthly_page_limit,
    api_key
) VALUES (
    'Shimon (Demo Account)',
    'shimon@revflow.io',
    'ENTERPRISE',
    'rp_demo_' || MD5(random()::text),
    'active',
    99999,
    'api_' || MD5(random()::text)
) ON CONFLICT (email) DO NOTHING;

-- ==========================================
-- VIEWS FOR ANALYTICS
-- ==========================================

CREATE OR REPLACE VIEW customer_usage_summary AS
SELECT 
    c.customer_id,
    c.customer_name,
    c.license_tier,
    COUNT(gc.content_id) as total_content_generated,
    SUM(ut.cost_usd) as total_cost_usd,
    c.monthly_page_limit,
    c.pages_used_this_month,
    CASE 
        WHEN c.pages_used_this_month >= c.monthly_page_limit THEN 'LIMIT_REACHED'
        WHEN c.pages_used_this_month >= (c.monthly_page_limit * 0.8) THEN 'WARNING'
        ELSE 'OK'
    END as usage_status
FROM customers c
LEFT JOIN generated_content gc ON c.customer_id = gc.customer_id
LEFT JOIN usage_tracking ut ON c.customer_id = ut.customer_id
GROUP BY c.customer_id;

-- ==========================================
-- FUNCTIONS
-- ==========================================

-- Function to reset monthly usage
CREATE OR REPLACE FUNCTION reset_monthly_usage()
RETURNS void AS $$
BEGIN
    UPDATE customers 
    SET pages_used_this_month = 0,
        billing_cycle_start = CURRENT_DATE
    WHERE CURRENT_DATE - billing_cycle_start >= 30;
END;
$$ LANGUAGE plpgsql;

-- Function to check license validity
CREATE OR REPLACE FUNCTION check_license(p_license_key VARCHAR)
RETURNS TABLE(
    valid BOOLEAN,
    customer_id INTEGER,
    license_tier VARCHAR,
    pages_remaining INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (c.status = 'active' AND c.pages_used_this_month < c.monthly_page_limit) as valid,
        c.customer_id,
        c.license_tier,
        (c.monthly_page_limit - c.pages_used_this_month) as pages_remaining
    FROM customers c
    WHERE c.license_key = p_license_key;
END;
$$ LANGUAGE plpgsql;

-- ==========================================
-- GRANTS
-- ==========================================

GRANT ALL PRIVILEGES ON SCHEMA revprompt TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA revprompt TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA revprompt TO postgres;

-- ==========================================
-- INITIAL DATA SUMMARY
-- ==========================================

SELECT 'Database schema created successfully!' as status;
SELECT COUNT(*) as demo_customers FROM customers WHERE email = 'shimon@revflow.io';
