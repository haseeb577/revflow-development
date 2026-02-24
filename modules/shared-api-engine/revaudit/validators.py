"""
RevAudit Content Validators
Local validation for hallucination detection
"""

import re
from typing import List, Dict, Tuple, Any


# Forbidden phrases that indicate potential hallucination
FORBIDDEN_PHRASES = [
    # Vague authority claims
    ("Based on industry best practices", "BLOCKED", "No specific source cited"),
    ("Studies show", "BLOCKED", "Which studies? Need citation"),
    ("Research indicates", "BLOCKED", "What research? Need source"),
    ("Experts suggest", "BLOCKED", "Which experts? Need names"),
    ("Experts say", "BLOCKED", "Which experts? Need names"),
    ("According to experts", "BLOCKED", "Which experts? Need citation"),

    # Unsourced generalizations
    ("Typically we see", "BLOCKED", "Anecdotal - needs data"),
    ("Generally speaking", "WARNING", "Too vague for data-driven report"),
    ("In our experience", "WARNING", "Anecdotal - needs data backing"),
    ("It is recommended", "WARNING", "Who recommends? Needs attribution"),
    ("Best practice suggests", "WARNING", "Needs specific source"),
    ("Industry standards indicate", "WARNING", "Which standards? Need citation"),

    # Fabrication indicators
    ("As you can see", "WARNING", "May be fabricating observation"),
    ("Obviously", "WARNING", "May be masking lack of data"),
    ("Clearly", "WARNING", "May be masking lack of data"),
    ("It goes without saying", "WARNING", "May be fabricating consensus"),

    # Unverifiable claims
    ("Many businesses", "WARNING", "How many? Need data"),
    ("Most companies", "WARNING", "What percentage? Need source"),
    ("Significant improvement", "WARNING", "Quantify with data"),
    ("Substantial increase", "WARNING", "Quantify with data"),
]


def check_for_hallucination(content: str) -> Tuple[bool, List[Dict]]:
    """
    Check content for hallucination indicators.

    Returns:
        (is_clean, detections) where:
        - is_clean: True if no BLOCKED issues
        - detections: List of all detected issues
    """
    if not content:
        return True, []

    content_lower = content.lower()
    detections = []

    for phrase, severity, reason in FORBIDDEN_PHRASES:
        if phrase.lower() in content_lower:
            detections.append({
                "phrase": phrase,
                "severity": severity,
                "reason": reason,
                "action": "blocked" if severity == "BLOCKED" else "flagged"
            })

    # Check for numeric claims without citations
    # Pattern: numbers followed by % or decimal numbers
    numeric_claims = re.findall(r'[^[]*?(\d+\.?\d*\s*%|\d+\.\d+)[^]]*', content)
    for claim_match in numeric_claims:
        # Check if this number has a citation nearby
        claim_context = content[max(0, content.find(claim_match) - 50):
                                content.find(claim_match) + len(claim_match) + 50]

        if '[Source:' not in claim_context and '[' not in claim_context:
            # Only flag if it looks like a claim, not just a number
            if any(word in claim_context.lower() for word in
                   ['rate', 'score', 'percent', 'improvement', 'increase',
                    'decrease', 'average', 'total', 'growth']):
                detections.append({
                    "phrase": claim_context.strip()[:100],
                    "severity": "WARNING",
                    "reason": "Numeric claim without source citation",
                    "action": "flagged"
                })

    is_clean = not any(d["severity"] == "BLOCKED" for d in detections)
    return is_clean, detections


def validate_content(content: str, strict: bool = True) -> Dict[str, Any]:
    """
    Validate content and return detailed result.

    Args:
        content: Text to validate
        strict: If True, treats BLOCKED as failure

    Returns:
        Dict with validation result
    """
    is_clean, detections = check_for_hallucination(content)

    blocked = [d for d in detections if d["severity"] == "BLOCKED"]
    warnings = [d for d in detections if d["severity"] == "WARNING"]

    return {
        "valid": is_clean if strict else True,
        "is_clean": is_clean,
        "blocked_count": len(blocked),
        "warning_count": len(warnings),
        "blocked_issues": blocked,
        "warnings": warnings,
        "can_proceed": is_clean
    }


def validate_report(report_sections: Dict[str, str]) -> Dict[str, Any]:
    """
    Validate an entire report with multiple sections.

    Args:
        report_sections: Dict mapping section names to content

    Returns:
        Validation result with per-section details
    """
    all_detections = []
    section_results = {}

    for section_name, content in report_sections.items():
        result = validate_content(content, strict=False)
        section_results[section_name] = result

        for detection in result.get("blocked_issues", []) + result.get("warnings", []):
            detection["section"] = section_name
            all_detections.append(detection)

    blocked = [d for d in all_detections if d["severity"] == "BLOCKED"]

    return {
        "valid": len(blocked) == 0,
        "total_issues": len(all_detections),
        "blocked_count": len(blocked),
        "sections": section_results,
        "all_detections": all_detections,
        "can_generate": len(blocked) == 0
    }


def format_with_citation(
    claim: str,
    source_tool: str,
    source_field: str,
    timestamp: str = None
) -> str:
    """
    Format a claim with proper citation.

    Example:
        format_with_citation(
            "Review response rate: 94%",
            "GBP_API",
            "response_rate",
            "2026-02-08 14:35:12"
        )
        # Returns: "Review response rate: 94% [Source: GBP_API, response_rate, 2026-02-08 14:35:12]"
    """
    citation_parts = [f"Source: {source_tool}"]
    if source_field:
        citation_parts.append(source_field)
    if timestamp:
        citation_parts.append(timestamp)

    return f"{claim} [{', '.join(citation_parts)}]"


def strip_citations(content: str) -> str:
    """Remove citations from content for readability."""
    return re.sub(r'\s*\[Source:[^\]]+\]', '', content)
