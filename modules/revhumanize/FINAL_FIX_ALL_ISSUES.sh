#!/bin/bash
set -e

echo "🔧 FINAL COMPREHENSIVE FIX - Adding Missing Classes & Fixing content_id"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# PART 1: Add the 3 MISSING Pydantic classes to the EXISTING file
# ═══════════════════════════════════════════════════════════════════════════

cat >> app/models/pydantic_models.py << 'MISSING_CLASSES'

# ============================================================================
# MISSING CLASSES (HumanizerValidationResult, AIDetectionResult, QAValidationResult)
# ============================================================================

class HumanizerValidationResult(BaseModel):
    """Result from humanizer validation service"""
    tier1_issues: List[Dict[str, Any]] = []
    tier2_issues: List[Dict[str, Any]] = []
    tier3_issues: List[Dict[str, Any]] = []
    eeat_score: float = 0.0
    geo_score: float = 0.0
    structural_score: float = 0.0
    final_score: float = 0.0
    status: str = "pending"
    can_auto_fix: bool = False
    needs_manual_review: bool = False

class AIDetectionResult(BaseModel):
    """Result from AI detection service"""
    ai_probability: float
    confidence: float
    transformer_score: float = 0.0
    perplexity_score: float = 0.0
    burstiness_score: float = 0.0
    pattern_score: float = 0.0
    statistical_score: float = 0.0
    verdict: str = "UNKNOWN"
    model_used: str = "unknown"

class QAValidationResult(BaseModel):
    """Result from QA validation - minimal stub"""
    score: float = 0.0
    passed: bool = False
    issues: List[str] = []
MISSING_CLASSES

echo "✅ Added 3 missing Pydantic classes"

# ═══════════════════════════════════════════════════════════════════════════
# PART 2: Fix database.py to use LOCALHOST (host.docker.internal doesn't work)
# ═══════════════════════════════════════════════════════════════════════════

cat > app/database.py << 'DBFIX'
import os
from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://rr_automation:ebx9CMvWRHuAt8AfbuQECT3e@172.17.0.1:5432/api_engine_db"
)

try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"connect_timeout": 2})
    with engine.connect() as conn:
        pass
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    DB_AVAILABLE = True
    print("✅ Database connected")
except Exception as e:
    print(f"⚠️  DB unavailable (continuing): {e}")
    SessionLocal = None
    DB_AVAILABLE = False

Base = declarative_base()

@contextmanager
def get_db() -> Generator[Optional[Session], None, None]:
    if not DB_AVAILABLE or SessionLocal is None:
        yield None
        return
    
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def get_db_session():
    """FastAPI dependency"""
    yield from get_db()
DBFIX

echo "✅ Fixed database.py with Docker bridge network IP"

# ═══════════════════════════════════════════════════════════════════════════
# PART 3: Fix main.py to use clean UUID (no broken f-strings)
# ═══════════════════════════════════════════════════════════════════════════

python3 << 'FIXMAIN'
import re

with open('app/main.py', 'r') as f:
    content = f.read()

# Add uuid import
if 'import uuid' not in content:
    content = content.replace('import os', 'import os\nimport uuid')

# Add content_id generation at function start
validate_start = '    Complete content validation pipeline\n    """'
if 'content_id = request.get_content_id()' not in content:
    content = content.replace(
        validate_start,
        validate_start + '\n    content_id = request.get_content_id()\n'
    )

# Replace all request.content_id with just content_id
content = re.sub(r'content_id=request\.content_id\b', 'content_id=content_id', content)

# Fix any remaining broken f-strings with __import__
content = re.sub(
    r'content_id or f"temp_\{__import__\("uuid"\)\.uuid4\(\)\.hex\[:12\]\}"',
    'content_id',
    content
)

with open('app/main.py', 'w') as f:
    f.write(content)

print("✅ Fixed main.py UUID handling")
FIXMAIN

# ═══════════════════════════════════════════════════════════════════════════
# PART 4: Verify all classes exist
# ═══════════════════════════════════════════════════════════════════════════

echo ""
echo "📋 Verifying ALL classes now exist:"
grep "^class " app/models/pydantic_models.py

# ═══════════════════════════════════════════════════════════════════════════
# PART 5: Deploy
# ═══════════════════════════════════════════════════════════════════════════

echo ""
echo "🚀 Deploying..."
docker-compose down
docker-compose build --no-cache
docker-compose up -d

echo ""
echo "⏳ Waiting for startup (20 seconds)..."
sleep 20

# ═══════════════════════════════════════════════════════════════════════════
# PART 6: Test
# ═══════════════════════════════════════════════════════════════════════════

echo ""
echo "🧪 Testing API:"
curl -s -X POST http://localhost:8003/api/v1/validate \
  -H "Content-Type: application/json" \
  -d '{"content":"Test content","title":"Test"}' | python3 -m json.tool 2>&1 | head -30

echo ""
echo "🧪 Running test suite:"
cd tests && ./run_all_tests.sh 2>&1 | tail -15
