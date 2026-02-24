#!/usr/bin/env python3
"""
Guru Intelligence - Rule Categorization Engine
Automatically categorizes all 359 rules by complexity level (Tier 1/2/3)

Usage:
    python categorize_rules.py

Requirements:
    - PostgreSQL connection to knowledge_graph_db
    - extracted_rules table with all 359 rules
"""

import re
import psycopg2
from typing import Dict, List, Tuple
from dataclasses import dataclass
import json

# Database configuration
DB_CONFIG = {
    'host': '172.23.0.2',
    'port': 5432,
    'database': 'knowledge_graph_db',
    'user': 'knowledge_admin',
    'password': 'ZYsCjjdy2dzIwrKKM4TY7Vc0Z8ryoR1V'
}

@dataclass
class RuleCategorizationResult:
    """Result of categorizing a single rule"""
    rule_id: str
    complexity_level: int
    validation_type: str
    validation_pattern: str
    confidence: float
    reasoning: str

class RuleCategorizer:
    """Categorizes rules into Tier 1 (regex), Tier 2 (NLP), or Tier 3 (LLM)"""
    
    # Keywords that indicate structural/quantitative checks (Tier 1)
    TIER1_KEYWORDS = [
        r'\b(?:must|should|require[sd]?|include[sd]?|contain[sd]?)\b',
        r'\b(?:minimum|maximum|at least|no more than|exactly|between)\b',
        r'\b\d+\s*(?:words?|sentences?|characters?|bullet|paragraph|line)\b',
        r'\b(?:phone|email|address|zip|license|number|code)\b',
        r'\b(?:format|pattern|structure)\b',
        r'\bURL\b',
        r'\b(?:price|cost|dollar|\$|range)\b',
        r'\b(?:H1|H2|H3|header|heading|title)\b',
        r'\b(?:bold|italic|list|bullet)\b'
    ]
    
    # Keywords that indicate NLP/grammar checks (Tier 2)
    TIER2_KEYWORDS = [
        r'\b(?:passive voice|active voice|verb tense)\b',
        r'\b(?:sentence structure|paragraph structure)\b',
        r'\b(?:readability|Flesch|grade level)\b',
        r'\b(?:grammar|spelling|punctuation)\b',
        r'\b(?:first sentence|opening|begins with)\b',
        r'\b(?:entity recognition|named entity)\b'
    ]
    
    # Keywords that indicate semantic/qualitative checks (Tier 3)
    TIER3_KEYWORDS = [
        r'\b(?:tone|voice|style|feeling|sound[s]?)\b',
        r'\b(?:persuasive|engaging|compelling|natural)\b',
        r'\b(?:appropriate|suitable|fits?|match(?:es)?)\b',
        r'\b(?:context|meaning|intent|purpose)\b',
        r'\b(?:answer[s]? the question|addresses|responds to)\b',
        r'\b(?:professional|empathetic|authoritative)\b',
        r'\b(?:trustworthy|credible|authentic)\b',
        r'\b(?:unique|original|distinctive)\b'
    ]
    
    def __init__(self):
        self.conn = None
        self.tier_counts = {1: 0, 2: 0, 3: 0}
        
    def connect(self):
        """Connect to PostgreSQL"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            print("✅ Connected to knowledge_graph_db")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("✅ Database connection closed")
    
    def fetch_all_rules(self) -> List[Tuple]:
        """Fetch all rules from database"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT rule_id, rule_name, rule_category, rule_description, 
                   enforcement_level, priority_score
            FROM extracted_rules
            ORDER BY rule_id
        """)
        rules = cursor.fetchall()
        cursor.close()
        print(f"📊 Fetched {len(rules)} rules from database")
        return rules
    
    def categorize_rule(self, rule_id: str, rule_name: str, rule_description: str) -> RuleCategorizationResult:
        """
        Categorize a single rule by analyzing its description
        
        Returns complexity_level (1, 2, or 3) and validation details
        """
        desc_lower = rule_description.lower()
        
        # Count keyword matches for each tier
        tier1_matches = sum(1 for pattern in self.TIER1_KEYWORDS if re.search(pattern, desc_lower, re.I))
        tier2_matches = sum(1 for pattern in self.TIER2_KEYWORDS if re.search(pattern, desc_lower, re.I))
        tier3_matches = sum(1 for pattern in self.TIER3_KEYWORDS if re.search(pattern, desc_lower, re.I))
        
        total_matches = tier1_matches + tier2_matches + tier3_matches
        
        # Determine tier based on keyword matches
        if total_matches == 0:
            # No clear indicators - default to Tier 1 for safety
            complexity_level = 1
            validation_type = 'regex'
            confidence = 0.3
            reasoning = "No strong indicators - defaulting to Tier 1"
        elif tier1_matches > tier2_matches and tier1_matches > tier3_matches:
            complexity_level = 1
            validation_type = self._infer_validation_type_tier1(rule_description)
            confidence = tier1_matches / total_matches
            reasoning = f"Structural indicators: {tier1_matches} Tier 1 keywords"
        elif tier2_matches > tier1_matches and tier2_matches > tier3_matches:
            complexity_level = 2
            validation_type = 'spacy'
            confidence = tier2_matches / total_matches
            reasoning = f"NLP indicators: {tier2_matches} Tier 2 keywords"
        else:
            complexity_level = 3
            validation_type = 'llm'
            confidence = tier3_matches / total_matches
            reasoning = f"Semantic indicators: {tier3_matches} Tier 3 keywords"
        
        # Generate validation pattern for Tier 1 rules
        validation_pattern = ""
        if complexity_level == 1:
            validation_pattern = self._generate_tier1_pattern(rule_id, rule_description)
        
        return RuleCategorizationResult(
            rule_id=rule_id,
            complexity_level=complexity_level,
            validation_type=validation_type,
            validation_pattern=validation_pattern,
            confidence=confidence,
            reasoning=reasoning
        )
    
    def _infer_validation_type_tier1(self, description: str) -> str:
        """Infer specific Tier 1 validation type from description"""
        desc_lower = description.lower()
        
        if re.search(r'\bword[s]?\s*count\b', desc_lower):
            return 'count'
        elif re.search(r'\b(?:keyword|phrase|term)\b', desc_lower):
            return 'keyword'
        elif re.search(r'\b(?:pattern|format|regex)\b', desc_lower):
            return 'regex'
        else:
            return 'regex'  # Default
    
    def _generate_tier1_pattern(self, rule_id: str, description: str) -> str:
        """Generate validation pattern for Tier 1 rules"""
        desc_lower = description.lower()
        
        # Word count patterns
        if 'word count' in desc_lower or 'words' in desc_lower:
            match = re.search(r'(\d+)-(\d+)\s*words?', desc_lower)
            if match:
                return f"word_count_range:{match.group(1)}:{match.group(2)}"
            match = re.search(r'(?:at least|minimum of?)\s*(\d+)\s*words?', desc_lower)
            if match:
                return f"word_count_min:{match.group(1)}"
            match = re.search(r'(?:maximum|no more than)\s*(\d+)\s*words?', desc_lower)
            if match:
                return f"word_count_max:{match.group(1)}"
        
        # Phone number
        if 'phone' in desc_lower:
            return 'has_phone'
        
        # Price/cost
        if 'price' in desc_lower or 'cost' in desc_lower or '$' in description:
            return 'has_price'
        
        # License
        if 'license' in desc_lower:
            return 'has_license'
        
        # City mentions
        if 'city' in desc_lower or 'location' in desc_lower or 'neighborhood' in desc_lower:
            match = re.search(r'(\d+)\s*(?:city|cities|location|neighborhood)', desc_lower)
            if match:
                return f"has_cities:{match.group(1)}"
            return 'has_cities:3'
        
        # Header requirements
        if 'h2' in desc_lower or 'header' in desc_lower:
            match = re.search(r'(\d+)\s*(?:h2|header)', desc_lower)
            if match:
                return f"has_h2:{match.group(1)}"
            return 'has_h2:1'
        
        # Bullet points
        if 'bullet' in desc_lower or 'list' in desc_lower:
            match = re.search(r'(\d+)\s*(?:bullet|list)', desc_lower)
            if match:
                return f"has_bullets:{match.group(1)}"
            return 'has_bullets:3'
        
        # Default - keyword extraction
        return f"keyword_check:{rule_id}"
    
    def update_rule_in_db(self, result: RuleCategorizationResult):
        """Update a single rule with categorization results"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE extracted_rules
            SET complexity_level = %s,
                validation_type = %s,
                validation_pattern = %s,
                updated_at = NOW()
            WHERE rule_id = %s
        """, (result.complexity_level, result.validation_type, 
              result.validation_pattern, result.rule_id))
        cursor.close()
    
    def categorize_all_rules(self):
        """Main categorization workflow"""
        print("\n" + "="*70)
        print("GURU INTELLIGENCE - RULE CATEGORIZATION ENGINE")
        print("="*70 + "\n")
        
        # Fetch all rules
        rules = self.fetch_all_rules()
        total_rules = len(rules)
        
        results = []
        
        # Process each rule
        print(f"\n🔄 Processing {total_rules} rules...\n")
        for i, (rule_id, rule_name, rule_category, rule_description, enforcement, priority) in enumerate(rules, 1):
            result = self.categorize_rule(rule_id, rule_name, rule_description)
            results.append(result)
            
            # Update database
            self.update_rule_in_db(result)
            
            # Track tier counts
            self.tier_counts[result.complexity_level] += 1
            
            # Progress indicator
            if i % 50 == 0 or i == total_rules:
                print(f"   Processed {i}/{total_rules} rules ({i*100//total_rules}%)")
        
        # Commit all changes
        self.conn.commit()
        print("\n✅ All rules categorized and database updated")
        
        return results
    
    def print_summary(self, results: List[RuleCategorizationResult]):
        """Print categorization summary"""
        print("\n" + "="*70)
        print("CATEGORIZATION SUMMARY")
        print("="*70)
        
        print(f"\n📊 Distribution by Tier:")
        print(f"   Tier 1 (Regex/Deterministic): {self.tier_counts[1]} rules ({self.tier_counts[1]*100//len(results)}%)")
        print(f"   Tier 2 (NLP/spaCy):           {self.tier_counts[2]} rules ({self.tier_counts[2]*100//len(results)}%)")
        print(f"   Tier 3 (LLM):                 {self.tier_counts[3]} rules ({self.tier_counts[3]*100//len(results)}%)")
        print(f"   TOTAL:                        {len(results)} rules")
        
        # High confidence Tier 1 rules
        tier1_high_conf = [r for r in results if r.complexity_level == 1 and r.confidence > 0.7]
        print(f"\n✅ High-confidence Tier 1 rules: {len(tier1_high_conf)}")
        
        # Rules needing manual review (low confidence)
        low_conf = [r for r in results if r.confidence < 0.4]
        print(f"\n⚠️  Low-confidence categorizations: {len(low_conf)} (manual review recommended)")
        
        if low_conf:
            print("\n   Rules for manual review:")
            for result in low_conf[:10]:  # Show first 10
                print(f"   - {result.rule_id}: Tier {result.complexity_level} ({result.confidence:.2%} confidence)")
                print(f"     {result.reasoning}")
        
        # Validation type distribution
        validation_types = {}
        for result in results:
            validation_types[result.validation_type] = validation_types.get(result.validation_type, 0) + 1
        
        print(f"\n📋 Validation Type Distribution:")
        for val_type, count in sorted(validation_types.items(), key=lambda x: x[1], reverse=True):
            print(f"   {val_type}: {count} rules")
        
        print("\n" + "="*70)
    
    def export_results(self, results: List[RuleCategorizationResult], filename: str = 'rule_categorization_results.json'):
        """Export categorization results to JSON"""
        export_data = {
            'total_rules': len(results),
            'tier_distribution': self.tier_counts,
            'timestamp': 'December 28, 2025',
            'rules': [
                {
                    'rule_id': r.rule_id,
                    'complexity_level': r.complexity_level,
                    'validation_type': r.validation_type,
                    'validation_pattern': r.validation_pattern,
                    'confidence': round(r.confidence, 3),
                    'reasoning': r.reasoning
                }
                for r in results
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"\n💾 Results exported to {filename}")

def main():
    """Main execution"""
    categorizer = RuleCategorizer()
    
    try:
        # Connect to database
        categorizer.connect()
        
        # Run categorization
        results = categorizer.categorize_all_rules()
        
        # Print summary
        categorizer.print_summary(results)
        
        # Export results
        categorizer.export_results(results)
        
        print("\n✅ CATEGORIZATION COMPLETE!")
        print("\nNext steps:")
        print("1. Review low-confidence rules manually")
        print("2. Add prompt_template for Tier 3 rules")
        print("3. Test validation patterns for Tier 1 rules")
        print("4. Deploy Multi-Tiered Assessor API")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
    finally:
        categorizer.disconnect()

if __name__ == "__main__":
    main()
