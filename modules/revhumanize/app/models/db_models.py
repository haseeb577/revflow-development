"""Database Models for Humanization Pipeline"""
from sqlalchemy import Column, String, Float, DateTime, Boolean, Text, Integer, JSON
from sqlalchemy.sql import func
from app.database import Base
import uuid

class ReviewQueueItem(Base):
    """Manual review queue for content that needs human review"""
    __tablename__ = "review_queue"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    content_id = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    title = Column(String)
    qa_score = Column(Float)
    ai_probability = Column(Float)
    tier1_issues = Column(JSON, default=list)
    tier2_issues = Column(JSON, default=list)
    tier3_issues = Column(JSON, default=list)
    status = Column(String, default="pending")
    assigned_to = Column(String)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    reviewed_at = Column(DateTime)
    reviewed_by = Column(String)

class AuditLog(Base):
    """Audit trail for all validation actions"""
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    content_id = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)
    details = Column(JSON)
    user = Column(String)
    created_at = Column(DateTime, server_default=func.now())

class WebhookConfig(Base):
    """Customer-specific webhook configurations"""
    __tablename__ = "webhook_configs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String, nullable=False, unique=True, index=True)
    webhook_url = Column(String, nullable=False)
    events = Column(JSON, default=list)
    secret_key = Column(String)
    enabled = Column(Boolean, default=True)
    retry_count = Column(Integer, default=3)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

class WebhookLog(Base):
    """Log of all webhook deliveries"""
    __tablename__ = "webhook_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    webhook_config_id = Column(String, nullable=False, index=True)
    content_id = Column(String, index=True)
    event = Column(String, nullable=False)
    payload = Column(JSON)
    response_code = Column(Integer)
    response_body = Column(Text)
    delivered_at = Column(DateTime, server_default=func.now())
    retry_attempt = Column(Integer, default=0)

class User(Base):
    """User accounts for multi-tenant authentication"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    customer_id = Column(String, index=True)
    created_at = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime)

class APIKey(Base):
    """API Keys for authentication"""
    __tablename__ = "api_keys"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    customer_id = Column(String, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
