"""
RevScore IQ Database Models
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Assessment(Base):
    """Main assessment record"""
    __tablename__ = "assessments"
    
    id = Column(Integer, primary_key=True)
    assessment_id = Column(String(100), unique=True, nullable=False, index=True)
    prospect_name = Column(String(255), nullable=False)
    prospect_url = Column(String(500), nullable=False)
    industry = Column(String(100))
    business_location = Column(JSON)  # {city, state, zip, lat, lng}
    service_area = Column(JSON)  # Array of locations
    contact_info = Column(JSON)  # {phone, email, contact_name}
    business_profile = Column(JSON)  # {years_in_business, employee_count, annual_revenue}
    
    # Assessment configuration
    assessment_mode = Column(String(50), default="comprehensive")  # executive, comprehensive, regional, json
    modules_selected = Column(JSON)  # Array of module letters [A, B, C, ...]
    depth_level = Column(String(20), default="standard")  # quick, standard, deep
    ai_model = Column(String(50), default="auto")
    appendices_selected = Column(JSON)  # Array of appendix IDs
    
    # Status and progress
    status = Column(String(50), default="draft")  # draft, in_progress, completed, failed
    overall_progress = Column(Integer, default=0)  # 0-100
    stage_1_status = Column(String(50), default="pending")
    stage_2_status = Column(String(50), default="pending")
    stage_3_status = Column(String(50), default="pending")
    stage_4_status = Column(String(50), default="pending")
    stage_5_status = Column(String(50), default="pending")
    
    # Results
    overall_score = Column(Float)
    letter_grade = Column(String(1))  # A, B, C, D
    p_classification = Column(String(2))  # P0, P1, P2, P3
    competitive_rank = Column(Integer)
    total_competitors = Column(Integer)
    industry_benchmark = Column(Float)
    gap_to_leader = Column(Float)
    revenue_at_risk = Column(Float)
    potential_revenue_gain = Column(Float)
    critical_issues_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Relationships
    competitors = relationship("Competitor", back_populates="assessment", cascade="all, delete-orphan")
    module_scores = relationship("ModuleScore", back_populates="assessment", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="assessment", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert assessment to dictionary, handling None values safely"""
        try:
            return {
                "id": self.id,
                "assessment_id": self.assessment_id,
                "prospect_name": self.prospect_name or "",
                "prospect_url": self.prospect_url or "",
                "status": self.status or "draft",
                "overall_score": float(self.overall_score) if self.overall_score is not None else None,
                "letter_grade": self.letter_grade or None,
                "p_classification": self.p_classification or None,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "completed_at": self.completed_at.isoformat() if self.completed_at else None
            }
        except Exception as e:
            # Fallback for any serialization errors
            return {
                "id": self.id,
                "assessment_id": getattr(self, 'assessment_id', ''),
                "prospect_name": getattr(self, 'prospect_name', ''),
                "prospect_url": getattr(self, 'prospect_url', ''),
                "status": getattr(self, 'status', 'draft'),
                "overall_score": None,
                "letter_grade": None,
                "p_classification": None,
                "created_at": None,
                "completed_at": None
            }


class Competitor(Base):
    """Competitor information for an assessment"""
    __tablename__ = "competitors"
    
    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    competitor_name = Column(String(255), nullable=False)
    competitor_url = Column(String(500), nullable=False)
    competitor_location = Column(JSON)  # {city, state}
    overall_score = Column(Float)
    letter_grade = Column(String(1))
    rank = Column(Integer)
    key_strength = Column(Text)
    key_weakness = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    assessment = relationship("Assessment", back_populates="competitors")
    module_scores = relationship("CompetitorModuleScore", back_populates="competitor", cascade="all, delete-orphan")


class ModuleScore(Base):
    """Module scores for an assessment"""
    __tablename__ = "module_scores"
    
    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    module_letter = Column(String(2), nullable=False)  # A, B, C, D, E, E1, E2, F
    module_name = Column(String(255), nullable=False)
    module_score = Column(Float, nullable=False)  # 0-100
    module_grade = Column(String(1), nullable=False)  # A, B, C, D
    status = Column(String(50))  # excellent, good, moderate, poor
    competitive_position = Column(Float)  # Points ahead/behind
    revenue_impact = Column(Float)
    summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    assessment = relationship("Assessment", back_populates="module_scores")
    component_scores = relationship("ComponentScore", back_populates="module_score", cascade="all, delete-orphan")


class ComponentScore(Base):
    """Component scores within a module"""
    __tablename__ = "component_scores"
    
    id = Column(Integer, primary_key=True)
    module_score_id = Column(Integer, ForeignKey("module_scores.id"), nullable=False)
    component_name = Column(String(255), nullable=False)
    component_key = Column(String(100), nullable=False)  # e.g., "indexation_status"
    score = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    percentage = Column(Float, nullable=False)
    grade = Column(String(1))
    status = Column(String(50))  # strong, good, moderate, poor
    details = Column(JSON)  # Component-specific data
    issues = Column(JSON)  # Array of issues found
    recommendations = Column(JSON)  # Array of recommendations
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    module_score = relationship("ModuleScore", back_populates="component_scores")


class CompetitorModuleScore(Base):
    """Module scores for competitors"""
    __tablename__ = "competitor_module_scores"
    
    id = Column(Integer, primary_key=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id"), nullable=False)
    module_letter = Column(String(2), nullable=False)
    module_score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    competitor = relationship("Competitor", back_populates="module_scores")


class Report(Base):
    """Generated reports"""
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    report_type = Column(String(50), nullable=False)  # executive, comprehensive, regional, json
    file_path = Column(String(500))
    file_url = Column(String(500))
    file_size = Column(Integer)  # bytes
    page_count = Column(Integer)
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    assessment = relationship("Assessment", back_populates="reports")


class Priority(Base):
    """Top priorities for an assessment"""
    __tablename__ = "priorities"
    
    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    priority_rank = Column(Integer, nullable=False)  # 1, 2, 3
    priority_title = Column(String(255), nullable=False)
    priority_description = Column(Text)
    module_affected = Column(String(2))
    impact = Column(String(20))  # high, medium, low
    effort_estimate = Column(String(50))  # e.g., "2-4 weeks"
    expected_lift = Column(String(50))  # e.g., "+15 points"
    created_at = Column(DateTime, default=datetime.utcnow)


class Appendix(Base):
    """Appendices library"""
    __tablename__ = "appendices"
    
    id = Column(Integer, primary_key=True)
    appendix_letter = Column(String(5), unique=True, nullable=False)  # A, B, C, ..., AF
    appendix_title = Column(String(255), nullable=False)
    appendix_description = Column(Text)
    category = Column(String(50))  # technical, strategic, content, ai, templates
    page_count = Column(Integer)
    file_path = Column(String(500))
    last_updated = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db(engine):
    """Initialize database tables"""
    Base.metadata.create_all(engine)

