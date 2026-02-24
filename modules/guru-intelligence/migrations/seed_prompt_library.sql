-- ============================================================================
-- GURU INTELLIGENCE - PROMPT LIBRARY SEED DATA
-- Populates prompt_templates with core prompts from R&R Automation
-- ============================================================================

-- ============================================================================
-- BASE LAYER PROMPTS (Rank Expand Foundation)
-- ============================================================================

INSERT INTO prompt_templates (
    prompt_id, prompt_type, name, description, category,
    system_prompt, user_prompt_template,
    required_variables, optional_variables, preferred_model,
    max_tokens, temperature, applies_to_modules, applies_to_page_types,
    is_active
) VALUES
(
    'BASE-001',
    'generation',
    'Promptmaster - Base Writing Style',
    'Foundation prompt that sets tone and format for all content generation',
    'Base Layer',
    'You are an expert content writer for local home services businesses. You write in a friendly, conversational tone while maintaining professionalism.',
    'Write in a friendly tone-of-voice and keep your language simple and straight-forward. Provide the result in basic Markdown format.

Target audience: {target_audience}
Industry: {industry}
Location: {location}',
    ARRAY['target_audience', 'industry', 'location'],
    ARRAY['brand_voice', 'special_instructions'],
    'claude-sonnet-4-20250514',
    2000,
    0.7,
    ARRAY['rr-automation', 'revflow'],
    NULL,
    TRUE
),
(
    'BASE-002',
    'generation',
    'Promptknowledge - Style Consistency',
    'References example content to maintain consistent style and formatting',
    'Base Layer',
    NULL,
    'Reference the following example content and formatting. If available, analyze the example text to find any information gaps and incorporate into the output.

EXAMPLE CONTENT:
{example_text}

Maintain similar:
- Tone and voice
- Sentence structure
- Technical depth
- Call-to-action style',
    ARRAY['example_text'],
    NULL,
    'claude-sonnet-4-20250514',
    2000,
    0.7,
    ARRAY['rr-automation'],
    NULL,
    TRUE
);

-- ============================================================================
-- PAGE TYPE PROMPTS (Structural Templates)
-- ============================================================================

