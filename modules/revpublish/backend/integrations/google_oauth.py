"""
Google OAuth Integration for RevPublish v2.0
Handles OAuth2 flow for Google Docs and Sheets access
"""

import os
import json
import pickle
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import get_db_connection

# Google API imports (optional - graceful fallback)
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False


class GoogleOAuthManager:
    """
    Manages Google OAuth2 flow and API access for Docs/Sheets.
    Stores credentials in PostgreSQL for persistence.
    """

    SCOPES = [
        'https://www.googleapis.com/auth/documents.readonly',
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/drive.readonly'
    ]

    # Read from shared environment - /opt/shared-api-engine/.env
    CONFIG_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', '/opt/revflow-os/config/google_credentials.json')
    REDIRECT_URI = 'http://217.15.168.106:8550/api/deploy/google/callback'

    def __init__(self):
        self._docs_service = None
        self._sheets_service = None
        self._drive_service = None
        self._credentials = None

    @property
    def is_available(self) -> bool:
        """Check if Google API libraries are installed"""
        return GOOGLE_API_AVAILABLE

    @property
    def is_configured(self) -> bool:
        """Check if OAuth credentials file exists"""
        return Path(self.CONFIG_PATH).exists()

    @property
    def is_authenticated(self) -> bool:
        """Check if we have valid OAuth tokens"""
        creds = self._load_credentials()
        return creds is not None and creds.valid

    def get_auth_url(self) -> str:
        """
        Generate OAuth authorization URL.
        User should visit this URL to grant access.
        """
        if not self.is_available:
            raise RuntimeError("Google API libraries not installed. Run: pip install google-auth google-auth-oauthlib google-api-python-client")

        if not self.is_configured:
            raise RuntimeError(f"OAuth config not found at {self.CONFIG_PATH}")

        flow = Flow.from_client_secrets_file(
            self.CONFIG_PATH,
            scopes=self.SCOPES,
            redirect_uri=self.REDIRECT_URI
        )

        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )

        # Store state for verification
        self._save_oauth_state(state)

        return auth_url

    def complete_auth(self, code: str, state: str) -> Dict:
        """
        Complete OAuth flow with authorization code.

        Args:
            code: Authorization code from Google callback
            state: State parameter for CSRF verification

        Returns:
            Dict with success status and user info
        """
        if not self.is_available:
            raise RuntimeError("Google API libraries not installed")

        # Verify state
        if not self._verify_oauth_state(state):
            raise ValueError("Invalid OAuth state - possible CSRF attack")

        flow = Flow.from_client_secrets_file(
            self.CONFIG_PATH,
            scopes=self.SCOPES,
            redirect_uri=self.REDIRECT_URI
        )

        # Exchange code for tokens
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Save credentials to database
        self._save_credentials(credentials)

        # Get user info
        try:
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            email = user_info.get('email', 'unknown')
        except:
            email = 'unknown'

        return {
            'success': True,
            'email': email,
            'expires_at': credentials.expiry.isoformat() if credentials.expiry else None
        }

    def revoke_auth(self) -> bool:
        """Revoke OAuth tokens and clear stored credentials"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM revpublish_oauth_tokens WHERE provider = 'google'")
            return cursor.rowcount > 0

    def get_document(self, document_id: str) -> Dict:
        """
        Fetch Google Doc content.

        Args:
            document_id: Google Docs document ID

        Returns:
            Dict with document title and content
        """
        service = self._get_docs_service()

        doc = service.documents().get(documentId=document_id).execute()

        title = doc.get('title', 'Untitled')
        content = self._extract_doc_content(doc)

        return {
            'title': title,
            'content': content,
            'document_id': document_id
        }

    def get_spreadsheet(self, spreadsheet_id: str, sheet_name: Optional[str] = None) -> Dict:
        """
        Fetch Google Sheet data.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Optional specific sheet name (defaults to first sheet)

        Returns:
            Dict with sheet data as list of row dicts
        """
        service = self._get_sheets_service()

        # Get spreadsheet metadata
        metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        title = metadata.get('properties', {}).get('title', 'Untitled')
        sheets = metadata.get('sheets', [])

        # Determine sheet to read
        if sheet_name:
            range_name = f"'{sheet_name}'"
        elif sheets:
            range_name = f"'{sheets[0]['properties']['title']}'"
        else:
            range_name = 'Sheet1'

        # Fetch data
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()

        values = result.get('values', [])

        # Convert to list of dicts using first row as headers
        rows = []
        if len(values) > 1:
            headers = values[0]
            for row in values[1:]:
                row_dict = {}
                for i, header in enumerate(headers):
                    if i < len(row):
                        row_dict[header] = row[i]
                    else:
                        row_dict[header] = ''
                rows.append(row_dict)

        return {
            'title': title,
            'sheet_name': sheet_name or (sheets[0]['properties']['title'] if sheets else 'Sheet1'),
            'spreadsheet_id': spreadsheet_id,
            'row_count': len(rows),
            'headers': values[0] if values else [],
            'rows': rows
        }

    def list_recent_docs(self, limit: int = 20) -> List[Dict]:
        """List user's recent Google Docs"""
        service = self._get_drive_service()

        results = service.files().list(
            q="mimeType='application/vnd.google-apps.document'",
            pageSize=limit,
            fields="files(id, name, modifiedTime, webViewLink)"
        ).execute()

        return [
            {
                'id': f['id'],
                'name': f['name'],
                'modified': f.get('modifiedTime'),
                'url': f.get('webViewLink')
            }
            for f in results.get('files', [])
        ]

    def list_recent_sheets(self, limit: int = 20) -> List[Dict]:
        """List user's recent Google Sheets"""
        service = self._get_drive_service()

        results = service.files().list(
            q="mimeType='application/vnd.google-apps.spreadsheet'",
            pageSize=limit,
            fields="files(id, name, modifiedTime, webViewLink)"
        ).execute()

        return [
            {
                'id': f['id'],
                'name': f['name'],
                'modified': f.get('modifiedTime'),
                'url': f.get('webViewLink')
            }
            for f in results.get('files', [])
        ]

    def _get_docs_service(self):
        """Get authenticated Docs API service"""
        if self._docs_service is None:
            creds = self._get_valid_credentials()
            self._docs_service = build('docs', 'v1', credentials=creds)
        return self._docs_service

    def _get_sheets_service(self):
        """Get authenticated Sheets API service"""
        if self._sheets_service is None:
            creds = self._get_valid_credentials()
            self._sheets_service = build('sheets', 'v4', credentials=creds)
        return self._sheets_service

    def _get_drive_service(self):
        """Get authenticated Drive API service"""
        if self._drive_service is None:
            creds = self._get_valid_credentials()
            self._drive_service = build('drive', 'v3', credentials=creds)
        return self._drive_service

    def _get_valid_credentials(self) -> 'Credentials':
        """Get valid credentials, refreshing if necessary"""
        creds = self._load_credentials()

        if creds is None:
            raise RuntimeError("Not authenticated with Google. Visit /api/deploy/google/auth to connect.")

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self._save_credentials(creds)

        return creds

    def _load_credentials(self) -> Optional['Credentials']:
        """Load credentials from database"""
        if not GOOGLE_API_AVAILABLE:
            return None

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT token_data FROM revpublish_oauth_tokens
                WHERE provider = 'google'
            """)
            row = cursor.fetchone()

            if row:
                try:
                    return pickle.loads(row['token_data'])
                except:
                    return None
        return None

    def _save_credentials(self, credentials: 'Credentials'):
        """Save credentials to database"""
        token_data = pickle.dumps(credentials)

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO revpublish_oauth_tokens (provider, token_data, created_at, updated_at)
                VALUES ('google', %s, NOW(), NOW())
                ON CONFLICT (provider) DO UPDATE SET
                    token_data = EXCLUDED.token_data,
                    updated_at = NOW()
            """, (token_data,))

    def _save_oauth_state(self, state: str):
        """Save OAuth state for CSRF verification"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO revpublish_oauth_states (state, created_at, expires_at)
                VALUES (%s, NOW(), NOW() + INTERVAL '10 minutes')
            """, (state,))

    def _verify_oauth_state(self, state: str) -> bool:
        """Verify and consume OAuth state"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM revpublish_oauth_states
                WHERE state = %s AND expires_at > NOW()
                RETURNING state
            """, (state,))
            return cursor.fetchone() is not None

    def _extract_doc_content(self, doc: Dict) -> str:
        """Extract text content from Google Docs API response"""
        content_parts = []

        for element in doc.get('body', {}).get('content', []):
            if 'paragraph' in element:
                para = element['paragraph']
                para_text = ''

                for elem in para.get('elements', []):
                    if 'textRun' in elem:
                        para_text += elem['textRun'].get('content', '')

                if para_text.strip():
                    # Check for heading style
                    style = para.get('paragraphStyle', {}).get('namedStyleType', '')
                    if 'HEADING' in style:
                        level = style.replace('HEADING_', '')
                        content_parts.append(f"<h{level}>{para_text.strip()}</h{level}>")
                    else:
                        content_parts.append(f"<p>{para_text.strip()}</p>")

            elif 'table' in element:
                # Handle tables
                table_html = self._extract_table(element['table'])
                content_parts.append(table_html)

        return '\n'.join(content_parts)

    def _extract_table(self, table: Dict) -> str:
        """Extract table as HTML"""
        rows = []
        for row in table.get('tableRows', []):
            cells = []
            for cell in row.get('tableCells', []):
                cell_text = ''
                for content in cell.get('content', []):
                    if 'paragraph' in content:
                        for elem in content['paragraph'].get('elements', []):
                            if 'textRun' in elem:
                                cell_text += elem['textRun'].get('content', '')
                cells.append(f"<td>{cell_text.strip()}</td>")
            rows.append(f"<tr>{''.join(cells)}</tr>")

        return f"<table>{''.join(rows)}</table>"


# Singleton instance
google_oauth = GoogleOAuthManager()
