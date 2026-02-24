-- ============================================================================
-- GURU INTELLIGENCE - PROMPT LIBRARY (FIXED)
-- Properly escaped SQL for all prompts
-- ============================================================================

-- Clear existing prompts first
DELETE FROM prompt_templates;

-- ============================================================================
-- BASE LAYER PROMPTS (Rank Expand Foundation)
-- ============================================================================

INSERT INTO prompt_templates (
    prompt_id, prompt_type, name, description, category,
    system_prompt, user_prompt_template,
    required_variables, optional_variables, preferred_model,
    max_tokens, temperature, applies_to_modules, is_active
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
    2000, 0.7,
    ARRAY['rr-automation', 'revflow'],
    TRUE
);

-- ============================================================================
-- REVFLOW PROMPTS (5-Stage Pipeline)
-- ============================================================================

INSERT INTO prompt_templates (
    prompt_id, prompt_type, name, description, category,
    system_prompt, user_prompt_template,
    required_variables, preferred_model, max_tokens, temperature,
    applies_to_modules, is_active
) VALUES
(
    'REVFLOW-PERPLEXITY-001',
    'analysis',
    'RevFlow - Perplexity Research Stage',
    'Initial research and question gathering using Perplexity',
    'RevFlow Pipeline',
    'You are a digital marketing research analyst using Perplexity to gather competitive intelligence.',
    $$Research the following business and compile initial intelligence:

Business: {business_name}
Industry: {industry}
Location: {location}
Website: {website_url}

Research tasks:
1. What are common customer questions in this industry?
2. Who are the top 3 local competitors?
3. What digital marketing strategies are they using?
4. What are current industry trends in {location}?

Provide a structured report with sources.$$,
    ARRAY['business_name', 'industry', 'location', 'website_url'],
    'claude-sonnet-4-20250514',
    3000, 0.7,
    ARRAY['revflow'],
    TRUE
),
(
    'REVFLOW-DATAFORSEO-001',
    'analysis',
    'RevFlow - DataForSEO Intelligence Layer',
    'Extract competitive data using DataForSEO APIs',
    'RevFlow Pipeline',
    'You are analyzing DataForSEO API results to build competitive intelligence.',
    $$Analyze the following DataForSEO data and create intelligence report:

SERP Data: {serp_data}
Keyword Data: {keyword_data}
Competitor Data: {competitor_data}

Create analysis with:
1. Current rankings and visibility
2. Keyword opportunities (search volume, difficulty, intent)
3. Competitor technical benchmarks
4. Gap analysis vs competitors
5. Priority recommendations

Format as McKinsey-style executive summary.$$,
    ARRAY['serp_data', 'keyword_data', 'competitor_data'],
    'claude-sonnet-4-20250514',
    4000, 0.7,
    ARRAY['revflow'],
    TRUE
),
(
    'REVFLOW-CHATGPT-001',
    'generation',
    'RevFlow - ChatGPT Structural Draft',
    'Generate initial assessment structure using ChatGPT',
    'RevFlow Pipeline',
    'You are creating a structured digital presence assessment report.',
    $$Create a digital presence assessment structure for:

Business: {business_name}
Industry: {industry}
Research Data: {research_summary}

Create outline with:
- Executive Summary
- Module A: Technical Foundation
- Module B: Local SEO Presence  
- Module C: Reputation & Trust
- Module D: Content Quality
- Module E: Competitive Positioning

For each module, include: Current State, Key Findings, Recommendations, Priority Level$$,
    ARRAY['business_name', 'industry', 'research_summary'],
    'gpt-4',
    3000, 0.7,
    ARRAY['revflow'],
    TRUE
),
(
    'REVFLOW-GEMINI-001',
    'enhancement',
    'RevFlow - Gemini Local Context',
    'Add local market intelligence using Gemini',
    'RevFlow Pipeline',
    'You are enhancing assessment with local market context and Google Maps data.',
    $$Enhance this assessment with local context:

Assessment Draft: {draft_assessment}
Location: {location}
GBP Data: {gbp_data}
Local Competitors: {local_competitors}

Add local intelligence:
1. Neighborhood-specific opportunities
2. Local search behavior patterns
3. Geographic service gaps
4. Local landmark references
5. Regional terminology

Integrate naturally into existing assessment structure.$$,
    ARRAY['draft_assessment', 'location', 'gbp_data', 'local_competitors'],
    'gemini-pro',
    3000, 0.7,
    ARRAY['revflow'],
    TRUE
),
(
    'REVFLOW-CLAUDE-001',
    'enhancement',
    'RevFlow - Claude Final Polish',
    'Final quality enhancement and executive narrative',
    'RevFlow Pipeline',
    'You are a senior marketing consultant providing final polish to client assessment.',
    $$Review and enhance this digital presence assessment:

Current Assessment: {assessment_draft}
Client: {business_name}
Industry: {industry}

Enhancement requirements:
1. Ensure executive tone (McKinsey-quality)
2. Add actionable next steps with timelines
3. Quantify impact where possible
4. Remove jargon, add clarity
5. Strengthen business case for recommendations

Maintain all data points, enhance narrative and strategic framing.$$,
    ARRAY['assessment_draft', 'business_name', 'industry'],
    'claude-sonnet-4-20250514',
    4000, 0.7,
    ARRAY['revflow'],
    TRUE
);

