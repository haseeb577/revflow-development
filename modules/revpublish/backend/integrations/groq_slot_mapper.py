"""
Free LLM (Groq) slot mapper: maps raw doc content to template slots for accurate import.
Uses Groq free tier (no credit card). Set GROQ_API_KEY in env (get at console.groq.com).
"""

import os
import re
import json
import requests
from typing import Dict, List, Any, Optional

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"
TIMEOUT = 45
MAX_CONTENT_LEN = 28000


def _strip_html_for_prompt(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(html))
    text = re.sub(r"[ \t]+", " ", text)  # collapse spaces/tabs, keep newlines for structure
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:MAX_CONTENT_LEN]


def map_content_to_slots(
    slots: List[Dict[str, Any]],
    raw_content: str,
    api_key: Optional[str] = None,
) -> Optional[Dict[str, str]]:
    """
    Use Groq (free) to map raw content into template slots. Returns slot_id -> text.
    If GROQ_API_KEY is not set or the request fails, returns None (caller falls back to chunk-based).
    """
    key = (api_key or os.getenv("GROQ_API_KEY") or "").strip()
    if not key:
        return None
    if not slots:
        return None
    content_text = _strip_html_for_prompt(raw_content)
    if not content_text:
        return None

    # Include current template text and WORD COUNT so the model keeps output within template length.
    slots_desc = []
    for s in slots:
        slot_id = (s.get("slot_id") or "").strip().upper()
        kind = (s.get("kind") or "paragraph").lower()
        label = (s.get("label") or "Content")[:80]
        current = (s.get("current_value") or "").strip()[:300]
        word_count = len(current.split()) if current else 0
        if slot_id:
            line = f"- {slot_id}: kind={kind}, label=\"{label}\""
            if current:
                line += f", current in template ({word_count} words): \"{current}\""
            else:
                line += ", current in template: (empty)"
            slots_desc.append(line)

    prompt = f"""You are an SEO copy editor. The TEMPLATE is the source of truth: preserve its structure and layout so the page looks exactly as before. Use the REFERENCE CONTENT only as inspiration — do not copy it verbatim.

STRICT LENGTH RULES (layout must not break):
- For each slot, the "current in template (N words)" is the existing page content. Your output for that slot must NOT exceed N+2 words (N words or at most 1–2 words more). If the reference content is longer, shorten it to fit. Prefer cutting words over breaking layout.
- heading slots: keep under 15 words and never longer than template length + 2.
- paragraph slots: your output must be at most (template word count + 2) words.
- button slots: keep under 8 words and never longer than template + 2.

PLACEMENT RULES:
- Where the template already has good content, keep it or make only minimal wording changes. If reference content does not fit the slot's role or length, leave the slot as "" so the existing template text will be kept.
- Slots are in page order (first = top). Map reference content to the matching section by position. When in doubt, keep what was there.

OTHER:
- REFERENCE CONTENT is for ideas only. Output EVERY slot ID; use "" when the slot should keep existing content (e.g. when nothing fits). Do not output labels like "Page content:" or "Hero Section:" as slot values.

REFERENCE CONTENT (use as reference only, do not copy as-is):
{content_text}

TEMPLATE SLOTS (current text is what is on the page now — keep, lightly adjust, or replace using reference):
{chr(10).join(slots_desc)}

Respond with ONLY a valid JSON: keys = every slot ID above, values = the final SEO-friendly text for that slot (or ""). No markdown."""

    try:
        r = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4096,
                "temperature": 0.2,
            },
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        content = content.strip()
        content = re.sub(r"^```\w*\s*", "", content)
        content = re.sub(r"\s*```\s*$", "", content)
        out = json.loads(content)
        if not isinstance(out, dict):
            return None
        # Build one entry per template slot; LLM may omit slots -> use ""
        slot_ids = [(s.get("slot_id") or "").strip().upper() for s in slots if (s.get("slot_id") or "").strip()]
        slot_map = {}
        for sid in slot_ids:
            if sid and sid.startswith("SLOT_"):
                raw = out.get(sid)
                slot_map[sid] = str(raw).strip() if raw is not None and str(raw).strip() else ""
        return slot_map
    except Exception:
        return None


def judge_and_adjust_slots(
    slots: List[Dict[str, Any]],
    slot_value_map: Dict[str, str],
    raw_content: str,
    api_key: Optional[str] = None,
) -> Dict[str, str]:
    """
    LLM as judge: review current slot mapping and return only corrections (slot_id -> new_value)
    for slots that are wrong type, too long (vs template), or off-topic. Keeps layout strict.
    """
    key = (api_key or os.getenv("GROQ_API_KEY") or "").strip()
    if not key or not slots or not slot_value_map:
        return {}
    content_preview = _strip_html_for_prompt(raw_content)[:2000]
    slots_desc = []
    for s in slots:
        sid = (s.get("slot_id") or "").strip().upper()
        kind = (s.get("kind") or "paragraph").lower()
        label = (s.get("label") or "Content")[:60]
        template_val = (s.get("current_value") or "").strip()
        template_words = len(template_val.split()) if template_val else 0
        max_allowed = template_words + 2 if template_words else (15 if kind == "heading" else (8 if kind == "button" else 50))
        if kind == "heading":
            max_allowed = min(max_allowed, 15)
        elif kind == "button":
            max_allowed = min(max_allowed, 8)
        mapped_val = (slot_value_map.get(sid) or "").strip()[:200]
        mapped_words = len((slot_value_map.get(sid) or "").split())
        if sid:
            slots_desc.append(
                f"- {sid}: kind={kind}, template={template_words} words (max {max_allowed}), mapped={mapped_words} words: \"{mapped_val}\""
            )

    prompt = f"""Review the MAPPED SLOTS. STRICT: Each slot must not exceed the template word count + 2 (layout must stay the same as the existing page).
- If "mapped" words > "max" for that slot, output a shortened correction (trim to max words).
- heading: max 15 words; button: max 8 words; paragraph: max = template words + 2.
- If a slot is wrong type (e.g. paragraph in heading slot) or off-topic, suggest a corrected value within the word limit.
- If the mapping is fine, omit that slot from your output.

REFERENCE CONTENT (excerpt):
{content_preview}

CURRENT MAPPING:
{chr(10).join(slots_desc)}

Respond with ONLY a JSON object. Include ONLY slot IDs that need correction; value = corrected text (within word limit). If nothing to fix, respond: {{}}."""

    try:
        r = requests.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2048,
                "temperature": 0.1,
            },
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            return {}
        text = (r.json().get("choices") or [{}])[0].get("message", {}).get("content") or ""
        text = re.sub(r"^```\w*\s*", "", text.strip()).strip()
        text = re.sub(r"\s*```\s*$", "", text)
        out = json.loads(text)
        if not isinstance(out, dict):
            return {}
        corrections = {}
        for sid, val in out.items():
            sid = str(sid).strip().upper()
            if sid.startswith("SLOT_") and val is not None and str(val).strip():
                corrections[sid] = str(val).strip()
        return corrections
    except Exception:
        return {}
