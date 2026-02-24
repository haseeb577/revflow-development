-- ============================================================================
-- GURU INTELLIGENCE PLATFORM - UNIFIED KNOWLEDGE LAYER SCHEMA MIGRATION
-- Version: 1.0
-- Date: December 28, 2025
-- Purpose: Expand database to support Multi-Tiered Rule Engine + Prompt Library
-- ============================================================================

-- ============================================================================
-- PART 1: MODIFY EXISTING extracted_rules TABLE
-- ============================================================================

-- Add new columns to support Multi-Tiered Engine
ALTER TABLE extracted_rules 
ADD COLUMN IF NOT EXISTS complexity_level INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS validation_type VARCHAR(20) DEFAULT 'regex',
ADD COLUMN IF NOT EXISTS validation_pattern TEXT,
ADD COLUMN IF NOT EXISTS prompt_template TEXT,
ADD COLUMN IF NOT EXISTS applies_to_modules TEXT[] DEFAULT ARRAY['all'],
ADD COLUMN IF NOT EXISTS applies_to_page_types TEXT[],
ADD COLUMN IF NOT EXISTS applies_to_industries TEXT[],
ADD COLUMN IF NOT EXISTS auto_fixable BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS fix_template TEXT,
ADD COLUMN IF NOT EXISTS weight DECIMAL(3,2) DEFAULT 1.0,
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_rules_complexity ON extracted_rules(complexity_level);
CREATE INDEX IF NOT EXISTS idx_rules_validation_type ON extracted_rules(validation_type);
CREATE INDEX IF NOT EXISTS idx_rules_category ON extracted_rules(rule_category);
CREATE INDEX IF NOT EXISTS idx_rules_active ON extracted_rules(is_active);
CREATE INDEX IF NOT EXISTS idx_rules_modules ON extracted_rules USING GIN(applies_to_modules);
CREATE INDEX IF NOT EXISTS idx_rules_page_types ON extracted_rules USING GIN(applies_to_page_types);

COMMENT ON COLUMN extracted_rules.complexity_level IS 'Tier level: 1=regex/deterministic, 2=NLP/spaCy, 3=LLM required';
COMMENT ON COLUMN extracted_rules.validation_type IS 'Type: regex, keyword, count, spacy, llm';
COMMENT ON COLUMN extracted_rules.validation_pattern IS 'Regex pattern OR function name OR keyword list';
COMMENT ON COLUMN extracted_rules.prompt_template IS 'For Tier 3 rules: the prompt to send to Claude';
COMMENT ON COLUMN extracted_rules.weight IS 'Scoring weight for this rule (0.0-1.0)';

-- ============================================================================
-- PART 2: CREATE knowledge_items TABLE (Master Knowledge Repository)
-- ============================================================================

CREATE TABLE IF NOT EXISTS knowledge_items (
    id SERIAL PRIMARY KEY,
    item_type VARCHAR(50) NOT NULL CHECK (item_type IN ('rule', 'prompt', 'framework', 'config', 'guideline', 'template')),
    category VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    content TEXT,
    
    -- Validation metadata (for rules)
    complexity_level INTEGER DEFAULT 1 CHECK (complexity_level BETWEEN 1 AND 3),
    validation_type VARCHAR(20),
    validation_pattern TEXT,
    prompt_template TEXT,
    
    -- Applicability filters
    applies_to_modules TEXT[],
    applies_to_page_types TEXT[],
    applies_to_industries TEXT[],
    
    -- Scoring configuration
    priority_score INTEGER DEFAULT 50 CHECK (priority_score BETWEEN 0 AND 100),
    enforcement_level VARCHAR(20) CHECK (enforcement_level IN ('required', 'recommended', 'optional')),
    weight DECIMAL(3,2) DEFAULT 1.0 CHECK (weight >= 0 AND weight <= 10.0),
    
    -- Auto-fix capabilities
    auto_fixable BOOLEAN DEFAULT FALSE,
    fix_template TEXT,
    
    -- Metadata
    source_document VARCHAR(255),
    version VARCHAR(20) DEFAULT '1.0',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Relationships
    parent_id INTEGER REFERENCES knowledge_items(id),
    related_items INTEGER[]
);