INSERT INTO prompt_templates (
    prompt_id, prompt_type, name, description, category,
    system_prompt, user_prompt_template,
    required_variables, preferred_model, max_tokens, temperature,
    applies_to_modules, applies_to_page_types, is_active
) VALUES
(
    'GEN-HOMEPAGE-001',
    'generation',
    'Homepage Content Generator',
    'Generates comprehensive homepage content for local service businesses',
    'Page Generation',
    NULL,
    'The homepage is one of the most important pages on this website to rank on Google. The homepage can be regarded as the executive summary for the website, and should refer all the different aspects of the business: the service area, services on offer, a little bit about the company, and why the customer should choose for us.

Company: {company_name}
Primary Service: {primary_service}
Service Area: {service_area}
Years in Business: {years_established}
License: {license_number}

Word Count Target: 1,200-2,000 words

REQUIRED SECTIONS:
1. Leader (3 lines) - Compelling opening that includes company name, service, and location
2. Introduction (≤200 words) - BLUF style, answer "What does this company do?"
3. Services Overview - List main services with brief descriptions
4. Why Choose Us - 3-5 differentiators
5. Service Area - Cities and neighborhoods served
6. Company Background - Brief history, credentials
7. Call to Action - Phone number, emergency services mention

CRITICAL REQUIREMENTS:
- First sentence must answer: "What does {company_name} do?"
- Include phone number: {phone}
- Mention at least 5 city names from service area
- Include license number
- Use question-format H2 headers',
    ARRAY['company_name', 'primary_service', 'service_area', 'years_established', 'license_number', 'phone'],
    'claude-sonnet-4-20250514',
    3000,
    0.7,
    ARRAY['rr-automation'],
    ARRAY['homepage'],
    TRUE
),
(
    'GEN-SERVICE-001',
    'generation',
    'Service Page Content Generator',
    'Generates focused service page content following BLUF and AI-SEO best practices',
    'Page Generation',
    NULL,
    'A service page is one of the main ranking pages for this website on Google. Service pages need to be focused on the main topic and dive deep into the service provided, and the context in which this company provides it. It shouldn\'t dive into related services, as there will be a separate page for those. The top of the service page should address the customer\'s search intent directly, and discuss the topic from most urgent and time-sensitive to least.

Company: {company_name}
Service: {service_name}
Location: {location}
Price Range: {price_range}
Industry: {industry}

Word Count Target: 800-1,200 words

REQUIRED STRUCTURE:
1. Leader (3 lines) - Direct answer to "What is {service_name}?"
2. H2: "How Much Does {service_name} Cost in {location}?"
   - BLUF answer in first sentence (40-60 words)
   - Include specific price range
   - Mention factors affecting cost
3. H2: "What is {service_name}?"
   - Technical explanation
   - When it\'s needed
   - Common scenarios
4. H2: "Why Choose {company_name} for {service_name}?"
   - Credentials and experience
   - Service guarantees
   - Response time
5. FAQ Section (3-5 questions)

CRITICAL REQUIREMENTS:
- EVERY H2 must be a question
- First sentence after each H2 must directly answer the question (BLUF)
- Include at least 3 city/neighborhood mentions
- Include phone number and license
- Use Partner voice (directive, confident, action-oriented)
- Include specific numbers: pricing, timeframes, years experience',
    ARRAY['company_name', 'service_name', 'location', 'price_range', 'industry'],
    'claude-sonnet-4-20250514',
    2500,
    0.7,
    ARRAY['rr-automation'],
    ARRAY['service'],
    TRUE
),
(
    'GEN-LOCATION-001',
    'generation',
    'Location Page Content Generator',
    'Generates location-specific content with local proof signals',
    'Page Generation',
    NULL,
    'Create a location-specific page that demonstrates deep local knowledge and proves this business genuinely serves this area.

Company: {company_name}
Service: {primary_service}
Target City: {city}
Neighborhoods: {neighborhoods}
Local Landmarks: {landmarks}

Word Count Target: ~800 words

REQUIRED LOCAL PROOF SIGNALS:
- Mention target city {city} at least 8 times
- Include 3+ specific neighborhoods: {neighborhoods}
- Reference 2+ local landmarks: {landmarks}
- Mention nearby highways/major roads
- Include service radius in miles

REQUIRED STRUCTURE:
1. Leader (3 lines) - "{primary_service} in {city}"
2. H2: "Professional {primary_service} Services in {city}"
   - BLUF: Service availability, response time, coverage area
3. H2: "Areas We Serve in {city}"
   - List neighborhoods with brief context
   - Mention landmarks near each area
4. H2: "Why {city} Residents Choose {company_name}"
   - Local experience (years serving area)
   - Knowledge of local building codes/regulations
   - Familiarity with common local issues
5. H2: "Schedule {primary_service} in {city} Today"
   - Call to action
   - Phone number
   - Service hours

CRITICAL REQUIREMENTS:
- High-resolution test: Could a competitor NOT use this by just changing the name?
- Specific street names, subdivisions, or local references
- Local terminology (e.g., "The Valley" in Phoenix, "SoCal" in LA)
- Mention local weather/climate factors if relevant to service',
    ARRAY['company_name', 'primary_service', 'city', 'neighborhoods', 'landmarks'],
    'claude-sonnet-4-20250514',
    2000,
    0.7,
    ARRAY['rr-automation'],
    ARRAY['location', 'service_area'],
    TRUE
);

-- ============================================================================
-- ENHANCEMENT PROMPTS (AI-SEO Layers)
-- ============================================================================