-- ============================================================================
-- R&R AUTOMATION - PAGE TYPE PROMPTS
-- ============================================================================

INSERT INTO prompt_templates (
    prompt_id, prompt_type, name, description, category,
    user_prompt_template, required_variables, preferred_model,
    max_tokens, temperature, applies_to_modules, applies_to_page_types, is_active
) VALUES
(
    'GEN-HOMEPAGE-001',
    'generation',
    'Homepage Content Generator',
    'Comprehensive homepage content for local service businesses',
    'Page Generation',
    $$Generate homepage content following these requirements:

Company: {company_name}
Primary Service: {primary_service}
Service Area: {service_area}
Years in Business: {years_established}
License: {license_number}
Phone: {phone}

WORD COUNT: 1,200-2,000 words

STRUCTURE:
1. Leader (3 lines) - Compelling opening with company, service, location
2. Introduction (≤200 words) - BLUF style answering "What does this company do?"
3. Services Overview - Main services with brief descriptions
4. Why Choose Us - 3-5 differentiators
5. Service Area - Cities and neighborhoods served
6. Company Background - Brief history, credentials
7. Call to Action - Phone number, emergency services

CRITICAL REQUIREMENTS:
- First sentence must answer: "What does {company_name} do?"
- Include phone number: {phone}
- Mention at least 5 city names from service area
- Include license number
- Use question-format H2 headers$$,
    ARRAY['company_name', 'primary_service', 'service_area', 'years_established', 'license_number', 'phone'],
    'claude-sonnet-4-20250514',
    3000, 0.7,
    ARRAY['rr-automation'],
    ARRAY['homepage'],
    TRUE
),
(
    'GEN-SERVICE-001',
    'generation',
    'Service Page Content Generator',
    'Focused service page content with BLUF and AI-SEO best practices',
    'Page Generation',
    $$Generate service page content:

Company: {company_name}
Service: {service_name}
Location: {location}
Price Range: {price_range}
Industry: {industry}

WORD COUNT: 800-1,200 words

STRUCTURE:
1. Leader (3 lines) - Direct answer to "What is {service_name}?"
2. H2: "How Much Does {service_name} Cost in {location}?"
   - BLUF answer (40-60 words)
   - Include price range
   - Factors affecting cost
3. H2: "What is {service_name}?"
   - Technical explanation
   - When needed
   - Common scenarios
4. H2: "Why Choose {company_name} for {service_name}?"
   - Credentials and experience
   - Service guarantees
   - Response time
5. FAQ Section (3-5 questions)

CRITICAL REQUIREMENTS:
- EVERY H2 must be a question
- First sentence after H2 must directly answer (BLUF)
- Include 3+ city/neighborhood mentions
- Include phone number and license
- Use Partner voice (directive, confident)
- Include specific numbers: pricing, timeframes, experience$$,
    ARRAY['company_name', 'service_name', 'location', 'price_range', 'industry'],
    'claude-sonnet-4-20250514',
    2500, 0.7,
    ARRAY['rr-automation'],
    ARRAY['service'],
    TRUE
),
(
    'GEN-LOCATION-001',
    'generation',
    'Location Page Content Generator',
    'Location-specific content with local proof signals',
    'Page Generation',
    $$Generate location-specific page with deep local knowledge:

Company: {company_name}
Service: {primary_service}
Target City: {city}
Neighborhoods: {neighborhoods}
Local Landmarks: {landmarks}

WORD COUNT: ~800 words

LOCAL PROOF SIGNALS REQUIRED:
- Mention {city} at least 8 times
- Include 3+ specific neighborhoods: {neighborhoods}
- Reference 2+ local landmarks: {landmarks}
- Mention nearby highways/major roads
- Include service radius in miles

STRUCTURE:
1. Leader (3 lines) - "{primary_service} in {city}"
2. H2: "Professional {primary_service} Services in {city}"
   - BLUF: Service availability, response time, coverage
3. H2: "Areas We Serve in {city}"
   - List neighborhoods with context
   - Mention landmarks near each area
4. H2: "Why {city} Residents Choose {company_name}"
   - Local experience (years serving area)
   - Knowledge of local codes/regulations
   - Familiarity with common local issues
5. H2: "Schedule {primary_service} in {city} Today"
   - Call to action with phone

HIGH-RESOLUTION TEST:
Could a competitor NOT use this by just changing the name?
- Specific street names, subdivisions, local references
- Local terminology
- Local weather/climate factors if relevant$$,
    ARRAY['company_name', 'primary_service', 'city', 'neighborhoods', 'landmarks'],
    'claude-sonnet-4-20250514',
    2000, 0.7,
    ARRAY['rr-automation'],
    ARRAY['location', 'service_area'],
    TRUE
),
(
    'GEN-EMERGENCY-001',
    'generation',
    'Emergency Page Content Generator',
    'Emergency service page with urgent tone',
    'Page Generation',
    $$Generate emergency service page with urgent, action-oriented content:

Company: {company_name}
Emergency Service: {emergency_service}
Location: {location}
Phone: {phone}
Response Time: {response_time}

WORD COUNT: 600-800 words

TONE: Partner voice - directive, urgent, confident

STRUCTURE:
1. Leader - Immediate action call-out
2. H2: "24/7 Emergency {emergency_service} in {location}"
   - BLUF: Available now, response time, coverage
3. H2: "When to Call for Emergency {emergency_service}"
   - Warning signs (3-5 urgent scenarios)
4. H2: "Our Emergency Response Process"
   - Step-by-step (numbered list)
5. Large CTA: "Call Now: {phone}"

CRITICAL REQUIREMENTS:
- Phone number appears 3+ times
- Response time mentioned in first paragraph
- Action verbs: "Call now", "Don''t wait", "Immediate"
- Short paragraphs (2-3 sentences)
- Emphasize 24/7 availability$$,
    ARRAY['company_name', 'emergency_service', 'location', 'phone', 'response_time'],
    'claude-sonnet-4-20250514',
    1500, 0.8,
    ARRAY['rr-automation'],
    ARRAY['emergency'],
    TRUE
);