-- Indexes for knowledge_items
CREATE INDEX IF NOT EXISTS idx_knowledge_type ON knowledge_items(item_type);
CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge_items(category, subcategory);
CREATE INDEX IF NOT EXISTS idx_knowledge_complexity ON knowledge_items(complexity_level);
CREATE INDEX IF NOT EXISTS idx_knowledge_modules ON knowledge_items USING GIN(applies_to_modules);
CREATE INDEX IF NOT EXISTS idx_knowledge_page_types ON knowledge_items USING GIN(applies_to_page_types);
CREATE INDEX IF NOT EXISTS idx_knowledge_active ON knowledge_items(is_active);
CREATE INDEX IF NOT EXISTS idx_knowledge_enforcement ON knowledge_items(enforcement_level);

-- ============================================================================
-- PART 3: CREATE prompt_templates TABLE (Prompt Library)
-- ============================================================================

CREATE TABLE IF NOT EXISTS prompt_templates (
    id SERIAL PRIMARY KEY,
    prompt_id VARCHAR(50) UNIQUE NOT NULL,
    prompt_type VARCHAR(50) NOT NULL CHECK (prompt_type IN ('generation', 'validation', 'meta', 'analysis', 'extraction', 'enhancement')),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- The actual prompts
    system_prompt TEXT,
    user_prompt_template TEXT,
    
    -- Variable management
    required_variables TEXT[],
    optional_variables TEXT[],
    variable_descriptions JSONB,
    
    -- Model configuration
    preferred_model VARCHAR(50) DEFAULT 'claude-sonnet-4-20250514',
    max_tokens INTEGER DEFAULT 2000,
    temperature DECIMAL(2,1) DEFAULT 0.7 CHECK (temperature >= 0 AND temperature <= 1.0),
    
    -- Applicability
    applies_to_modules TEXT[],
    applies_to_page_types TEXT[],
    
    -- Example usage
    example_input JSONB,
    example_output TEXT,
    
    -- Metadata
    category VARCHAR(100),
    tags TEXT[],
    version VARCHAR(20) DEFAULT '1.0',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Usage statistics
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    average_tokens_used INTEGER
);

-- Indexes for prompt_templates
CREATE INDEX IF NOT EXISTS idx_prompts_type ON prompt_templates(prompt_type);
CREATE INDEX IF NOT EXISTS idx_prompts_category ON prompt_templates(category);
CREATE INDEX IF NOT EXISTS idx_prompts_active ON prompt_templates(is_active);
CREATE INDEX IF NOT EXISTS idx_prompts_modules ON prompt_templates USING GIN(applies_to_modules);
CREATE INDEX IF NOT EXISTS idx_prompts_tags ON prompt_templates USING GIN(tags);

-- ============================================================================
-- PART 4: CREATE scoring_frameworks TABLE (Scoring Rubrics)
-- ============================================================================

