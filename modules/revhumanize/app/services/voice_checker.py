"""
Voice Consistency Checker
Ensures content matches brand voice patterns
"""
from typing import List, Dict, Any
import re

class VoiceConsistencyChecker:
    """
    Checks if content maintains consistent voice and tone
    """
    
    # Prohibited patterns (AI-like phrases)
    PROHIBITED_PATTERNS = [
        r"it's important to note",
        r"it's worth noting",
        r"as an AI",
        r"I don't have personal",
        r"I cannot",
        r"delve into",
        r"navigate the landscape",
        r"comprehensive guide",
        r"in today's digital age",
        r"in conclusion",
        r"to summarize"
    ]
    
    def check(self, content: str, reference_voice: str = None) -> Dict[str, Any]:
        """
        Check content for voice consistency
        
        Returns:
            {
                "score": float,
                "violations": List[Dict],
                "is_consistent": bool
            }
        """
        violations = []
        
        # Check for prohibited AI patterns
        content_lower = content.lower()
        for pattern in self.PROHIBITED_PATTERNS:
            matches = list(re.finditer(pattern, content_lower, re.IGNORECASE))
            if matches:
                for match in matches:
                    violations.append({
                        "pattern_type": "prohibited_phrase",
                        "phrase": match.group(),
                        "position": match.start(),
                        "severity": "high"
                    })
        
        # Calculate score
        max_violations = 10
        violation_count = len(violations)
        score = max(0, 100 - (violation_count / max_violations * 100))
        
        return {
            "score": round(score, 1),
            "violations": violations,
            "is_consistent": score >= 80,
            "details": {
                "violation_count": violation_count,
                "patterns_checked": len(self.PROHIBITED_PATTERNS)
            }
        }
