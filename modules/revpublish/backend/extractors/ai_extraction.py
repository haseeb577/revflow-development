"""
AI-Powered Field Extraction using Claude-3-Haiku
RevPublish v2.0 - Intelligent content parsing with cost controls
"""

import os
import json
import httpx
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import get_db_connection


@dataclass
class ExtractionCost:
    """Cost tracking for AI extraction"""
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    model: str = "claude-3-haiku-20240307"

    # Haiku pricing (as of 2024): $0.25/1M input, $1.25/1M output
    INPUT_COST_PER_TOKEN = 0.25 / 1_000_000
    OUTPUT_COST_PER_TOKEN = 1.25 / 1_000_000

    @classmethod
    def calculate(cls, input_tokens: int, output_tokens: int) -> 'ExtractionCost':
        cost = (input_tokens * cls.INPUT_COST_PER_TOKEN) + (output_tokens * cls.OUTPUT_COST_PER_TOKEN)
        return cls(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=round(cost, 6)
        )


class AIFieldExtractor:
    """
    Extracts structured fields from raw content using Claude-3-Haiku.
    Includes cost estimation before extraction and actual cost tracking.
    """

    MODEL = "claude-3-haiku-20240307"
    MAX_TOKENS = 4096
    API_URL = "https://api.anthropic.com/v1/messages"

    # Cost limits
    DEFAULT_MAX_COST_PER_EXTRACTION = 0.10  # $0.10 max per extraction
    DEFAULT_MAX_DAILY_SPEND = 5.00  # $5.00 daily limit

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        self.client = httpx.Client(
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            timeout=60.0
        )

    def estimate_cost(self, content: str, page_type_id: str) -> ExtractionCost:
        """
        Estimate extraction cost before running.
        Uses approximate token counting (4 chars = 1 token).
        """
        # Estimate input tokens
        fields = self._get_page_fields(page_type_id)
        prompt = self._build_prompt(content, fields, page_type_id)
        input_tokens = len(prompt) // 4  # Rough estimate

        # Estimate output tokens (JSON response with all fields)
        output_tokens = min(self.MAX_TOKENS, len(fields) * 100)  # ~100 tokens per field

        return ExtractionCost.calculate(input_tokens, output_tokens)

    def extract_fields(
        self,
        content: str,
        page_type_id: str,
        max_cost: Optional[float] = None
    ) -> Tuple[Dict, ExtractionCost]:
        """
        Extract structured fields from content using AI.

        Args:
            content: Raw content (text, HTML, or document text)
            page_type_id: Target page type (service_page, location_page, etc.)
            max_cost: Maximum cost allowed for this extraction

        Returns:
            Tuple of (extracted_fields_dict, actual_cost)

        Raises:
            ValueError: If estimated cost exceeds max_cost
        """
        max_cost = max_cost or self.DEFAULT_MAX_COST_PER_EXTRACTION

        # Check cost estimate first
        estimated = self.estimate_cost(content, page_type_id)
        if estimated.estimated_cost_usd > max_cost:
            raise ValueError(
                f"Estimated cost ${estimated.estimated_cost_usd:.4f} exceeds "
                f"limit ${max_cost:.2f}. Reduce content size or increase limit."
            )

        # Check daily spend limit
        daily_spend = self._get_daily_spend()
        if daily_spend + estimated.estimated_cost_usd > self.DEFAULT_MAX_DAILY_SPEND:
            raise ValueError(
                f"Daily spend limit (${self.DEFAULT_MAX_DAILY_SPEND:.2f}) would be exceeded. "
                f"Current: ${daily_spend:.2f}, Estimated: ${estimated.estimated_cost_usd:.4f}"
            )

        # Build extraction prompt
        fields = self._get_page_fields(page_type_id)
        prompt = self._build_prompt(content, fields, page_type_id)

        # Call Claude API
        response = self._call_api(prompt)

        # Parse response
        extracted = self._parse_response(response, fields)

        # Calculate actual cost
        actual_cost = ExtractionCost.calculate(
            response.get('usage', {}).get('input_tokens', 0),
            response.get('usage', {}).get('output_tokens', 0)
        )

        # Log usage to database
        self._log_usage(page_type_id, actual_cost)

        return extracted, actual_cost

    def _get_page_fields(self, page_type_id: str) -> List[Dict]:
        """Get field definitions for page type"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT field_name, field_label, field_type, is_required, description
                FROM revpublish_page_fields
                WHERE page_type_id = %s
                ORDER BY field_order
            """, (page_type_id,))
            return [dict(row) for row in cursor.fetchall()]

    def _build_prompt(self, content: str, fields: List[Dict], page_type_id: str) -> str:
        """Build extraction prompt for Claude"""

        field_descriptions = "\n".join([
            f"- {f['field_name']} ({f['field_type']}): {f['description'] or f['field_label']}"
            + (" [REQUIRED]" if f['is_required'] else "")
            for f in fields
        ])

        return f"""You are an expert content parser. Extract structured data from the following content to populate a {page_type_id.replace('_', ' ')} page.

## Target Fields:
{field_descriptions}

## Content to Parse:
{content[:8000]}

## Instructions:
1. Extract values for each field from the content
2. For 'list' type fields, provide pipe-separated values (e.g., "Item 1|Item 2|Item 3")
3. For 'html' type fields, preserve formatting
4. If a field value is not found, use null
5. Return ONLY valid JSON, no explanation

## Output Format:
Return a JSON object with field names as keys. Example:
{{"field_name": "value", "list_field": "item1|item2|item3"}}

Extract the fields now:"""

    def _call_api(self, prompt: str) -> Dict:
        """Call Claude API"""
        payload = {
            "model": self.MODEL,
            "max_tokens": self.MAX_TOKENS,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        response = self.client.post(self.API_URL, json=payload)
        response.raise_for_status()
        return response.json()

    def _parse_response(self, response: Dict, fields: List[Dict]) -> Dict:
        """Parse Claude's response into structured data"""
        try:
            content = response.get('content', [{}])[0].get('text', '{}')

            # Find JSON in response (might be wrapped in markdown)
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1].split('```')[0]

            extracted = json.loads(content.strip())

            # Validate against expected fields
            validated = {}
            for field in fields:
                field_name = field['field_name']
                if field_name in extracted:
                    validated[field_name] = extracted[field_name]
                elif field['is_required']:
                    validated[field_name] = None  # Mark as missing but required

            return validated

        except json.JSONDecodeError:
            # Fallback: try to extract what we can
            return {}

    def _get_daily_spend(self) -> float:
        """Get total AI extraction spend for today"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(SUM(cost_usd), 0) as total
                FROM revpublish_ai_usage
                WHERE DATE(created_at) = CURRENT_DATE
            """)
            row = cursor.fetchone()
            return float(row['total']) if row else 0.0

    def _log_usage(self, page_type_id: str, cost: ExtractionCost):
        """Log AI usage to database"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO revpublish_ai_usage
                (page_type_id, model, input_tokens, output_tokens, cost_usd, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (page_type_id, cost.model, cost.input_tokens, cost.output_tokens, cost.estimated_cost_usd))


class HybridExtractor:
    """
    Combines rule-based extraction with AI fallback.
    Uses AI only when rule-based extraction fails or is incomplete.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.ai_extractor = AIFieldExtractor(api_key) if api_key or os.getenv("ANTHROPIC_API_KEY") else None

        # Rule-based patterns
        self.patterns = {
            'phone_number': r'[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4}',
            'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            'address': r'\d+\s+[\w\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr)[\w\s,]*\d{5}',
            'price': r'\$[\d,]+(?:\.\d{2})?',
            'city': None,  # Requires AI or location DB
            'state': None,  # Requires AI or location DB
        }

    def extract(
        self,
        content: str,
        page_type_id: str,
        use_ai: bool = True,
        ai_max_cost: float = 0.05
    ) -> Tuple[Dict, Optional[ExtractionCost], List[str]]:
        """
        Extract fields using hybrid approach.

        Returns:
            Tuple of (extracted_data, ai_cost_if_used, warnings)
        """
        import re
        warnings = []

        # First pass: rule-based extraction
        extracted = {}
        for field_name, pattern in self.patterns.items():
            if pattern:
                matches = re.findall(pattern, content)
                if matches:
                    extracted[field_name] = matches[0] if len(matches) == 1 else '|'.join(matches[:5])

        # Get required fields
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT field_name, is_required
                FROM revpublish_page_fields
                WHERE page_type_id = %s
            """, (page_type_id,))
            fields_info = {row['field_name']: row['is_required'] for row in cursor.fetchall()}

        # Check for missing required fields
        missing_required = [
            name for name, required in fields_info.items()
            if required and name not in extracted
        ]

        ai_cost = None

        # Use AI if needed and enabled
        if use_ai and missing_required and self.ai_extractor:
            try:
                ai_extracted, ai_cost = self.ai_extractor.extract_fields(
                    content, page_type_id, max_cost=ai_max_cost
                )
                # Merge AI results (AI fills gaps, doesn't override)
                for key, value in ai_extracted.items():
                    if key not in extracted and value is not None:
                        extracted[key] = value
            except ValueError as e:
                warnings.append(f"AI extraction skipped: {str(e)}")
            except Exception as e:
                warnings.append(f"AI extraction failed: {str(e)}")

        # Final check for missing fields
        still_missing = [
            name for name, required in fields_info.items()
            if required and name not in extracted
        ]
        if still_missing:
            warnings.append(f"Missing required fields: {', '.join(still_missing)}")

        return extracted, ai_cost, warnings


# Singleton instances
ai_extractor = None
hybrid_extractor = None

def get_ai_extractor() -> AIFieldExtractor:
    global ai_extractor
    if ai_extractor is None:
        ai_extractor = AIFieldExtractor()
    return ai_extractor

def get_hybrid_extractor() -> HybridExtractor:
    global hybrid_extractor
    if hybrid_extractor is None:
        hybrid_extractor = HybridExtractor()
    return hybrid_extractor