INSERT INTO prompt_templates (
    prompt_id, prompt_type, name, description, category,
    system_prompt, user_prompt_template,
    required_variables, preferred_model, max_tokens, temperature,
    applies_to_modules, is_active
) VALUES
(
    'ENH-BLUF-001',
    'enhancement',
    'BLUF Enforcement',
    'Ensures content follows Bottom Line Up Front structure',
    'AI-SEO Enhancement',
    'You are a content editor specializing in BLUF (Bottom Line Up Front) structure for AI-optimized content.',
    'Review this content and ensure EVERY H2 header is followed by a 40-60 word direct answer in the first sentence.

CONTENT:
{content}

RULES:
1. First sentence after H2 must answer the question directly
2. No throat-clearing phrases: "When it comes to...", "Many people wonder...", "If you\'re looking for..."
3. Answer must be 40-60 words
4. Include specific details: numbers, locations, timeframes

Return the content with BLUF structure applied.',
    ARRAY['content'],
    'claude-sonnet-4-20250514',
    3000,
    0.5,
    ARRAY['rr-automation'],
    TRUE
),
(
    'ENH-ENTITY-001',
    'enhancement',
    'Entity Density Optimization',
    'Adds or strengthens entity signals for AI visibility',
    'AI-SEO Enhancement',
    'You are an entity optimization specialist. Your job is to strengthen entity signals for better AI visibility.',
    'Enhance this content with strong entity signals:

CONTENT:
{content}

REQUIRED ENTITIES TO STRENGTHEN:
- Business: {company_name}
- Location: {location} (+ neighborhoods)
- Service: {service}
- People: Add technician/owner names
- Credentials: {license_number}
- Mechanisms: Proprietary service methods

REQUIREMENTS:
- First paragraph must contain: business name, service, location, credential
- Add 2-3 specific person names with titles
- Strengthen location mentions (8-12 city/neighborhood references)
- Add numeric specificity (years, counts, measurements)

Return enhanced content with entity signals.',
    ARRAY['content', 'company_name', 'location', 'service', 'license_number'],
    'claude-sonnet-4-20250514',
    3000,
    0.6,
    ARRAY['rr-automation'],
    TRUE
);

-- ============================================================================
-- VALIDATION PROMPTS (Tier 3 LLM Checks)
-- ============================================================================

INSERT INTO prompt_templates (
    prompt_id, prompt_type, name, description, category,
    system_prompt, user_prompt_template,
    required_variables, preferred_model, max_tokens, temperature,
    applies_to_modules, is_active
) VALUES
(
    'VAL-TIER3-001',
    'validation',
    'Batched Tier 3 Validation',
    'Multi-rule LLM validation in single API call',
    'Validation',
    'You are a content quality auditor. Assess content against multiple quality rules strictly but fairly.',
    'Analyze this content against {rule_count} quality rules.

CONTENT TO ASSESS:
---
{content}
---

RULES TO CHECK:
{rules_list}

For each rule, provide your assessment in this JSON format:
{{
    "assessments": [
        {{"rule_id": "BLUF-001", "passed": true, "reason": "First sentence directly answers the question"}},
        {{"rule_id": "TONE-003", "passed": false, "reason": "Tone is too casual for professional service page"}}
    ]
}}

Be strict but fair. Only mark as failed if clearly violated. Respond ONLY with valid JSON.',
    ARRAY['content', 'rule_count', 'rules_list'],
    'claude-sonnet-4-20250514',
    1000,
    0.3,
    ARRAY['rr-automation', 'revflow'],
    TRUE
),
(
    'VAL-TONE-001',
    'validation',
    'Voice Modality Validator',
    'Validates content matches appropriate voice (Partner/Professor/Peer)',
    'Validation',
    'You are a tone and voice expert for home services content.',
    'Assess if this content uses the appropriate voice modality.

CONTENT:
{content}

PAGE TYPE: {page_type}
EXPECTED VOICE: {expected_voice}

VOICE DEFINITIONS:
- Partner (Emergency/Transactional): Directive, confident, action-oriented. Commands: "Call now", "Don\'t wait"
- Professor (Technical/Legal): Precise, citation-heavy, neutral. "According to...", "Standards require..."
- Peer (Comparison/Pain-driven): Empathetic, validating. "Many homeowners feel...", "You might be wondering..."

Does this content match the expected {expected_voice} voice?
- YES or NO
- Brief explanation
- Quote specific phrases that support your assessment

Respond in JSON: {{"passed": true/false, "reason": "...", "examples": []}}',
    ARRAY['content', 'page_type', 'expected_voice'],
    'claude-sonnet-4-20250514',
    500,
    0.3,
    ARRAY['rr-automation'],
    TRUE
);