-- ============================================================================
-- ENHANCEMENT PROMPTS (AI-SEO Layers)
-- ============================================================================

INSERT INTO prompt_templates (
    prompt_id, prompt_type, name, description, category,
    user_prompt_template, required_variables, preferred_model,
    max_tokens, temperature, applies_to_modules, is_active
) VALUES
(
    'ENH-BLUF-001',
    'enhancement',
    'BLUF Enforcement',
    'Ensures content follows Bottom Line Up Front structure',
    'AI-SEO Enhancement',
    $$Review this content and ensure EVERY H2 header is followed by a 40-60 word direct answer in the first sentence.

CONTENT:
{content}

RULES:
1. First sentence after H2 must answer the question directly
2. No throat-clearing phrases: "When it comes to...", "Many people wonder...", "If you''re looking for..."
3. Answer must be 40-60 words
4. Include specific details: numbers, locations, timeframes

Return the content with BLUF structure applied.$$,
    ARRAY['content'],
    'claude-sonnet-4-20250514',
    3000, 0.5,
    ARRAY['rr-automation'],
    TRUE
),
(
    'ENH-ENTITY-001',
    'enhancement',
    'Entity Density Optimization',
    'Adds or strengthens entity signals for AI visibility',
    'AI-SEO Enhancement',
    $$Enhance this content with strong entity signals:

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

Return enhanced content with entity signals.$$,
    ARRAY['content', 'company_name', 'location', 'service', 'license_number'],
    'claude-sonnet-4-20250514',
    3000, 0.6,
    ARRAY['rr-automation'],
    TRUE
),
(
    'ENH-LOCAL-001',
    'enhancement',
    'Local Proof Injection',
    'Adds specific local references and proof signals',
    'AI-SEO Enhancement',
    $$Enhance this content with local proof signals:

CONTENT:
{content}

LOCATION: {location}
NEIGHBORHOODS: {neighborhoods}
LANDMARKS: {landmarks}

ADD LOCAL PROOF:
1. Replace generic "the area" with specific neighborhood names
2. Add 2-3 landmark references
3. Include local street names or major intersections
4. Add local terminology (e.g., "The Valley" for Phoenix)
5. Reference local weather/climate if relevant to service

MAINTAIN:
- Original structure and flow
- All existing information
- Professional tone

Return enhanced content with stronger local signals.$$,
    ARRAY['content', 'location', 'neighborhoods', 'landmarks'],
    'claude-sonnet-4-20250514',
    2500, 0.6,
    ARRAY['rr-automation'],
    TRUE
);

