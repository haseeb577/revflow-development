"""
YMYL (Your Money Your Life) Verification Checker
Verifies critical information in health, finance, legal content
"""
from typing import List, Dict, Any
import re

class YMYLVerificationChecker:
    """
    Verifies YMYL content has proper disclaimers and accurate info
    """
    
    # Required elements for YMYL content
    YMYL_REQUIREMENTS = {
        "medical": ["licensed", "certified", "disclaimer"],
        "financial": ["licensed", "registered", "disclaimer"],
        "legal": ["attorney", "licensed", "jurisdiction", "disclaimer"]
    }
    
    def check(self, content: str, content_type: str = "general") -> Dict[str, Any]:
        """
        Verify YMYL content requirements
        
        Returns:
            {
                "score": float,
                "failures": List[Dict],
                "is_verified": bool
            }
        """
        failures = []
        
        # If not YMYL content, pass automatically
        if content_type == "general":
            return {
                "score": 100.0,
                "failures": [],
                "is_verified": True,
                "details": {"content_type": "general", "ymyl_check": "not_applicable"}
            }
        
        # Check for required elements
        content_lower = content.lower()
        required = self.YMYL_REQUIREMENTS.get(content_type, [])
        
        for requirement in required:
            if requirement not in content_lower:
                failures.append({
                    "type": "missing_requirement",
                    "requirement": requirement,
                    "severity": "critical",
                    "message": f"YMYL content missing: {requirement}"
                })
        
        # Check for phone numbers (should be present for YMYL)
        phone_pattern = r'\(\d{3}\)\s*\d{3}-\d{4}|\d{3}-\d{3}-\d{4}'
        if not re.search(phone_pattern, content):
            failures.append({
                "type": "missing_contact",
                "requirement": "phone_number",
                "severity": "high",
                "message": "YMYL content should include contact phone"
            })
        
        # Calculate score
        max_failures = len(required) + 1
        failure_count = len(failures)
        score = max(0, 100 - (failure_count / max_failures * 100))
        
        return {
            "score": round(score, 1),
            "failures": failures,
            "is_verified": score >= 80,
            "details": {
                "content_type": content_type,
                "requirements_checked": len(required),
                "failures_found": failure_count
            }
        }