-- ============================================================================
-- ANALYSIS PROMPTS (RevFlow & Research)
-- ============================================================================

INSERT INTO prompt_templates (
    prompt_id, prompt_type, name, description, category,
    system_prompt, user_prompt_template,
    required_variables, preferred_model, max_tokens, temperature,
    applies_to_modules, is_active
) VALUES
(
    'ANALYZE-REVFLOW-001',
    'analysis',
    'Digital Presence Assessment',
    'McKinsey-quality digital presence analysis for RevFlow',
    'RevFlow Analysis',
    'You are a senior digital marketing analyst providing McKinsey-quality assessments.',
    'Analyze this business\'s digital presence and provide a comprehensive assessment.

BUSINESS: {business_name}
INDUSTRY: {industry}
LOCATION: {location}

DATA PROVIDED:
- Website analysis: {website_data}
- Local SEO metrics: {local_seo_data}
- Reputation data: {reputation_data}
- Competitor benchmarks: {competitor_data}

Provide assessment in these areas:
1. TECHNICAL FOUNDATION (Website performance, mobile-friendliness, technical SEO)
2. LOCAL SEO PRESENCE (GBP optimization, citations, local rankings)
3. REPUTATION & TRUST (Review velocity, rating trends, response patterns)
4. CONTENT QUALITY (AI-SEO readiness, BLUF compliance, entity signals)
5. COMPETITIVE POSITIONING (Gaps vs competitors, opportunities)

For each area:
- Current state score (0-100)
- Key findings (2-3 bullet points)
- Priority recommendations
- Estimated impact (High/Medium/Low)

Format as executive summary suitable for business owners.',
    ARRAY['business_name', 'industry', 'location', 'website_data', 'local_seo_data', 'reputation_data', 'competitor_data'],
    'claude-sonnet-4-20250514',
    4000,
    0.7,
    ARRAY['revflow'],
    TRUE
);

-- ============================================================================
-- META-PROMPTS (Prompt Generation)
-- ============================================================================

INSERT INTO prompt_templates (
    prompt_id, prompt_type, name, description, category,
    system_prompt, user_prompt_template,
    required_variables, preferred_model, max_tokens, temperature,
    applies_to_modules, is_active
) VALUES
(
    'META-001',
    'meta',
    'Prompt Generator',
    'Generates new prompts based on requirements (Rank Expand Academy methodology)',
    'Meta-Prompting',
    'You are a prompt engineering expert specializing in the Rank Expand Academy methodology.',
    'Create a new prompt template for the following use case:

USE CASE: {use_case_description}
OUTPUT TYPE: {output_type}
TARGET AUDIENCE: {target_audience}
KEY REQUIREMENTS: {requirements}

The prompt should follow Rank Expand Academy principles:
1. Multi-layer structure (Base + Context + Structure + Component)
2. Clear, actionable instructions
3. Example-driven where applicable
4. Built-in quality controls

Provide:
1. System prompt (sets role and constraints)
2. User prompt template (with {variable} placeholders)
3. Required variables list
4. Example input/output pair

Format as JSON-structured prompt template.',
    ARRAY['use_case_description', 'output_type', 'target_audience', 'requirements'],
    'claude-sonnet-4-20250514',
    2000,
    0.8,
    ARRAY['prompt-lab'],
    TRUE
);

-- ============================================================================
-- VERIFICATION QUERY
-- ============================================================================

-- Count prompts by type
SELECT prompt_type, COUNT(*) as count
FROM prompt_templates
WHERE is_active = TRUE
GROUP BY prompt_type
ORDER BY prompt_type;

-- Display all prompts
SELECT prompt_id, name, prompt_type, category, applies_to_modules
FROM prompt_templates
WHERE is_active = TRUE
ORDER BY prompt_type, prompt_id;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Prompt library seeded with core prompts!';
    RAISE NOTICE 'Total prompts created: %', (SELECT COUNT(*) FROM prompt_templates WHERE is_active = TRUE);
END $$;