-- ============================================================================
-- VALIDATION PROMPTS (Tier 3 LLM Checks)
-- ============================================================================

INSERT INTO prompt_templates (
    prompt_id, prompt_type, name, description, category,
    system_prompt, user_prompt_template, required_variables,
    preferred_model, max_tokens, temperature, applies_to_modules, is_active
) VALUES
(
    'VAL-TIER3-001',
    'validation',
    'Batched Tier 3 Validation',
    'Multi-rule LLM validation in single API call',
    'Validation',
    'You are a content quality auditor. Assess content against multiple quality rules strictly but fairly.',
    $$Analyze this content against {rule_count} quality rules.

CONTENT TO ASSESS:
---
{content}
---

RULES TO CHECK:
{rules_list}

For each rule, provide your assessment in this JSON format:
{
    "assessments": [
        {"rule_id": "BLUF-001", "passed": true, "reason": "First sentence directly answers the question"},
        {"rule_id": "TONE-003", "passed": false, "reason": "Tone is too casual for professional service page"}
    ]
}

Be strict but fair. Only mark as failed if clearly violated. Respond ONLY with valid JSON.$$,
    ARRAY['content', 'rule_count', 'rules_list'],
    'claude-sonnet-4-20250514',
    1000, 0.3,
    ARRAY['rr-automation', 'revflow'],
    TRUE
),
(
    'VAL-TONE-001',
    'validation',
    'Voice Modality Validator',
    'Validates content matches appropriate voice',
    'Validation',
    'You are a tone and voice expert for home services content.',
    $$Assess if this content uses the appropriate voice modality.

CONTENT:
{content}

PAGE TYPE: {page_type}
EXPECTED VOICE: {expected_voice}

VOICE DEFINITIONS:
- Partner (Emergency/Transactional): Directive, confident, action-oriented
- Professor (Technical/Legal): Precise, citation-heavy, neutral
- Peer (Comparison/Pain-driven): Empathetic, validating

Does this content match the expected {expected_voice} voice?
- YES or NO
- Brief explanation
- Quote specific phrases that support your assessment

Respond in JSON: {"passed": true/false, "reason": "...", "examples": []}$$,
    ARRAY['content', 'page_type', 'expected_voice'],
    'claude-sonnet-4-20250514',
    500, 0.3,
    ARRAY['rr-automation'],
    TRUE
);

-- Verify prompt count
SELECT COUNT(*) as total_prompts FROM prompt_templates WHERE is_active = TRUE;

