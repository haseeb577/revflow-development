"""
Phase 2: Approval Service
==========================
Handles three-path approval workflow:
1. Auto-approve (Google Trends 0.90+)
2. Human review (Expert content)
3. Manual paste (User submissions)

Created: 2025-12-28
Location: /opt/guru-intelligence/src/services/approval_service.py
"""

import logging
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy import create_engine, and_, or_, desc, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from models.approval import (
    PendingUpdate, AutomationRule, UpdateLog, 
    NotificationQueue, ApprovalMetrics, Base
)

logger = logging.getLogger(__name__)


class ApprovalService:
    """
    Manages the approval workflow for rule updates.
    
    Features:
    - Auto-approval based on source + confidence
    - Deduplication via semantic hashing
    - Audit trail logging
    - Notification queue management
    - Integration with Knowledge Graph API
    """
    
    def __init__(self, database_url: str, knowledge_graph_url: str = None):
        """
        Initialize approval service.
        
        Args:
            database_url: PostgreSQL connection string
            knowledge_graph_url: URL to Knowledge Graph API (optional)
        """
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.knowledge_graph_url = knowledge_graph_url
        
        logger.info("ApprovalService initialized")
    
    def create_tables(self):
        """Create all approval workflow tables"""
        Base.metadata.create_all(self.engine)
        logger.info("✅ Approval workflow tables created")
    
    def submit_update(
        self,
        rule_name: str,
        category: str,
        tier: int,
        definition: str,
        source_type: str,
        confidence_score: float,
        impact_estimate: str = "medium",
        evidence_strength: str = "moderate",
        supporting_data: Dict[str, Any] = None,
        source_url: str = None,
        source_expert: str = None,
        rule_id: str = None,  # For updates to existing rules
        metadata: Dict[str, Any] = None
    ) -> Tuple[int, str]:
        """
        Submit a new rule update for approval.
        
        Returns:
            (update_id, approval_path): ID of created update and path taken
        """
        session = self.SessionLocal()
        
        try:
            # Generate semantic hash for deduplication
            semantic_hash = self._generate_semantic_hash(definition)
            
            # Check for duplicates
            similar_rules = self._find_similar_rules(session, semantic_hash, category)
            
            # Create pending update
            update = PendingUpdate(
                rule_id=rule_id,
                rule_name=rule_name,
                category=category,
                tier=tier,
                definition=definition,
                source_type=source_type,
                source_url=source_url,
                source_expert=source_expert,
                confidence_score=confidence_score,
                impact_estimate=impact_estimate,
                evidence_strength=evidence_strength,
                supporting_data=supporting_data or {},
                semantic_hash=semantic_hash,
                similar_rules=similar_rules,
                metadata=metadata or {}
            )
            
            session.add(update)
            session.flush()  # Get update_id
            
            # Log creation
            self._log_action(
                session,
                update.update_id,
                action='created',
                action_by='system',
                new_status='pending',
                reason=f'Submitted from {source_type}'
            )
            
            # Check for auto-approval
            approval_path = self._check_auto_approval(session, update)
            
            if approval_path == 'auto':
                # Auto-approve immediately
                self._auto_approve_update(session, update)
                logger.info(f"✅ Update {update.update_id} auto-approved")
            else:
                # Queue for human review
                self._queue_notification(
                    session,
                    recipient_email='shimon@smarketsherpa.ai',  # TODO: Make configurable
                    notification_type='pending_review',
                    update_ids=[update.update_id],
                    subject=f'New {source_type} rule pending review',
                    body_text=f'Rule: {rule_name}\nConfidence: {confidence_score}\nCategory: {category}'
                )
                logger.info(f"📋 Update {update.update_id} queued for review ({approval_path})")
            
            session.commit()
            return update.update_id, approval_path
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error in submit_update: {e}")
            raise
        finally:
            session.close()
    
    def _generate_semantic_hash(self, text: str) -> str:
        """
        Generate semantic hash for deduplication.
        Uses SHA256 of normalized text.
        """
        # Normalize: lowercase, strip whitespace, remove punctuation
        normalized = text.lower().strip().replace('.', '').replace(',', '')
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def _find_similar_rules(
        self, 
        session: Session, 
        semantic_hash: str, 
        category: str
    ) -> List[str]:
        """
        Find similar rules to prevent duplicates.
        Returns list of similar rule IDs.
        """
        # Exact hash match in same category
        similar = session.query(PendingUpdate.rule_id).filter(
            and_(
                PendingUpdate.semantic_hash == semantic_hash,
                PendingUpdate.category == category,
                PendingUpdate.approval_status != 'rejected'
            )
        ).limit(5).all()
        
        return [r[0] for r in similar if r[0]]
    
    def _check_auto_approval(self, session: Session, update: PendingUpdate) -> str:
        """
        Check if update qualifies for auto-approval.
        
        Returns:
            'auto' = auto-approve
            'human' = needs human review
            'manual' = manual submission
        """
        if update.source_type == 'manual':
            return 'manual'
        
        # Get matching automation rules
        automation_rule = session.query(AutomationRule).filter(
            and_(
                AutomationRule.is_active == True,
                AutomationRule.source_types.contains([update.source_type]),
                AutomationRule.min_confidence <= update.confidence_score,
                AutomationRule.min_tier <= update.tier,
                AutomationRule.max_tier >= update.tier
            )
        ).order_by(desc(AutomationRule.priority)).first()
        
        if automation_rule and automation_rule.auto_approve:
            update.approval_path = 'auto'
            return 'auto'
        else:
            update.approval_path = 'human'
            return 'human'
    
    def _auto_approve_update(self, session: Session, update: PendingUpdate):
        """Auto-approve an update and push to Knowledge Graph"""
        update.approval_status = 'approved'
        update.approval_path = 'auto'
        update.reviewed_by = 'system'
        update.reviewed_at = datetime.utcnow()
        
        # Log approval
        self._log_action(
            session,
            update.update_id,
            action='auto_approved',
            action_by='system',
            previous_status='pending',
            new_status='approved',
            reason=f'Auto-approved: {update.source_type} with {update.confidence_score} confidence'
        )
        
        # Push to Knowledge Graph (if URL configured)
        if self.knowledge_graph_url:
            try:
                self._push_to_knowledge_graph(update)
            except Exception as e:
                logger.error(f"Failed to push to Knowledge Graph: {e}")
                # Don't fail the approval, just log the error
        
        # Queue success notification
        self._queue_notification(
            session,
            recipient_email='shimon@smarketsherpa.ai',
            notification_type='approval_summary',
            update_ids=[update.update_id],
            subject=f'Rule auto-approved: {update.rule_name}',
            body_text=f'Auto-approved from {update.source_type}\nConfidence: {update.confidence_score}'
        )
    
    def approve_update(
        self, 
        update_id: int, 
        reviewed_by: str, 
        reason: str = None
    ) -> bool:
        """
        Manually approve an update (human decision).
        
        Args:
            update_id: ID of update to approve
            reviewed_by: User who approved
            reason: Optional reason for approval
            
        Returns:
            True if successful
        """
        session = self.SessionLocal()
        
        try:
            update = session.query(PendingUpdate).filter_by(
                update_id=update_id,
                approval_status='pending'
            ).first()
            
            if not update:
                logger.warning(f"Update {update_id} not found or already processed")
                return False
            
            update.approval_status = 'approved'
            update.approval_path = 'human'
            update.reviewed_by = reviewed_by
            update.reviewed_at = datetime.utcnow()
            
            # Log approval
            self._log_action(
                session,
                update_id,
                action='human_approved',
                action_by=reviewed_by,
                previous_status='pending',
                new_status='approved',
                reason=reason or 'Manual approval'
            )
            
            # Push to Knowledge Graph
            if self.knowledge_graph_url:
                try:
                    self._push_to_knowledge_graph(update)
                except Exception as e:
                    logger.error(f"Failed to push to Knowledge Graph: {e}")
            
            session.commit()
            logger.info(f"✅ Update {update_id} approved by {reviewed_by}")
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error in approve_update: {e}")
            raise
        finally:
            session.close()
    
    def reject_update(
        self,
        update_id: int,
        reviewed_by: str,
        reason: str
    ) -> bool:
        """
        Reject an update.
        
        Args:
            update_id: ID of update to reject
            reviewed_by: User who rejected
            reason: Reason for rejection
            
        Returns:
            True if successful
        """
        session = self.SessionLocal()
        
        try:
            update = session.query(PendingUpdate).filter_by(
                update_id=update_id,
                approval_status='pending'
            ).first()
            
            if not update:
                logger.warning(f"Update {update_id} not found or already processed")
                return False
            
            update.approval_status = 'rejected'
            update.reviewed_by = reviewed_by
            update.reviewed_at = datetime.utcnow()
            update.rejection_reason = reason
            
            # Log rejection
            self._log_action(
                session,
                update_id,
                action='rejected',
                action_by=reviewed_by,
                previous_status='pending',
                new_status='rejected',
                reason=reason
            )
            
            session.commit()
            logger.info(f"❌ Update {update_id} rejected by {reviewed_by}")
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error in reject_update: {e}")
            raise
        finally:
            session.close()
    
    def _push_to_knowledge_graph(self, update: PendingUpdate):
        """
        Push approved rule to Knowledge Graph API.
        
        This should call the Knowledge Graph API to create/update the rule.
        For now, just log (to be implemented with actual API client).
        """
        logger.info(f"📤 Pushing to Knowledge Graph: {update.rule_name}")
        
        # TODO: Implement actual API call
        # import requests
        # response = requests.post(
        #     f"{self.knowledge_graph_url}/api/v1/rules",
        #     json={
        #         "rule_id": update.rule_id or f"GURU_{update.update_id}",
        #         "rule_name": update.rule_name,
        #         "category": update.category,
        #         "tier": update.tier,
        #         "definition": update.definition,
        #         # ... other fields
        #     }
        # )
        # response.raise_for_status()
    
    def _log_action(
        self,
        session: Session,
        update_id: int,
        action: str,
        action_by: str,
        previous_status: str = None,
        new_status: str = None,
        reason: str = None,
        changes: Dict = None,
        automation_rule_id: int = None
    ):
        """Log an action to the audit trail"""
        log = UpdateLog(
            update_id=update_id,
            action=action,
            action_by=action_by,
            previous_status=previous_status,
            new_status=new_status,
            reason=reason,
            changes=changes,
            automation_rule_id=automation_rule_id
        )
        session.add(log)
    
    def _queue_notification(
        self,
        session: Session,
        recipient_email: str,
        notification_type: str,
        update_ids: List[int],
        subject: str,
        body_text: str,
        body_html: str = None
    ):
        """Queue a notification for sending"""
        notification = NotificationQueue(
            recipient_email=recipient_email,
            notification_type=notification_type,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            update_ids=update_ids
        )
        session.add(notification)
    
    def get_pending_updates(
        self,
        source_type: str = None,
        min_confidence: float = None,
        category: str = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get list of pending updates with optional filters.
        
        Returns list sorted by priority (confidence, then date).
        """
        session = self.SessionLocal()
        
        try:
            query = session.query(PendingUpdate).filter_by(approval_status='pending')
            
            if source_type:
                query = query.filter_by(source_type=source_type)
            if min_confidence:
                query = query.filter(PendingUpdate.confidence_score >= min_confidence)
            if category:
                query = query.filter_by(category=category)
            
            # Sort by confidence (high to low), then date (old to new)
            updates = query.order_by(
                desc(PendingUpdate.confidence_score),
                PendingUpdate.created_at
            ).limit(limit).all()
            
            return [u.to_dict() for u in updates]
            
        finally:
            session.close()
    
    def get_update_stats(self) -> Dict[str, Any]:
        """Get approval workflow statistics"""
        session = self.SessionLocal()
        
        try:
            # Count by status
            total = session.query(func.count(PendingUpdate.update_id)).scalar()
            pending = session.query(func.count(PendingUpdate.update_id)).filter_by(
                approval_status='pending'
            ).scalar()
            approved = session.query(func.count(PendingUpdate.update_id)).filter_by(
                approval_status='approved'
            ).scalar()
            rejected = session.query(func.count(PendingUpdate.update_id)).filter_by(
                approval_status='rejected'
            ).scalar()
            
            # Auto vs human approval
            auto_approved = session.query(func.count(PendingUpdate.update_id)).filter_by(
                approval_path='auto'
            ).scalar()
            
            # Average confidence
            avg_confidence = session.query(
                func.avg(PendingUpdate.confidence_score)
            ).filter_by(approval_status='pending').scalar()
            
            # Source breakdown
            source_counts = session.query(
                PendingUpdate.source_type,
                func.count(PendingUpdate.update_id)
            ).filter_by(approval_status='pending').group_by(
                PendingUpdate.source_type
            ).all()
            
            return {
                'total_submissions': total or 0,
                'pending': pending or 0,
                'approved': approved or 0,
                'rejected': rejected or 0,
                'auto_approved': auto_approved or 0,
                'avg_confidence': float(avg_confidence) if avg_confidence else 0.0,
                'source_breakdown': {source: count for source, count in source_counts},
                'approval_rate': round((approved / total * 100), 2) if total > 0 else 0.0
            }
            
        finally:
            session.close()
    
    def process_notification_queue(self, max_retries: int = 3):
        """
        Process queued notifications.
        Called by scheduler to send pending emails.
        """
        session = self.SessionLocal()
        
        try:
            # Get queued notifications
            notifications = session.query(NotificationQueue).filter(
                and_(
                    NotificationQueue.status == 'queued',
                    NotificationQueue.scheduled_for <= datetime.utcnow(),
                    NotificationQueue.retry_count < max_retries
                )
            ).limit(10).all()
            
            for notification in notifications:
                try:
                    # TODO: Implement actual email sending
                    # For now, just mark as sent
                    notification.status = 'sent'
                    notification.sent_at = datetime.utcnow()
                    logger.info(f"📧 Notification {notification.notification_id} sent")
                    
                except Exception as e:
                    notification.retry_count += 1
                    notification.error_message = str(e)
                    if notification.retry_count >= max_retries:
                        notification.status = 'failed'
                    logger.error(f"Failed to send notification {notification.notification_id}: {e}")
            
            session.commit()
            
        finally:
            session.close()


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Initialize service
    service = ApprovalService(
        database_url="postgresql://knowledge_admin:password@localhost:5434/knowledge_graph_db",
        knowledge_graph_url="http://localhost:8102"
    )
    
    # Create tables
    service.create_tables()
    
    # Submit a test update
    update_id, path = service.submit_update(
        rule_name="Test Rule",
        category="SEO",
        tier=1,
        definition="This is a test rule definition",
        source_type="google_trends",
        confidence_score=0.92,
        impact_estimate="high",
        evidence_strength="strong"
    )
    
    print(f"✅ Created update {update_id} via {path} path")
    
    # Get stats
    stats = service.get_update_stats()
    print(f"📊 Stats: {stats}")
