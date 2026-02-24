#!/usr/bin/env python3
"""
Guru Intelligence - Multi-Tiered Assessment Engine
Cost-effective content validation using Tier 1/2/3 architecture

Tier 1: Regex/Deterministic (Free, ~100ms)
Tier 2: NLP/spaCy (Free, ~500ms) 
Tier 3: LLM/Claude (Paid, ~3s)

Usage:
    from multi_tiered_assessor import MultiTieredAssessor
    
    assessor = MultiTieredAssessor()
    result = assessor.assess(content, page_type='service', industry='plumbing')
"""

import re
import time
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import anthropic
import psycopg2

# Optional NLP dependencies
try:
    import spacy
    import textstat
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    print("⚠️  spaCy not available - Tier 2 validation disabled")

# Database configuration
# DB_CONFIG = {
#     'host': 'localhost',
#     'port': 5432,
#     'database': 'knowledge_graph_db',
#     'user': 'knowledge_admin',
#     'password': 'ZYsCjjdy2dzIwrKKM4TY7Vc0Z8ryoR1V'
# }

@dataclass
class Violation:
    """A single rule violation"""
    rule_id: str
    rule_name: str
    tier: int
    severity: str  # 'critical', 'major', 'minor'
    message: str
    fix_suggestion: Optional[str] = None
    auto_fixable: bool = False

@dataclass
class TierResult:
    """Results from a single tier"""
    tier: int
    rules_checked: int
    rules_passed: int
    violations: List[Violation] = field(default_factory=list)
    processing_time_ms: int = 0
    skipped: bool = False
    skip_reason: Optional[str] = None

@dataclass
class AssessmentResult:
    """Complete assessment result"""
    overall_score: int
    passed: bool
    tiers_run: List[int]
    tier_results: Dict[int, TierResult]
    violations: List[Violation]
    passed_rules: List[str]
    auto_fixes: List[Dict]
    recommendations: List[str]
    
    # Cost tracking
    api_cost: float = 0.0
    tokens_used: int = 0
    total_processing_time_ms: int = 0
    
    # Metadata
    content_length: int = 0
    page_type: str = ""
    industry: str = ""
    assessed_at: str = ""

