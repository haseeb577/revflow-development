"""
Database setup script for RevScore IQ
"""
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from models import Base, Assessment, Competitor, ModuleScore, ComponentScore, CompetitorModuleScore, Report, Priority, Appendix

# Load environment variables
env_paths = ['../../.env', '../.env', '.env']
for path in env_paths:
    if os.path.exists(path):
        load_dotenv(path)
        break

# Database connection - use environment variables or defaults
# Docker PostgreSQL runs on port 5433 (mapped from container port 5432)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5433")  # Docker port
POSTGRES_DB = os.getenv("POSTGRES_DB", "revflow")
POSTGRES_USER = os.getenv("POSTGRES_USER", "revflow")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "revflow2026")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

def setup_database():
    """Create all database tables"""
    try:
        print(f"Connecting to database at {POSTGRES_HOST}:{POSTGRES_PORT}...")
        print(f"Database: {POSTGRES_DB}, User: {POSTGRES_USER}")
        
        engine = create_engine(DATABASE_URL)
        
        # Test connection first
        with engine.connect() as conn:
            print("SUCCESS: Database connection successful!")
        
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("SUCCESS: Database tables created successfully!")
        
        # Initialize appendices (32 appendices)
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Check if appendices already exist
        existing = session.query(Appendix).count()
        if existing == 0:
            print("Initializing appendices library...")
            appendices_data = [
                {"letter": "A", "title": "Technical SEO & On-Page Audit", "category": "technical", "page_count": 47},
                {"letter": "B", "title": "90-Day AI-SEO + GEO Roadmap", "category": "strategic", "page_count": 52},
                {"letter": "C", "title": "AI-SEO Audit Categories Matrix", "category": "technical", "page_count": 32},
                {"letter": "D", "title": "Traditional SEO vs RevAI SEO Playbook", "category": "strategic", "page_count": 41},
                {"letter": "E", "title": "Data Source & Tool Integration Matrix", "category": "technical", "page_count": 28},
                {"letter": "F", "title": "Competitive Intelligence Methodology", "category": "strategic", "page_count": 38},
                {"letter": "G", "title": "Budget & Pain Calculator", "category": "strategic", "page_count": 25},
                {"letter": "H", "title": "Sales Handoff Protocol", "category": "strategic", "page_count": 33},
                {"letter": "I", "title": "Regional Assessment Protocols", "category": "technical", "page_count": 35},
                {"letter": "J", "title": "Local Context Intelligence", "category": "content", "page_count": 40},
                {"letter": "K", "title": "Voice Modalities & Tone Framework", "category": "content", "page_count": 36},
                {"letter": "L", "title": "Proprietary Mechanism Strategy", "category": "content", "page_count": 31},
                {"letter": "M", "title": "Deep Research Protocols", "category": "content", "page_count": 45},
                {"letter": "N", "title": "Industry Knowledge Frameworks", "category": "content", "page_count": 50},
                {"letter": "O", "title": "Credible Backstory Engineering", "category": "content", "page_count": 27},
                {"letter": "P", "title": "Market Intelligence (PAA) Methodology", "category": "content", "page_count": 34},
                {"letter": "Q", "title": "Entity Density & Knowledge Graph", "category": "content", "page_count": 42},
                {"letter": "R", "title": "Quality Assurance Protocols", "category": "ai", "page_count": 37},
                {"letter": "S", "title": "Automated Quality Assurance Protocols", "category": "technical", "page_count": 29},
                {"letter": "T", "title": "Conversion Path Engineering", "category": "content", "page_count": 48},
                {"letter": "U", "title": "E-E-A-T Optimization Framework", "category": "content", "page_count": 39},
                {"letter": "V", "title": "AI Citation Testing Framework", "category": "ai", "page_count": 33},
                {"letter": "W", "title": "Schema Implementation Playbook", "category": "ai", "page_count": 46},
                {"letter": "X", "title": "NAP Consistency Framework", "category": "ai", "page_count": 30},
                {"letter": "Y", "title": "Content Templates Library", "category": "content", "page_count": 315},
                {"letter": "Z", "title": "GBP Optimization Checklist", "category": "ai", "page_count": 35},
                {"letter": "AA", "title": "Pricing & Packaging Framework", "category": "strategic", "page_count": 44},
                {"letter": "AB", "title": "Structured Data Validation", "category": "ai", "page_count": 29},
                {"letter": "AC", "title": "Complete AI-SEO-GEO Playbook", "category": "ai", "page_count": 278},
                {"letter": "AD", "title": "Communication Templates", "category": "templates", "page_count": 41},
                {"letter": "AE", "title": "Measurement & KPI Framework", "category": "templates", "page_count": 38},
                {"letter": "AF", "title": "Implementation Roadmap Template", "category": "templates", "page_count": 43}
            ]
            
            for app_data in appendices_data:
                appendix = Appendix(
                    appendix_letter=app_data["letter"],
                    appendix_title=app_data["title"],
                    appendix_description=f"Comprehensive guide for {app_data['title']}",
                    category=app_data["category"],
                    page_count=app_data["page_count"]
                )
                session.add(appendix)
            
            session.commit()
            print(f"SUCCESS: Initialized {len(appendices_data)} appendices")
        else:
            print(f"SUCCESS: Appendices already exist ({existing} entries)")
        
        session.close()
        print("SUCCESS: Database setup complete!")
        
    except Exception as e:
        print(f"ERROR: Error setting up database: {e}")
        print("\nTROUBLESHOOTING:")
        print("   1. Ensure Docker is running")
        print("   2. Start PostgreSQL container: docker-compose up -d postgres")
        print("   3. Check if PostgreSQL is accessible on port 5433")
        print(f"   4. Verify connection: {POSTGRES_HOST}:{POSTGRES_PORT}")
        print("\n   To start Docker PostgreSQL:")
        print("   cd to project root")
        print("   docker-compose -f docker-compose.modules.yml up -d postgres")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    setup_database()

