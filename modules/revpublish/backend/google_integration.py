"""
Google Docs Integration for RevPublish
Handles OAuth flow and document text extraction
"""
import os
import re
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv('/opt/shared-api-engine/.env')

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8550/callback')


def get_google_auth_url(state: str = None) -> str:
    """Generate OAuth2 authorization URL for Google Docs access"""
    scope = "https://www.googleapis.com/auth/documents.readonly"
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={GOOGLE_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope={scope}&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    if state:
        auth_url += f"&state={state}"
    return auth_url


def extract_doc_id(url: str) -> Optional[str]:
    """Extract Google Doc ID from URL"""
    patterns = [
        r'/document/d/([a-zA-Z0-9-_]+)',
        r'id=([a-zA-Z0-9-_]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


async def fetch_google_doc_structured(doc_url: str, access_token: str = None) -> Dict[str, Any]:
    """
    Fetch and parse Google Doc content.
    Returns text content only - images are sourced from RunPod.
    """
    import httpx

    doc_id = extract_doc_id(doc_url)
    if not doc_id:
        return {"error": "Invalid Google Doc URL", "text": "", "raw": None}

    # Use service account or provided token
    token = access_token or os.getenv('GOOGLE_SERVICE_ACCOUNT_TOKEN')

    if not token:
        # For development/testing without OAuth
        return {
            "doc_id": doc_id,
            "text": "[Mock content - configure Google OAuth for real extraction]",
            "raw": None,
            "source": "mock"
        }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://docs.googleapis.com/v1/documents/{doc_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        if response.status_code != 200:
            return {
                "error": f"Failed to fetch doc: {response.status_code}",
                "text": "",
                "raw": None
            }

        doc_data = response.json()

        # Extract text content
        text_content = extract_text_from_doc(doc_data)

        return {
            "doc_id": doc_id,
            "title": doc_data.get("title", ""),
            "text": text_content,
            "raw": doc_data,
            "source": "google_api"
        }


def extract_text_from_doc(doc_data: dict) -> str:
    """Extract plain text from Google Docs API response"""
    text_parts = []

    body = doc_data.get("body", {})
    content = body.get("content", [])

    for element in content:
        if "paragraph" in element:
            paragraph = element["paragraph"]
            for elem in paragraph.get("elements", []):
                if "textRun" in elem:
                    text_parts.append(elem["textRun"].get("content", ""))

    return "".join(text_parts)


def parse_doc_sections(text: str) -> Dict[str, str]:
    """
    Parse document text into logical sections.
    Looks for common heading patterns.
    """
    sections = {
        "title": "",
        "introduction": "",
        "body": "",
        "conclusion": ""
    }

    lines = text.split('\n')
    current_section = "body"

    for line in lines:
        line_lower = line.lower().strip()

        if any(keyword in line_lower for keyword in ['introduction', 'overview', 'about']):
            current_section = "introduction"
        elif any(keyword in line_lower for keyword in ['conclusion', 'summary', 'final']):
            current_section = "conclusion"

        if current_section in sections:
            sections[current_section] += line + "\n"

    # First non-empty line is likely the title
    for line in lines:
        if line.strip():
            sections["title"] = line.strip()
            break

    return sections
