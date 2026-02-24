"""
Complete Validation Engines
Tier 1, 2, 3 validators with all checks
"""
from typing import List, Dict, Any
import re

class Tier1Validator:
    """
    Tier 1: Critical structural issues
    - Missing required elements
    - Broken formatting
    - Invalid structure
    """
    
    def validate(self, content: str, title: str = None) -> List[Dict[str, Any]]:
        issues = []
        
        # Check minimum length
        if len(content) < 100:
            issues.append({
                "type": "too_short",
                "severity": "critical",
                "message": "Content too short (< 100 chars)",
                "location": "global"
            })
        
        # Check for title
        if not title or len(title) < 10:
            issues.append({
                "type": "missing_title",
                "severity": "critical",
                "message": "Title missing or too short",
                "location": "title"
            })
        
        # Check for paragraphs
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if len(paragraphs) < 2:
            issues.append({
                "type": "no_paragraphs",
                "severity": "critical",
                "message": "Content needs multiple paragraphs",
                "location": "structure"
            })
        
        return issues

class Tier2Validator:
    """
    Tier 2: Quality issues
    - Readability problems
    - SEO issues
    - Content quality
    """
    
    def validate(self, content: str) -> List[Dict[str, Any]]:
        issues = []
        
        # Check sentence length
        sentences = re.split(r'[.!?]+', content)
        long_sentences = [s for s in sentences if len(s.split()) > 40]
        if long_sentences:
            issues.append({
                "type": "long_sentences",
                "severity": "warning",
                "message": f"{len(long_sentences)} sentences too long",
                "location": "readability"
            })
        
        # Check for passive voice (simple check)
        passive_indicators = ['was', 'were', 'been', 'being']
        passive_count = sum(content.lower().count(word) for word in passive_indicators)
        if passive_count > len(content.split()) * 0.1:
            issues.append({
                "type": "passive_voice",
                "severity": "warning",
                "message": "High passive voice usage",
                "location": "style"
            })
        
        return issues

class Tier3Validator:
    """
    Tier 3: Enhancement opportunities
    - Optimization suggestions
    - Best practices
    """
    
    def validate(self, content: str) -> List[Dict[str, Any]]:
        issues = []
        
        # Check for headers
        if not any(marker in content for marker in ['##', '<h2', '<h3']):
            issues.append({
                "type": "no_headers",
                "severity": "info",
                "message": "Consider adding subheaders",
                "location": "structure"
            })
        
        # Check for lists
        if not any(marker in content for marker in ['- ', '* ', '1.', '<ul', '<ol']):
            issues.append({
                "type": "no_lists",
                "severity": "info",
                "message": "Consider adding lists for readability",
                "location": "formatting"
            })
        
        return issues

class QAValidator:
    """
    Overall QA scoring system
    """
    
    def __init__(self):
        self.tier1 = Tier1Validator()
        self.tier2 = Tier2Validator()
        self.tier3 = Tier3Validator()
    
    def calculate_score(self, content: str, title: str = None) -> Dict[str, Any]:
        tier1_issues = self.tier1.validate(content, title)
        tier2_issues = self.tier2.validate(content)
        tier3_issues = self.tier3.validate(content)
        
        # Calculate score (100 base, subtract for issues)
        score = 100.0
        score -= len(tier1_issues) * 15  # Critical issues
        score -= len(tier2_issues) * 5   # Warnings
        score -= len(tier3_issues) * 2   # Info
        
        score = max(0, min(100, score))
        
        return {
            "qa_score": score,
            "tier1_issues": tier1_issues,
            "tier2_issues": tier2_issues,
            "tier3_issues": tier3_issues,
            "total_issues": len(tier1_issues) + len(tier2_issues) + len(tier3_issues),
            "passed": score >= 70
        }