class Tier1Validator:
    """Tier 1: Deterministic/Regex validation ($0.00)"""
    
    # City database for LOCAL-001 checks
    CITIES = [
        'Phoenix', 'Scottsdale', 'Tempe', 'Mesa', 'Gilbert', 'Chandler', 
        'Glendale', 'Peoria', 'Surprise', 'Avondale', 'Goodyear', 'Buckeye',
        'Allen', 'Plano', 'Frisco', 'McKinney', 'Richardson', 'Dallas',
        'Los Angeles', 'San Diego', 'San Francisco', 'San Jose', 'Oakland',
        'Houston', 'Austin', 'San Antonio', 'Fort Worth', 'Arlington',
        'New York', 'Brooklyn', 'Queens', 'Manhattan', 'Bronx',
        'Chicago', 'Seattle', 'Portland', 'Denver', 'Atlanta', 'Miami',
        'Las Vegas', 'Reno', 'Tucson', 'Albuquerque', 'Salt Lake City',
        'Nashville', 'Memphis', 'Louisville', 'Indianapolis', 'Columbus',
        'Philadelphia', 'Pittsburgh', 'Boston', 'Baltimore', 'Charlotte',
        # Add more as needed
    ]
    
    VALIDATION_FUNCTIONS = {
        'word_count_min': lambda content, min_val: len(content.split()) >= int(min_val),
        'word_count_max': lambda content, max_val: len(content.split()) <= int(max_val),
        'word_count_range': lambda content, min_val, max_val: int(min_val) <= len(content.split()) <= int(max_val),
        'has_phone': lambda content, _: bool(re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', content)),
        'has_price': lambda content, _: bool(re.search(r'\$\d+', content)),
        'has_license': lambda content, _: bool(re.search(r'(?:ROC|license|lic|#)[-#]?\s*\d+', content, re.I)),
        'has_cities': lambda content, min_count: len(Tier1Validator._find_cities(content)) >= int(min_count),
        'has_h2': lambda content, min_count: content.count('## ') >= int(min_count),
        'has_bullets': lambda content, min_count: len(re.findall(r'^\s*[-*]\s', content, re.M)) >= int(min_count),
        'contains_keyword': lambda content, keyword: keyword.lower() in content.lower(),
        'no_phrase': lambda content, phrase: phrase.lower() not in content.lower(),
        'has_numbers': lambda content, min_count: len(re.findall(r'\b\d+\b', content)) >= int(min_count),
    }
    
    @staticmethod
    def _find_cities(content: str) -> List[str]:
        """Find city mentions in content"""
        found_cities = []
        for city in Tier1Validator.CITIES:
            if re.search(r'\b' + re.escape(city) + r'\b', content, re.I):
                found_cities.append(city)
        return found_cities
    
    def validate(self, content: str, rules: List[Dict]) -> TierResult:
        """Run all Tier 1 validations"""
        start_time = time.time()
        violations = []
        passed_count = 0
        
        for rule in rules:
            rule_id = rule['rule_id']
            rule_name = rule['rule_name']
            validation_pattern = rule['validation_pattern']
            enforcement_level = rule['enforcement_level']
            
            if not validation_pattern:
                continue
            
            # Parse validation pattern
            parts = validation_pattern.split(':')
            func_name = parts[0]
            func_args = parts[1:] if len(parts) > 1 else []
            
            if func_name in self.VALIDATION_FUNCTIONS:
                try:
                    func = self.VALIDATION_FUNCTIONS[func_name]
                    passed = func(content, *func_args)
                    
                    if passed:
                        passed_count += 1
                    else:
                        severity = 'critical' if enforcement_level == 'required' else 'minor'
                        violations.append(Violation(
                            rule_id=rule_id,
                            rule_name=rule_name,
                            tier=1,
                            severity=severity,
                            message=rule['rule_description'],
                            auto_fixable=rule.get('auto_fixable', False)
                        ))
                except Exception as e:
                    print(f"⚠️  Tier 1 validation error for {rule_id}: {e}")
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return TierResult(
            tier=1,
            rules_checked=len(rules),
            rules_passed=passed_count,
            violations=violations,
            processing_time_ms=processing_time
        )

class Tier2Validator:
    """Tier 2: NLP/spaCy validation ($0.00)"""
    
    def __init__(self):
        self.nlp = None
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load('en_core_web_sm')
            except:
                print("⚠️  spaCy model not loaded - run: python -m spacy download en_core_web_sm")
    
    def validate(self, content: str, rules: List[Dict]) -> TierResult:
        """Run all Tier 2 validations"""
        start_time = time.time()
        violations = []
        passed_count = 0
        
        if not self.nlp:
            return TierResult(
                tier=2,
                rules_checked=0,
                rules_passed=0,
                skipped=True,
                skip_reason="spaCy not available"
            )
        
        # Parse content with spaCy
        doc = self.nlp(content[:100000])  # Limit for performance
        
        for rule in rules:
            rule_id = rule['rule_id']
            rule_name = rule['rule_name']
            validation_type = rule['validation_type']
            enforcement_level = rule['enforcement_level']
            
            passed = True
            
            # Implement Tier 2 checks
            if 'passive voice' in rule['rule_description'].lower():
                # Check for passive voice in first paragraph
                first_para = content.split('\n\n')[0] if '\n\n' in content else content[:500]
                passive_count = sum(1 for token in self.nlp(first_para) if token.dep_ == 'auxpass')
                passed = passive_count == 0
            
            elif 'readability' in rule['rule_description'].lower():
                # Check Flesch-Kincaid score
                try:
                    fk_score = textstat.flesch_kincaid_grade(content)
                    passed = fk_score <= 12  # Grade 12 or below
                except:
                    passed = True  # Skip if textstat fails
            
            elif 'first sentence' in rule['rule_description'].lower():
                # Check first sentence length
                sentences = list(doc.sents)
                if sentences:
                    first_sent = sentences[0]
                    word_count = len([token for token in first_sent if not token.is_punct])
                    passed = word_count <= 20
            
            if passed:
                passed_count += 1
            else:
                severity = 'major' if enforcement_level == 'required' else 'minor'
                violations.append(Violation(
                    rule_id=rule_id,
                    rule_name=rule_name,
                    tier=2,
                    severity=severity,
                    message=rule['rule_description']
                ))
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return TierResult(
            tier=2,
            rules_checked=len(rules),
            rules_passed=passed_count,
            violations=violations,
            processing_time_ms=processing_time
        )

class Tier3Validator:
    """Tier 3: LLM/Claude validation (~$0.01 per batch)"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            self.client = anthropic.Anthropic(api_key=api_key)
        self.total_cost = 0.0
        self.total_tokens = 0
    
    def validate_batched(self, content: str, rules: List[Dict], max_rules: int = 10) -> TierResult:
        """Run batched LLM validation - ONE API call for multiple rules"""
        start_time = time.time()
        violations = []
        passed_count = 0
        
        if not self.client:
            return TierResult(
                tier=3,
                rules_checked=0,
                rules_passed=0,
                skipped=True,
                skip_reason="Claude API key not configured"
            )
        
        # Limit to max_rules to control cost
        rules_to_check = rules[:max_rules]
        
        # Build batched prompt
        rules_text = "\n".join([
            f"{i+1}. [{r['rule_id']}] {r['rule_name']}: {r['rule_description']}"
            for i, r in enumerate(rules_to_check)
        ])
        
        prompt = f"""Analyze this content against {len(rules_to_check)} quality rules.

CONTENT TO ASSESS:
---
{content[:5000]}  
---

RULES TO CHECK:
{rules_text}

For each rule, provide your assessment in this JSON format:
{{
    "assessments": [
        {{"rule_id": "BLUF-001", "passed": true, "reason": "First sentence directly answers the question"}},
        {{"rule_id": "TONE-003", "passed": false, "reason": "Tone is too casual for professional service page"}}
    ]
}}

Be strict but fair. Only mark as failed if clearly violated. Respond ONLY with valid JSON."""

        try:
            # Call Claude API
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse response
            response_text = response.content[0].text
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group())
                assessments = result_data.get('assessments', [])
                
                # Map results back to rules
                for assessment in assessments:
                    rule_id = assessment.get('rule_id')
                    passed = assessment.get('passed', False)
                    reason = assessment.get('reason', '')
                    
                    # Find matching rule
                    matching_rule = next((r for r in rules_to_check if r['rule_id'] == rule_id), None)
                    
                    if matching_rule:
                        if passed:
                            passed_count += 1
                        else:
                            severity = 'major' if matching_rule['enforcement_level'] == 'required' else 'minor'
                            violations.append(Violation(
                                rule_id=rule_id,
                                rule_name=matching_rule['rule_name'],
                                tier=3,
                                severity=severity,
                                message=reason
                            ))
            
            # Track cost (approximate)
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            self.total_tokens = input_tokens + output_tokens
            
            # Claude Sonnet 4 pricing (approximate)
            self.total_cost = (input_tokens / 1_000_000 * 3.00) + (output_tokens / 1_000_000 * 15.00)
            
        except Exception as e:
            print(f"⚠️  Tier 3 LLM validation error: {e}")
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return TierResult(
            tier=3,
            rules_checked=len(rules_to_check),
            rules_passed=passed_count,
            violations=violations,
            processing_time_ms=processing_time
        )

class MultiTieredAssessor:
    """Main assessment orchestrator with short-circuit logic"""
    
    def __init__(self, claude_api_key: Optional[str] = None):
        self.conn = None
        self.tier1 = Tier1Validator()
        self.tier2 = Tier2Validator()
        self.tier3 = Tier3Validator(claude_api_key)
        self._connect_db()
    
    def _connect_db(self):
        """Connect to PostgreSQL"""
        pass  # Database disabled
        # try:
        #     self.conn = psycopg2.connect(**DB_CONFIG)
        # except Exception as e:
        #     print(f"⚠️  Database connection failed: {e}")
    
    def _get_rules(self, complexity_level: int, page_type: Optional[str] = None, 
                   industry: Optional[str] = None) -> List[Dict]:
        """Fetch rules from database by tier and filters"""
        if not self.conn:
            return []
        
        cursor = self.conn.cursor()
        
        query = """
            SELECT rule_id, rule_name, rule_category, rule_description,
                   complexity_level, validation_type, validation_pattern,
                   prompt_template, enforcement_level, priority_score,
                   auto_fixable, applies_to_modules, applies_to_page_types
            FROM extracted_rules
            WHERE complexity_level = %s
              AND is_active = TRUE
        """
        params = [complexity_level]
        
        if page_type:
            query += " AND (%s = ANY(applies_to_page_types) OR applies_to_page_types IS NULL)"
            params.append(page_type)
        
        query += " ORDER BY priority_score DESC"
        
        cursor.execute(query, params)
        
        columns = [desc[0] for desc in cursor.description]
        rules = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        cursor.close()
        return rules
    
    def assess(self, content: str, page_type: str = 'service', industry: str = 'general',
               options: Optional[Dict] = None) -> AssessmentResult:
        """
        Main assessment method with short-circuit logic
        
        Args:
            content: Content to assess
            page_type: Page type (service, location, homepage, etc.)
            industry: Industry (plumbing, hvac, legal, etc.)
            options: Configuration options
                - run_tier3: Enable LLM checks (default: True)
                - short_circuit: Stop on critical failures (default: True)
                - max_tier3_rules: Batch limit for LLM (default: 10)
        """
        start_time = time.time()
        
        options = options or {}
        run_tier3 = options.get('run_tier3', True)
        short_circuit = options.get('short_circuit', True)
        max_tier3_rules = options.get('max_tier3_rules', 10)
        
        violations = []
        tier_results = {}
        tiers_run = []
        
        # ============== TIER 1: Deterministic ==============
        tier1_rules = self._get_rules(1, page_type, industry)
        tier1_result = self.tier1.validate(content, tier1_rules)
        tier_results[1] = tier1_result
        tiers_run.append(1)
        violations.extend(tier1_result.violations)
        
        # SHORT-CIRCUIT: Critical Tier 1 failures
        critical_violations = [v for v in tier1_result.violations if v.severity == 'critical']
        if short_circuit and len(critical_violations) >= 3:
            return self._build_result(
                content, page_type, industry, tiers_run, tier_results, violations,
                skipped_tiers=[2, 3],
                skip_reason="Critical Tier 1 failures - fix before proceeding"
            )
        
        # ============== TIER 2: NLP ==============
        tier2_rules = self._get_rules(2, page_type, industry)
        if tier2_rules:
            tier2_result = self.tier2.validate(content, tier2_rules)
            tier_results[2] = tier2_result
            tiers_run.append(2)
            violations.extend(tier2_result.violations)
            
            # SHORT-CIRCUIT: High Tier 2 failure rate
            if short_circuit and tier2_result.rules_checked > 0:
                failure_rate = 1 - (tier2_result.rules_passed / tier2_result.rules_checked)
                if failure_rate > 0.5:
                    return self._build_result(
                        content, page_type, industry, tiers_run, tier_results, violations,
                        skipped_tiers=[3],
                        skip_reason=f"High Tier 2 failure rate ({failure_rate:.0%}) - fix before LLM validation"
                    )
        
        # ============== TIER 3: LLM ==============
        if run_tier3:
            tier3_rules = self._get_rules(3, page_type, industry)
            if tier3_rules:
                tier3_result = self.tier3.validate_batched(content, tier3_rules, max_tier3_rules)
                tier_results[3] = tier3_result
                tiers_run.append(3)
                violations.extend(tier3_result.violations)
        
        return self._build_result(content, page_type, industry, tiers_run, tier_results, violations)
    
    def _build_result(self, content: str, page_type: str, industry: str,
                      tiers_run: List[int], tier_results: Dict[int, TierResult],
                      violations: List[Violation], skipped_tiers: Optional[List[int]] = None,
                      skip_reason: Optional[str] = None) -> AssessmentResult:
        """Build final assessment result"""
        
        # Calculate overall score
        total_rules = sum(tr.rules_checked for tr in tier_results.values())
        total_passed = sum(tr.rules_passed for tr in tier_results.values())
        
        overall_score = int((total_passed / total_rules * 100)) if total_rules > 0 else 0
        passed = overall_score >= 70
        
        # Extract passed rules
        passed_rules = []
        for tier, result in tier_results.items():
            passed_rules.extend([f"Tier {tier}"] * result.rules_passed)
        
        # Generate recommendations
        recommendations = []
        if skipped_tiers:
            recommendations.append(f"Fix {len([v for v in violations if v.severity == 'critical'])} critical issues before proceeding")
        
        critical_count = len([v for v in violations if v.severity == 'critical'])
        major_count = len([v for v in violations if v.severity == 'major'])
        
        if critical_count > 0:
            recommendations.append(f"Address {critical_count} critical violations immediately")
        if major_count > 0:
            recommendations.append(f"Review {major_count} major quality issues")
        
        # Auto-fixes
        auto_fixes = [
            {'rule_id': v.rule_id, 'suggestion': v.fix_suggestion}
            for v in violations if v.auto_fixable and v.fix_suggestion
        ]
        
        # Cost tracking
        api_cost = self.tier3.total_cost
        tokens_used = self.tier3.total_tokens
        
        # Total processing time
        total_processing_time = sum(tr.processing_time_ms for tr in tier_results.values())
        
        return AssessmentResult(
            overall_score=overall_score,
            passed=passed,
            tiers_run=tiers_run,
            tier_results={k: v for k, v in tier_results.items()},
            violations=violations,
            passed_rules=passed_rules,
            auto_fixes=auto_fixes,
            recommendations=recommendations,
            api_cost=api_cost,
            tokens_used=tokens_used,
            total_processing_time_ms=total_processing_time,
            content_length=len(content),
            page_type=page_type,
            industry=industry,
            assessed_at=datetime.now().isoformat()
        )
    
    def to_dict(self, result: AssessmentResult) -> Dict:
        """Convert assessment result to dictionary"""
        return {
            'overall_score': result.overall_score,
            'passed': result.passed,
            'tiers_run': result.tiers_run,
            'tier_results': {
                tier: {
                    'rules_checked': tr.rules_checked,
                    'rules_passed': tr.rules_passed,
                    'violations': [asdict(v) for v in tr.violations],
                    'processing_time_ms': tr.processing_time_ms,
                    'skipped': tr.skipped,
                    'skip_reason': tr.skip_reason
                }
                for tier, tr in result.tier_results.items()
            },
            'violations': [asdict(v) for v in result.violations],
            'passed_rules_count': len(result.passed_rules),
            'auto_fixes': result.auto_fixes,
            'recommendations': result.recommendations,
            'api_cost': result.api_cost,
            'tokens_used': result.tokens_used,
            'total_processing_time_ms': result.total_processing_time_ms,
            'content_length': result.content_length,
            'page_type': result.page_type,
            'industry': result.industry,
            'assessed_at': result.assessed_at
        }

# Example usage
if __name__ == "__main__":
    # Test content
    test_content = """
    Phoenix plumbers charge between $150-$450 for drain cleaning services. 
    ABC Plumbing has served the Phoenix metro area since 1987, completing over 
    15,000 emergency repairs for homeowners across Scottsdale, Tempe, Mesa, 
    and Gilbert. Our licensed contractor team (ROC-284756) responds within 
    60 minutes for emergency calls. We service all major brands including 
    American Standard, Kohler, and Moen. Call (602) 555-1234 for same-day service.
    
    ## How Much Does Drain Cleaning Cost?
    
    Professional drain cleaning in Phoenix typically costs $150-$450 depending on 
    the severity and location of the clog. Our certified technicians provide 
    upfront pricing with no hidden fees.
    """
    
    assessor = MultiTieredAssessor()
    result = assessor.assess(test_content, page_type='service', industry='plumbing')
    
    print(json.dumps(assessor.to_dict(result), indent=2))
