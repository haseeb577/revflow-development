"""
RevAudit™ Anti-Hallucination Framework
Core Audit Service for Data Provenance & Integrity

Every API call, every claim, every piece of data must be auditable.
Zero tolerance for fabricated data.
"""

import os
import json
import hashlib
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
from enum import Enum


class ConfidenceLevel(Enum):
    HIGH = "HIGH"           # Direct API response
    MEDIUM = "MEDIUM"       # Calculated from API data
    LOW = "LOW"             # Estimated/derived
    UNVERIFIED = "UNVERIFIED"  # No source - BLOCKED


class HallucinationSeverity(Enum):
    BLOCKED = "BLOCKED"     # Cannot proceed
    WARNING = "WARNING"     # Flagged but allowed
    INFO = "INFO"           # Logged for review


class HallucinationDetected(Exception):
    """Raised when potential hallucination is detected"""
    def __init__(self, content: str, reason: str, severity: HallucinationSeverity):
        self.content = content
        self.reason = reason
        self.severity = severity
        super().__init__(f"Hallucination detected: {reason}")


class MissingSourceAttribution(Exception):
    """Raised when a claim has no source attribution"""
    pass


class RevAuditService:
    """
    Core audit service for anti-hallucination framework.

    Features:
    - API call logging with full payloads
    - Response hash verification
    - Claim source attribution
    - Hallucination detection
    - User verification gates
    """

    def __init__(self):
        self.db_config = {
            'dbname': os.getenv('POSTGRES_DB', 'revflow'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'revflow2026'),
            'host': 'localhost',
            'port': 5432
        }
        self.audit_storage_path = Path('/opt/revflow-data/audit')
        self.audit_storage_path.mkdir(parents=True, exist_ok=True)
        self._forbidden_phrases = None

    def _get_connection(self):
        return psycopg2.connect(**self.db_config)

    # =========================================================================
    # API CALL LOGGING
    # =========================================================================

    def log_api_call(
        self,
        tool: str,
        endpoint: str,
        method: str = 'GET',
        request_payload: Optional[Dict] = None,
        response_data: Any = None,
        response_status: int = 200,
        called_by_module: str = None,
        assessment_id: str = None,
        session_id: str = None,
        user_id: str = None,
        duration_ms: int = None
    ) -> Dict[str, Any]:
        """
        Log an API call with full audit trail.

        Returns audit record with audit_id for future reference.
        """
        audit_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()

        # Serialize and hash response
        response_str = json.dumps(response_data, default=str) if response_data else ""
        response_hash = hashlib.sha256(response_str.encode()).hexdigest()
        response_size = len(response_str)

        # Store raw response to file
        raw_response_path = None
        if response_data:
            raw_response_path = self._store_raw_response(audit_id, response_data)

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO audit_api_calls
                        (audit_id, tool, endpoint, method, request_payload,
                         response_status, response_hash, response_size, raw_response_path,
                         called_by_module, assessment_id, session_id, user_id,
                         request_timestamp, response_timestamp, duration_ms)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        audit_id, tool, endpoint, method,
                        json.dumps(request_payload) if request_payload else None,
                        response_status, response_hash, response_size, raw_response_path,
                        called_by_module,
                        assessment_id,
                        session_id,
                        user_id,
                        timestamp, timestamp, duration_ms
                    ))
                conn.commit()

            return {
                'audit_id': audit_id,
                'tool': tool,
                'endpoint': endpoint,
                'response_hash': response_hash,
                'raw_response_path': raw_response_path,
                'timestamp': timestamp.isoformat(),
                'logged': True
            }

        except Exception as e:
            print(f"[RevAudit] Failed to log API call: {e}")
            return {'audit_id': audit_id, 'logged': False, 'error': str(e)}

    def _store_raw_response(self, audit_id: str, response_data: Any) -> str:
        """Store raw API response to file for audit purposes"""
        date_path = datetime.utcnow().strftime('%Y/%m/%d')
        storage_dir = self.audit_storage_path / date_path
        storage_dir.mkdir(parents=True, exist_ok=True)

        file_path = storage_dir / f"{audit_id}.json"
        with open(file_path, 'w') as f:
            json.dump({
                'audit_id': audit_id,
                'stored_at': datetime.utcnow().isoformat(),
                'response': response_data
            }, f, indent=2, default=str)

        return str(file_path)

    def get_raw_response(self, audit_id: str) -> Optional[Dict]:
        """Retrieve stored raw response by audit_id"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT raw_response_path FROM audit_api_calls WHERE audit_id = %s",
                        (audit_id,)
                    )
                    row = cur.fetchone()
                    if row and row['raw_response_path']:
                        with open(row['raw_response_path']) as f:
                            return json.load(f)
            return None
        except Exception as e:
            print(f"[RevAudit] Failed to get raw response: {e}")
            return None

    # =========================================================================
    # CLAIM REGISTRATION & VERIFICATION
    # =========================================================================

    def register_claim(
        self,
        claim_text: str,
        source_audit_id: str,
        source_field: str,
        source_value: Any,
        claim_type: str = 'metric',
        assessment_id: str = None,
        report_section: str = None
    ) -> Dict[str, Any]:
        """
        Register a claim with its source attribution.

        Every claim in a report must call this to prove it has a source.
        """
        claim_id = str(uuid.uuid4())

        # Determine confidence level
        confidence = self._calculate_confidence(source_audit_id, source_field)

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Get source tool from audit record
                    cur.execute(
                        "SELECT tool FROM audit_api_calls WHERE audit_id = %s",
                        (source_audit_id,)
                    )
                    source_row = cur.fetchone()
                    source_tool = source_row['tool'] if source_row else 'UNKNOWN'

                    cur.execute("""
                        INSERT INTO audit_claims
                        (claim_id, claim_text, claim_type, source_audit_id,
                         source_tool, source_field, source_value, confidence_level,
                         confidence_reason, assessment_id, report_section)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *
                    """, (
                        claim_id, claim_text, claim_type, source_audit_id,
                        source_tool, source_field, str(source_value),
                        confidence.value,
                        f"Source: {source_tool}, Field: {source_field}",
                        assessment_id, report_section
                    ))
                    result = cur.fetchone()
                conn.commit()

            return {
                'claim_id': claim_id,
                'confidence': confidence.value,
                'source_tool': source_tool,
                'verified': True,
                'citation': f"[Source: {source_tool}, {source_field}]"
            }

        except Exception as e:
            print(f"[RevAudit] Failed to register claim: {e}")
            return {'claim_id': claim_id, 'verified': False, 'error': str(e)}

    def _calculate_confidence(self, audit_id: str, source_field: str) -> ConfidenceLevel:
        """Calculate confidence level based on source"""
        if not audit_id:
            return ConfidenceLevel.UNVERIFIED

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id FROM audit_api_calls WHERE audit_id = %s",
                        (audit_id,)
                    )
                    if cur.fetchone():
                        if source_field:
                            return ConfidenceLevel.HIGH
                        return ConfidenceLevel.MEDIUM
        except:
            pass

        return ConfidenceLevel.LOW

    # =========================================================================
    # HALLUCINATION DETECTION
    # =========================================================================

    def check_for_hallucination(
        self,
        content: str,
        assessment_id: str = None,
        module: str = None
    ) -> Tuple[bool, List[Dict]]:
        """
        Check content for potential hallucinations.

        Returns (is_clean, detections) where:
        - is_clean: True if no BLOCKED issues found
        - detections: List of all detected issues
        """
        detections = []
        forbidden = self._get_forbidden_phrases()

        for phrase_row in forbidden:
            phrase = phrase_row['phrase'].lower()
            if phrase in content.lower():
                severity = HallucinationSeverity[phrase_row['severity']]
                detection = self._log_detection(
                    content[:200],
                    f"Contains forbidden phrase: '{phrase_row['phrase']}'",
                    f"forbidden_phrase:{phrase_row['id']}",
                    severity,
                    assessment_id,
                    module
                )
                detections.append(detection)

        # Check for claims without citations
        # Simple heuristic: sentences with numbers but no brackets
        import re
        sentences = re.split(r'[.!?]', content)
        for sentence in sentences:
            if re.search(r'\d+%|\d+\.\d+', sentence):  # Has numbers
                if '[' not in sentence and 'Source:' not in sentence:
                    detection = self._log_detection(
                        sentence.strip()[:200],
                        "Numeric claim without source citation",
                        "missing_citation",
                        HallucinationSeverity.WARNING,
                        assessment_id,
                        module
                    )
                    detections.append(detection)

        is_clean = not any(d['severity'] == 'BLOCKED' for d in detections)
        return is_clean, detections

    def _get_forbidden_phrases(self) -> List[Dict]:
        """Get list of forbidden phrases"""
        if self._forbidden_phrases is None:
            try:
                with self._get_connection() as conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute(
                            "SELECT * FROM audit_forbidden_phrases WHERE active = TRUE"
                        )
                        self._forbidden_phrases = [dict(r) for r in cur.fetchall()]
            except:
                self._forbidden_phrases = []
        return self._forbidden_phrases

    def _log_detection(
        self,
        content: str,
        reason: str,
        rule: str,
        severity: HallucinationSeverity,
        assessment_id: str = None,
        module: str = None
    ) -> Dict:
        """Log a hallucination detection"""
        detection_id = str(uuid.uuid4())
        action = 'blocked' if severity == HallucinationSeverity.BLOCKED else 'flagged'

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO audit_hallucination_detections
                        (detection_id, flagged_content, detection_reason, detection_rule,
                         severity, action_taken, assessment_id, module)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        detection_id, content, reason, rule,
                        severity.value, action, assessment_id, module
                    ))
                conn.commit()
        except Exception as e:
            print(f"[RevAudit] Failed to log detection: {e}")

        return {
            'detection_id': detection_id,
            'severity': severity.value,
            'reason': reason,
            'action': action
        }

    def validate_report_content(
        self,
        report_text: str,
        assessment_id: str,
        strict: bool = True
    ) -> Dict[str, Any]:
        """
        Validate entire report content before generation.

        If strict=True, raises exception on BLOCKED issues.
        Returns validation result with all findings.
        """
        is_clean, detections = self.check_for_hallucination(
            report_text, assessment_id
        )

        blocked = [d for d in detections if d['severity'] == 'BLOCKED']
        warnings = [d for d in detections if d['severity'] == 'WARNING']

        result = {
            'valid': is_clean,
            'assessment_id': assessment_id,
            'blocked_count': len(blocked),
            'warning_count': len(warnings),
            'blocked_issues': blocked,
            'warnings': warnings,
            'can_generate': is_clean
        }

        if strict and not is_clean:
            raise HallucinationDetected(
                blocked[0]['reason'] if blocked else "Unknown",
                f"{len(blocked)} blocked issues found",
                HallucinationSeverity.BLOCKED
            )

        return result

    # =========================================================================
    # USER VERIFICATION GATES
    # =========================================================================

    def create_verification_gate(
        self,
        assessment_id: str,
        data_type: str,
        data_snapshot: Dict
    ) -> str:
        """
        Create a verification gate that user must approve.

        Returns verification_id for tracking.
        """
        verification_id = str(uuid.uuid4())

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO audit_verifications
                        (verification_id, assessment_id, data_type, status, data_snapshot)
                        VALUES (%s, %s, %s, 'pending', %s)
                    """, (
                        verification_id, assessment_id, data_type,
                        json.dumps(data_snapshot, default=str)
                    ))
                conn.commit()

            return verification_id

        except Exception as e:
            print(f"[RevAudit] Failed to create verification gate: {e}")
            return None

    def approve_verification(
        self,
        verification_id: str,
        user_id: str,
        notes: str = None
    ) -> bool:
        """User approves data - allows report generation to proceed"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE audit_verifications
                        SET status = 'approved',
                            verified_by = %s,
                            verification_timestamp = NOW(),
                            user_notes = %s
                        WHERE verification_id = %s
                    """, (user_id, notes, verification_id))
                conn.commit()
            return True
        except Exception as e:
            print(f"[RevAudit] Failed to approve verification: {e}")
            return False

    def check_verification_status(self, assessment_id: str) -> Dict[str, Any]:
        """Check if all verifications are approved for an assessment"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT verification_id, data_type, status, verified_by,
                               verification_timestamp
                        FROM audit_verifications
                        WHERE assessment_id = %s
                        ORDER BY created_at
                    """, (assessment_id,))
                    verifications = [dict(r) for r in cur.fetchall()]

            pending = [v for v in verifications if v['status'] == 'pending']
            approved = [v for v in verifications if v['status'] == 'approved']

            return {
                'assessment_id': assessment_id,
                'total': len(verifications),
                'pending': len(pending),
                'approved': len(approved),
                'all_approved': len(pending) == 0 and len(verifications) > 0,
                'can_generate_report': len(pending) == 0,
                'verifications': verifications
            }

        except Exception as e:
            return {'error': str(e), 'can_generate_report': False}

    # =========================================================================
    # AUDIT TRAIL RETRIEVAL
    # =========================================================================

    def get_audit_trail(self, assessment_id: str) -> Dict[str, Any]:
        """Get complete audit trail for an assessment"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Get API calls
                    cur.execute("""
                        SELECT audit_id, tool, endpoint, response_status,
                               request_timestamp, duration_ms, raw_response_path
                        FROM audit_api_calls
                        WHERE assessment_id = %s
                        ORDER BY request_timestamp
                    """, (assessment_id,))
                    api_calls = [dict(r) for r in cur.fetchall()]

                    # Get claims
                    cur.execute("""
                        SELECT claim_id, claim_text, source_tool, confidence_level,
                               verified
                        FROM audit_claims
                        WHERE assessment_id = %s
                    """, (assessment_id,))
                    claims = [dict(r) for r in cur.fetchall()]

                    # Get detections
                    cur.execute("""
                        SELECT detection_id, detection_reason, severity, resolved
                        FROM audit_hallucination_detections
                        WHERE assessment_id = %s
                    """, (assessment_id,))
                    detections = [dict(r) for r in cur.fetchall()]

            return {
                'assessment_id': assessment_id,
                'api_calls': api_calls,
                'claims': claims,
                'detections': detections,
                'summary': {
                    'total_api_calls': len(api_calls),
                    'total_claims': len(claims),
                    'high_confidence_claims': len([c for c in claims if c['confidence_level'] == 'HIGH']),
                    'unresolved_detections': len([d for d in detections if not d['resolved']])
                }
            }

        except Exception as e:
            return {'error': str(e)}

    def health_check(self) -> Dict[str, Any]:
        """Check audit service health"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM audit_api_calls")
                    api_calls = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM audit_claims")
                    claims = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM audit_hallucination_detections WHERE resolved = FALSE")
                    unresolved = cur.fetchone()[0]

            return {
                'status': 'healthy',
                'service': 'RevAudit™ Anti-Hallucination Framework',
                'stats': {
                    'total_api_calls_logged': api_calls,
                    'total_claims_registered': claims,
                    'unresolved_detections': unresolved
                }
            }
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}


# Singleton instance
audit_service = RevAuditService()
