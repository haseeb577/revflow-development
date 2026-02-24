"""
Phase 2: Approval Workflow Database Models
============================================
SQLAlchemy ORM models for pending_updates, automation_rules, update_log, etc.

Created: 2025-12-28
Location: /opt/guru-intelligence/src/models/approval.py
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Text, DECIMAL, TIMESTAMP, Boolean,
    ForeignKey, CheckConstraint, ARRAY, JSON, Index, Date
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()


class PendingUpdate(Base):
    """
    Stores rule updates awaiting approval.
    Three-path system: auto-approve, human review, or manual paste.
    """
    __tablename__ = 'pending_updates'
    
    # Primary key
    update_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Rule identification
    rule_id = Column(String(50), nullable=True)  # NULL for new rules
    rule_name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    tier = Column(Integer, nullable=False)
    definition = Column(Text, nullable=False)
    
    # Source information
    source_type = Column(
        String(50), 
        nullable=False,
        comment='google_trends, youtube, blog, rss, twitter, manual'
    )
    source_url = Column(Text, nullable=True)
    source_expert = Column(String(200), nullable=True)
    collected_date = Column(TIMESTAMP, default=datetime.utcnow)
    
    # AI Analysis
    confidence_score = Column(DECIMAL(3, 2), nullable=False)
    impact_estimate = Column(String(50), nullable=True)  # high, medium, low
    evidence_strength = Column(String(50), nullable=True)  # strong, moderate, weak
    supporting_data = Column(JSONB, nullable=True)
    
    # Approval tracking
    approval_status = Column(
        String(20), 
        default='pending',
        comment='pending, approved, rejected, merged'
    )
    approval_path = Column(
        String(20),
        nullable=True,
        comment='auto, human, manual'
    )
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(TIMESTAMP, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Deduplication
    semantic_hash = Column(String(64), nullable=True)
    similar_rules = Column(JSONB, nullable=True)  # Array of similar rule_ids
    
    # Metadata
    metadata = Column(JSONB, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    logs = relationship("UpdateLog", back_populates="update", cascade="all, delete-orphan")
    
    # Table constraints
    __table_args__ = (
        CheckConstraint('tier BETWEEN 1 AND 3', name='check_tier_range'),
        CheckConstraint(
            "source_type IN ('google_trends', 'youtube', 'blog', 'rss', 'twitter', 'manual')",
            name='check_source_type'
        ),
        CheckConstraint(
            "approval_status IN ('pending', 'approved', 'rejected', 'merged')",
            name='check_approval_status'
        ),
        CheckConstraint(
            "approval_path IN ('auto', 'human', 'manual')",
            name='check_approval_path'
        ),
        CheckConstraint(
            'confidence_score BETWEEN 0 AND 1',
            name='check_confidence_range'
        ),
        Index('idx_pending_status', 'approval_status'),
        Index('idx_pending_source', 'source_type'),
        Index('idx_pending_confidence', 'confidence_score'),
        Index('idx_pending_created', 'created_at'),
        Index('idx_pending_category', 'category'),
        Index('idx_pending_semantic', 'semantic_hash'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'update_id': self.update_id,
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'category': self.category,
            'tier': self.tier,
            'definition': self.definition,
            'source_type': self.source_type,
            'source_url': self.source_url,
            'source_expert': self.source_expert,
            'collected_date': self.collected_date.isoformat() if self.collected_date else None,
            'confidence_score': float(self.confidence_score) if self.confidence_score else None,
            'impact_estimate': self.impact_estimate,
            'evidence_strength': self.evidence_strength,
            'supporting_data': self.supporting_data,
            'approval_status': self.approval_status,
            'approval_path': self.approval_path,
            'reviewed_by': self.reviewed_by,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'rejection_reason': self.rejection_reason,
            'semantic_hash': self.semantic_hash,
            'similar_rules': self.similar_rules,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class AutomationRule(Base):
    """
    Configures auto-approval criteria.
    Example: Google Trends with 0.90+ confidence = auto-approve
    """
    __tablename__ = 'automation_rules'
    
    # Primary key
    automation_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Rule definition
    rule_name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Criteria
    source_types = Column(ARRAY(String(50)), nullable=False)
    min_confidence = Column(DECIMAL(3, 2), nullable=False, default=0.90)
    required_evidence = Column(ARRAY(String(50)), default=['strong'])
    min_tier = Column(Integer, default=1)
    max_tier = Column(Integer, default=3)
    
    # Actions
    auto_approve = Column(Boolean, default=False)
    auto_notify = Column(Boolean, default=True)
    require_human_review = Column(Boolean, default=False)
    
    # Conditions (flexible JSON)
    conditions = Column(JSONB, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=50)  # Higher = evaluated first
    
    # Metadata
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=True)
    
    # Relationships
    logs = relationship("UpdateLog", back_populates="automation_rule")
    
    __table_args__ = (
        CheckConstraint('min_confidence BETWEEN 0 AND 1', name='check_min_confidence'),
        CheckConstraint('min_tier BETWEEN 1 AND 3', name='check_min_tier'),
        CheckConstraint('max_tier BETWEEN 1 AND 3', name='check_max_tier'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'automation_id': self.automation_id,
            'rule_name': self.rule_name,
            'description': self.description,
            'source_types': self.source_types,
            'min_confidence': float(self.min_confidence) if self.min_confidence else None,
            'required_evidence': self.required_evidence,
            'min_tier': self.min_tier,
            'max_tier': self.max_tier,
            'auto_approve': self.auto_approve,
            'auto_notify': self.auto_notify,
            'require_human_review': self.require_human_review,
            'conditions': self.conditions,
            'is_active': self.is_active,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
        }


class UpdateLog(Base):
    """
    Audit trail of all approval decisions.
    Tracks who approved/rejected what and why.
    """
    __tablename__ = 'update_log'
    
    # Primary key
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    update_id = Column(Integer, ForeignKey('pending_updates.update_id', ondelete='CASCADE'))
    
    # Action details
    action = Column(
        String(50),
        nullable=False,
        comment='created, auto_approved, human_approved, rejected, merged, modified, deleted'
    )
    action_by = Column(String(100), nullable=True)  # 'system' or user ID
    action_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    # Change tracking
    previous_status = Column(String(20), nullable=True)
    new_status = Column(String(20), nullable=True)
    changes = Column(JSONB, nullable=True)  # What changed
    
    # Reasoning
    reason = Column(Text, nullable=True)
    automation_rule_id = Column(
        Integer, 
        ForeignKey('automation_rules.automation_id'),
        nullable=True
    )
    
    # Metadata
    metadata = Column(JSONB, nullable=True)
    
    # Relationships
    update = relationship("PendingUpdate", back_populates="logs")
    automation_rule = relationship("AutomationRule", back_populates="logs")
    
    __table_args__ = (
        CheckConstraint(
            "action IN ('created', 'auto_approved', 'human_approved', 'rejected', 'merged', 'modified', 'deleted')",
            name='check_action_type'
        ),
        Index('idx_log_update', 'update_id'),
        Index('idx_log_action', 'action'),
        Index('idx_log_timestamp', 'action_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'log_id': self.log_id,
            'update_id': self.update_id,
            'action': self.action,
            'action_by': self.action_by,
            'action_at': self.action_at.isoformat() if self.action_at else None,
            'previous_status': self.previous_status,
            'new_status': self.new_status,
            'changes': self.changes,
            'reason': self.reason,
            'automation_rule_id': self.automation_rule_id,
            'metadata': self.metadata,
        }


class NotificationQueue(Base):
    """
    Email/notification queue for digest reports.
    Sends daily digests and urgent alerts.
    """
    __tablename__ = 'notification_queue'
    
    # Primary key
    notification_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Target
    recipient_email = Column(String(200), nullable=False)
    notification_type = Column(
        String(50),
        nullable=False,
        comment='daily_digest, pending_review, approval_summary, urgent_alert'
    )
    
    # Content
    subject = Column(String(500), nullable=True)
    body_html = Column(Text, nullable=True)
    body_text = Column(Text, nullable=True)
    
    # Related data
    update_ids = Column(ARRAY(Integer), nullable=True)
    
    # Status
    status = Column(
        String(20),
        default='queued',
        comment='queued, sent, failed, cancelled'
    )
    scheduled_for = Column(TIMESTAMP, default=datetime.utcnow)
    sent_at = Column(TIMESTAMP, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Retry logic
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Metadata
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint(
            "notification_type IN ('daily_digest', 'pending_review', 'approval_summary', 'urgent_alert')",
            name='check_notification_type'
        ),
        CheckConstraint(
            "status IN ('queued', 'sent', 'failed', 'cancelled')",
            name='check_notification_status'
        ),
        Index('idx_notification_status', 'status'),
        Index('idx_notification_scheduled', 'scheduled_for'),
        Index('idx_notification_type', 'notification_type'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'notification_id': self.notification_id,
            'recipient_email': self.recipient_email,
            'notification_type': self.notification_type,
            'subject': self.subject,
            'body_html': self.body_html,
            'body_text': self.body_text,
            'update_ids': self.update_ids,
            'status': self.status,
            'scheduled_for': self.scheduled_for.isoformat() if self.scheduled_for else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ApprovalMetrics(Base):
    """
    Track approval workflow performance metrics.
    One row per day with aggregated statistics.
    """
    __tablename__ = 'approval_metrics'
    
    # Primary key
    metric_id = Column(Integer, primary_key=True, autoincrement=True)
    metric_date = Column(Date, nullable=False, unique=True, default=datetime.utcnow().date)
    
    # Volume metrics
    total_submissions = Column(Integer, default=0)
    auto_approved = Column(Integer, default=0)
    human_approved = Column(Integer, default=0)
    rejected = Column(Integer, default=0)
    pending = Column(Integer, default=0)
    
    # Source breakdown
    source_breakdown = Column(JSONB, nullable=True)
    
    # Quality metrics
    avg_confidence = Column(DECIMAL(3, 2), nullable=True)
    high_impact_count = Column(Integer, default=0)
    
    # Performance
    avg_review_time_hours = Column(DECIMAL(6, 2), nullable=True)
    
    # Metadata
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_metrics_date', 'metric_date'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'metric_id': self.metric_id,
            'metric_date': self.metric_date.isoformat() if self.metric_date else None,
            'total_submissions': self.total_submissions,
            'auto_approved': self.auto_approved,
            'human_approved': self.human_approved,
            'rejected': self.rejected,
            'pending': self.pending,
            'source_breakdown': self.source_breakdown,
            'avg_confidence': float(self.avg_confidence) if self.avg_confidence else None,
            'high_impact_count': self.high_impact_count,
            'avg_review_time_hours': float(self.avg_review_time_hours) if self.avg_review_time_hours else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
