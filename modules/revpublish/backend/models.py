from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
Base = declarative_base()
class WordPressSite(Base):
    __tablename__ = "wordpress_sites"
    id = Column(Integer, primary_key=True)
    site_id = Column(String(100), unique=True, nullable=False)
    site_url = Column(String(255), nullable=False)
    wp_username = Column(String(100))
    app_password = Column(String(255))
    connection_status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
class PageTemplate(Base):
    __tablename__ = "page_templates"
    id = Column(Integer, primary_key=True)
    page_type = Column(String(50), nullable=False, unique=True)
    display_name = Column(String(255), nullable=False)
    required_fields = Column(JSON)
    optional_fields = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
class PublishedPage(Base):
    __tablename__ = "published_pages"
    id = Column(Integer, primary_key=True)
    page_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    content = Column(Text)
    status = Column(String(50), default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)
class Deployment(Base):
    __tablename__ = "deployments"
    id = Column(Integer, primary_key=True)
    page_id = Column(Integer)
    site_id = Column(Integer)
    status = Column(String(50), default="pending")
    wordpress_post_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
class ConflictDetection(Base):
    __tablename__ = "conflict_detections"
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer)
    slug = Column(String(255), nullable=False)
    existing_post_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
class ImportSession(Base):
    __tablename__ = "import_sessions"
    id = Column(Integer, primary_key=True)
    import_name = Column(String(255), nullable=False)
    page_type = Column(String(50), nullable=False)
    status = Column(String(50), default="uploading")
    total_rows = Column(Integer)
    successful_rows = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
class GoogleOAuthToken(Base):
    __tablename__ = "google_oauth_tokens"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), nullable=False, unique=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
def init_db(engine):
    Base.metadata.create_all(engine)
