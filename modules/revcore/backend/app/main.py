from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from app.config import settings
from app.database import get_db
from app.models.service import Service, ServiceStatus, HealthStatus

app = FastAPI(
    title="RevCore API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "service": "RevCore API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "http://217.15.168.106:8004/docs",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = "unhealthy"
        print(f"Database health check failed: {e}")
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "service": "RevCore API",
        "version": "1.0.0",
        "checks": {"database": db_status}
    }

@app.post("/api/v1/services")
def register_service(service_data: dict, db: Session = Depends(get_db)):
    existing = db.query(Service).filter(Service.service_id == service_data["service_id"]).first()
    if existing:
        for key, value in service_data.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
        existing.status = ServiceStatus.active  # This uses the enum which converts to lowercase
        db.commit()
        db.refresh(existing)
        return {"message": "Service updated", "service": existing.to_dict()}
    
    service = Service(
        service_id=service_data["service_id"],
        name=service_data["name"],
        display_name=service_data.get("display_name", service_data["name"]),
        port=service_data["port"],
        version=service_data.get("version", "1.0.0"),
        status=ServiceStatus.ACTIVE  # Enum value (lowercase in DB)
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return {"message": "Service registered", "service": service.to_dict()}

@app.get("/api/v1/services")
def list_services(db: Session = Depends(get_db)):
    services = db.query(Service).all()
    return {"total": len(services), "services": [s.to_dict() for s in services]}

@app.get("/api/v1/services/{service_id}")
def get_service(service_id: str, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.service_id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service.to_dict()

@app.delete("/api/v1/services/{service_id}")
def deregister_service(service_id: str, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.service_id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    db.delete(service)
    db.commit()
    return {"message": "Service deregistered"}
