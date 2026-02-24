"""
AI-Powered Field Extraction using Claude-3-Haiku
Cost-controlled extraction with mandatory user opt-in
"""
import os
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv('/opt/shared-api-engine/.env')

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# Pricing: Claude-3-Haiku (as of 2026)
HAIKU_INPUT_COST_PER_1M = 0.25   # $0.25 per million input tokens
HAIKU_OUTPUT_COST_PER_1M = 1.25  # $1.25 per million output tokens
AVG_CHARS_PER_TOKEN = 4
EXPECTED_OUTPUT_TOKENS = 500  # Typical JSON response size


def estimate_extraction_cost(text: str) -> float:
    """
    Estimate the cost of AI extraction for transparency.
    Returns cost in USD.
    """
    input_tokens = len(text) / AVG_CHARS_PER_TOKEN
    input_cost = (input_tokens / 1_000_000) * HAIKU_INPUT_COST_PER_1M
    output_cost = (EXPECTED_OUTPUT_TOKENS / 1_000_000) * HAIKU_OUTPUT_COST_PER_1M

    total_cost = input_cost + output_cost
    return round(total_cost, 6)


def estimate_batch_cost(texts: list) -> Dict[str, Any]:
    """Estimate cost for entire batch"""
    total_cost = sum(estimate_extraction_cost(t) for t in texts)
    return {
        "item_count": len(texts),
        "estimated_cost_usd": round(total_cost, 4),
        "cost_per_item_avg": round(total_cost / len(texts), 6) if texts else 0
    }


async def extract_fields_from_doc(text: str, page_type: str = "service") -> Dict[str, Any]:
    """
    Use Claude-3-Haiku to extract structured fields from document text.

    Args:
        text: Raw text content from Google Doc
        page_type: Type of page (service, location, blog, etc.)

    Returns:
        Structured JSON with extracted fields
    """
    import httpx

    if not ANTHROPIC_API_KEY:
        return {
            "error": "ANTHROPIC_API_KEY not configured",
            "fields": get_default_fields(page_type)
        }

    system_prompt = get_extraction_prompt(page_type)

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 1024,
                    "system": system_prompt,
                    "messages": [
                        {"role": "user", "content": f"Extract fields from:\n\n{text[:8000]}"}
                    ]
                }
            )

            if response.status_code != 200:
                return {
                    "error": f"API error: {response.status_code}",
                    "fields": get_default_fields(page_type)
                }

            result = response.json()
            content = result.get("content", [{}])[0].get("text", "{}")

            # Parse JSON from response
            try:
                extracted = json.loads(content)
                return {"fields": extracted, "source": "ai", "tokens_used": result.get("usage", {})}
            except json.JSONDecodeError:
                # Try to extract JSON from text
                import re
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    extracted = json.loads(json_match.group())
                    return {"fields": extracted, "source": "ai_parsed"}
                return {"error": "Failed to parse AI response", "fields": get_default_fields(page_type)}

        except Exception as e:
            return {
                "error": str(e),
                "fields": get_default_fields(page_type)
            }


def get_extraction_prompt(page_type: str) -> str:
    """Get system prompt for specific page type"""
    prompts = {
        "service": """You are a content extraction assistant. Extract these fields from the provided text and return ONLY valid JSON:
{
  "hero_headline": "Main headline for the page",
  "hero_subheadline": "Supporting text under headline",
  "service_description": "2-3 sentence service description",
  "benefits": ["benefit 1", "benefit 2", "benefit 3"],
  "cta_text": "Call to action button text",
  "meta_title": "SEO title (60 chars max)",
  "meta_description": "SEO description (155 chars max)"
}
Return ONLY the JSON object, no explanation.""",

        "location": """Extract location page fields as JSON:
{
  "city": "City name",
  "state": "State abbreviation",
  "hero_headline": "Location-specific headline",
  "service_areas": ["area1", "area2"],
  "local_description": "Location-specific content",
  "meta_title": "SEO title with location",
  "meta_description": "SEO description with location"
}
Return ONLY JSON.""",

        "blog": """Extract blog post fields as JSON:
{
  "title": "Blog post title",
  "excerpt": "Short summary (2 sentences)",
  "main_content": "Full article content",
  "tags": ["tag1", "tag2"],
  "meta_title": "SEO title",
  "meta_description": "SEO description"
}
Return ONLY JSON."""
    }
    return prompts.get(page_type, prompts["service"])


def get_default_fields(page_type: str) -> Dict[str, Any]:
    """Return default empty fields structure"""
    defaults = {
        "service": {
            "hero_headline": "",
            "hero_subheadline": "",
            "service_description": "",
            "benefits": [],
            "cta_text": "Get a Free Quote",
            "meta_title": "",
            "meta_description": ""
        },
        "location": {
            "city": "",
            "state": "",
            "hero_headline": "",
            "service_areas": [],
            "local_description": "",
            "meta_title": "",
            "meta_description": ""
        },
        "blog": {
            "title": "",
            "excerpt": "",
            "main_content": "",
            "tags": [],
            "meta_title": "",
            "meta_description": ""
        }
    }
    return defaults.get(page_type, defaults["service"])
