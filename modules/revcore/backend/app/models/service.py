from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from app.database import Base
import enum

class ServiceStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"

class HealthStatus(str, enum.Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class Service(Base):
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True)
    service_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    display_name = Column(String(100))
    description = Column(Text)
    version = Column(String(20))
    host = Column(String(255), default="localhost")
    port = Column(Integer, nullable=False)
    base_path = Column(String(100), default="/api/v1")
    health_endpoint = Column(String(100), default="/health")
    # CRITICAL: Use values_callable to force SQLAlchemy to use enum values
    status = Column(SQLEnum(ServiceStatus, values_callable=lambda x: [e.value for e in x]), default=ServiceStatus.ACTIVE)
    health = Column(SQLEnum(HealthStatus, values_callable=lambda x: [e.value for e in x]), default=HealthStatus.UNKNOWN)
    last_health_check = Column(DateTime)
    endpoints_count = Column(Integer, default=0)
    dependencies = Column(JSON, default=list)
    config = Column(JSON, default=dict)
    registered_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "service_id": self.service_id,
            "name": self.name,
            "display_name": self.display_name,
            "port": self.port,
            "version": self.version,
            "status": self.status.value if self.status else None,
            "health": self.health.value if self.health else None,
            "registered_at": self.registered_at.isoformat() if self.registered_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