CREATE TABLE IF NOT EXISTS scoring_frameworks (
    id SERIAL PRIMARY KEY,
    framework_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Scoring configuration
    max_score INTEGER DEFAULT 100 CHECK (max_score > 0),
    passing_threshold INTEGER DEFAULT 70 CHECK (passing_threshold >= 0 AND passing_threshold <= max_score),
    
    -- Component weights (JSON structure)
    components JSONB NOT NULL,
    -- Example: {"experience": 0.25, "expertise": 0.25, "authority": 0.25, "trust": 0.25}
    
    -- Rules linked to this framework
    rule_ids TEXT[],
    tier1_rules TEXT[],
    tier2_rules TEXT[],
    tier3_rules TEXT[],
    
    -- Applicability
    applies_to_modules TEXT[],
    applies_to_page_types TEXT[],
    
    -- Metadata
    category VARCHAR(100),
    version VARCHAR(20) DEFAULT '1.0',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Indexes for scoring_frameworks
CREATE INDEX IF NOT EXISTS idx_frameworks_active ON scoring_frameworks(is_active);
CREATE INDEX IF NOT EXISTS idx_frameworks_category ON scoring_frameworks(category);
CREATE INDEX IF NOT EXISTS idx_frameworks_modules ON scoring_frameworks USING GIN(applies_to_modules);

-- ============================================================================
-- PART 5: CREATE industry_configs TABLE (Industry-Specific Settings)
-- ============================================================================

CREATE TABLE IF NOT EXISTS industry_configs (
    id SERIAL PRIMARY KEY,
    industry_code VARCHAR(50) UNIQUE NOT NULL,
    industry_name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Content configuration
    backstory_template TEXT,
    service_catalog JSONB,
    pricing_ranges JSONB,
    
    -- Credential patterns
    license_patterns TEXT[],
    certification_keywords TEXT[],
    
    -- Local terminology by region
    regional_terms JSONB,
    
    -- Module-specific overrides
    rr_config JSONB,
    revflow_config JSONB,
    prompt_lab_config JSONB,
    
    -- Default values
    default_word_counts JSONB,
    default_voice_modality VARCHAR(20),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Indexes for industry_configs
CREATE INDEX IF NOT EXISTS idx_industry_code ON industry_configs(industry_code);
CREATE INDEX IF NOT EXISTS idx_industry_active ON industry_configs(is_active);

-- ============================================================================
-- PART 6: CREATE validation_history TABLE (Audit Trail)
-- ============================================================================

CREATE TABLE IF NOT EXISTS validation_history (
    id SERIAL PRIMARY KEY,
    content_id VARCHAR(100),
    page_type VARCHAR(50),
    industry VARCHAR(50),
    module VARCHAR(50),
    
    -- Assessment details
    overall_score INTEGER,
    passed BOOLEAN,
    tiers_run INTEGER[],
    
    -- Tier results
    tier1_checked INTEGER,
    tier1_passed INTEGER,
    tier2_checked INTEGER,
    tier2_passed INTEGER,
    tier3_checked INTEGER,
    tier3_passed INTEGER,
    
    -- Violations
    violations_count INTEGER,
    violations JSONB,
    
    -- Cost tracking
    api_cost DECIMAL(10,4),
    tokens_used INTEGER,
    
    -- Performance
    processing_time_ms INTEGER,
    
    -- Metadata
    assessed_at TIMESTAMP DEFAULT NOW(),
    assessed_by VARCHAR(100)
);

-- Indexes for validation_history
CREATE INDEX IF NOT EXISTS idx_validation_content ON validation_history(content_id);
CREATE INDEX IF NOT EXISTS idx_validation_date ON validation_history(assessed_at);
CREATE INDEX IF NOT EXISTS idx_validation_module ON validation_history(module);
CREATE INDEX IF NOT EXISTS idx_validation_passed ON validation_history(passed);

-- ============================================================================
-- PART 7: CREATE prompt_usage_log TABLE (Prompt Analytics)
-- ============================================================================

CREATE TABLE IF NOT EXISTS prompt_usage_log (
    id SERIAL PRIMARY KEY,
    prompt_id VARCHAR(50) REFERENCES prompt_templates(prompt_id),
    module VARCHAR(50),
    page_type VARCHAR(50),
    
    -- Execution details
    variables_used JSONB,
    tokens_generated INTEGER,
    cost DECIMAL(10,4),
    execution_time_ms INTEGER,
    
    -- Quality metrics
    validation_score INTEGER,
    user_feedback INTEGER,
    
    -- Metadata
    executed_at TIMESTAMP DEFAULT NOW(),
    executed_by VARCHAR(100)
);

-- Indexes for prompt_usage_log
CREATE INDEX IF NOT EXISTS idx_prompt_usage_id ON prompt_usage_log(prompt_id);
CREATE INDEX IF NOT EXISTS idx_prompt_usage_date ON prompt_usage_log(executed_at);
CREATE INDEX IF NOT EXISTS idx_prompt_usage_module ON prompt_usage_log(module);

-- ============================================================================
-- PART 8: CREATE VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View: Active Tier 1 Rules
CREATE OR REPLACE VIEW v_tier1_rules AS
SELECT 
    rule_id,
    rule_name,
    rule_category,
    rule_description,
    validation_type,
    validation_pattern,
    enforcement_level,
    priority_score,
    applies_to_modules,
    applies_to_page_types
FROM extracted_rules
WHERE complexity_level = 1 
  AND is_active = TRUE
ORDER BY priority_score DESC;

-- View: Active Tier 3 Rules (LLM-based)
CREATE OR REPLACE VIEW v_tier3_rules AS
SELECT 
    rule_id,
    rule_name,
    rule_category,
    rule_description,
    prompt_template,
    enforcement_level,
    priority_score,
    applies_to_modules,
    applies_to_page_types
FROM extracted_rules
WHERE complexity_level = 3 
  AND is_active = TRUE
  AND prompt_template IS NOT NULL
ORDER BY priority_score DESC;

-- View: Prompt Library Summary
CREATE OR REPLACE VIEW v_prompt_summary AS
SELECT 
    prompt_id,
    name,
    prompt_type,
    category,
    preferred_model,
    usage_count,
    last_used_at,
    applies_to_modules,
    is_active
FROM prompt_templates
ORDER BY prompt_type, category, name;

-- View: Validation Statistics by Module
CREATE OR REPLACE VIEW v_validation_stats AS
SELECT 
    module,
    page_type,
    COUNT(*) as total_assessments,
    SUM(CASE WHEN passed THEN 1 ELSE 0 END) as passed_count,
    ROUND(AVG(overall_score), 2) as avg_score,
    SUM(api_cost) as total_cost,
    ROUND(AVG(processing_time_ms), 0) as avg_processing_ms
FROM validation_history
WHERE assessed_at >= NOW() - INTERVAL '30 days'
GROUP BY module, page_type
ORDER BY module, page_type;

-- ============================================================================
-- PART 9: GRANT PERMISSIONS
-- ============================================================================

-- Ensure knowledge_admin has all necessary permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO knowledge_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO knowledge_admin;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO knowledge_admin;

-- ============================================================================
-- PART 10: MIGRATION VERIFICATION QUERIES
-- ============================================================================

-- Verify table structure
DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name IN ('extracted_rules', 'knowledge_items', 'prompt_templates', 
                         'scoring_frameworks', 'industry_configs', 'validation_history', 
                         'prompt_usage_log');
    
    RAISE NOTICE 'Tables created: %', table_count;
    
    IF table_count < 7 THEN
        RAISE WARNING 'Expected 7 tables, found %', table_count;
    END IF;
END $$;

-- Display column additions to extracted_rules
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'extracted_rules'
  AND column_name IN ('complexity_level', 'validation_type', 'validation_pattern', 
                      'prompt_template', 'applies_to_modules', 'auto_fixable')
ORDER BY ordinal_position;

-- ============================================================================
-- END OF SCHEMA MIGRATION
-- ============================================================================

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Guru Unified Knowledge Layer schema migration completed successfully!';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Run rule categorization script to set complexity_level for all 359 rules';
    RAISE NOTICE '2. Populate prompt_templates with core prompts';
    RAISE NOTICE '3. Create scoring_frameworks for E-E-A-T, GEO, etc.';
    RAISE NOTICE '4. Deploy Multi-Tiered Assessor API';
END $$;
