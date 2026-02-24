"""
RevCleanup™ - Disk Space Cleanup Module
Integrated into RevAudit v4.0
"""

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import subprocess
from datetime import datetime
from pathlib import Path
import hashlib
from collections import defaultdict

router = APIRouter(prefix="/revcleanup", tags=["RevCleanup"])

# Installation artifact patterns
ARTIFACT_CATEGORIES = {
    "installers": {
        "patterns": ["*.tar.gz", "*.tgz", "*.tar.bz2", "*.zip", "*.deb"],
        "paths": ["/tmp", "/root", "/opt"],
        "description": "Downloaded installation packages"
    },
    "source_code": {
        "patterns": ["*/configure", "*/Makefile", "*/setup.py"],
        "paths": ["/tmp", "/root", "/opt"],
        "description": "Extracted source code directories"
    },
    "pip_cache": {
        "patterns": [".cache/pip", ".pip"],
        "paths": ["/root", "/home/*"],
        "description": "Python pip cache"
    },
    "npm_cache": {
        "patterns": ["npm-*", ".npm/_cacache"],
        "paths": ["/tmp", "/root/.npm"],
        "description": "NPM cache"
    },
    "build_artifacts": {
        "patterns": ["*.o", "*.a", "build/", "dist/"],
        "paths": ["/tmp", "/opt"],
        "description": "Build artifacts"
    }
}

@router.get("/status")
async def get_cleanup_status():
    """Get RevCleanup™ module status"""
    return {
        "module": "RevCleanup™",
        "status": "active",
        "version": "1.0.0",
        "description": "Disk space cleanup and artifact detection"
    }

@router.get("/disk-overview")
async def get_disk_overview():
    """Get disk space overview"""
    import psutil
    disk = psutil.disk_usage('/')
    
    return {
        "total_gb": round(disk.total / (1024**3), 2),
        "used_gb": round(disk.used / (1024**3), 2),
        "free_gb": round(disk.free / (1024**3), 2),
        "percent_used": disk.percent,
        "status": "critical" if disk.percent > 90 else "warning" if disk.percent > 80 else "healthy"
    }

@router.post("/scan/artifacts")
async def scan_artifacts(background_tasks: BackgroundTasks):
    """Scan for installation artifacts"""
    scan_id = f"artifacts_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Run scan in background
    background_tasks.add_task(perform_artifact_scan, scan_id)
    
    return {
        "scan_id": scan_id,
        "status": "started",
        "message": "Artifact scan initiated"
    }

def perform_artifact_scan(scan_id: str):
    """Perform actual artifact scan"""
    results = {}
    
    for category, config in ARTIFACT_CATEGORIES.items():
        files_found = []
        total_size = 0
        
        for path_pattern in config["paths"]:
            for pattern in config["patterns"]:
                try:
                    cmd = f"find {path_pattern} -name '{pattern}' -type f 2>/dev/null | head -100"
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
                    
                    if result.stdout:
                        for filepath in result.stdout.strip().split('\n'):
                            if os.path.exists(filepath):
                                try:
                                    size = os.path.getsize(filepath)
                                    age_days = (datetime.now().timestamp() - os.path.getmtime(filepath)) / 86400
                                    
                                    files_found.append({
                                        "path": filepath,
                                        "size_mb": round(size / (1024 * 1024), 2),
                                        "age_days": int(age_days)
                                    })
                                    total_size += size
                                except:
                                    continue
                except:
                    continue
        
        results[category] = {
            "description": config["description"],
            "file_count": len(files_found),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "files": sorted(files_found, key=lambda x: x["size_mb"], reverse=True)[:20]
        }
    
    # Save results
    save_dir = Path("/opt/shared-api-engine/revaudit/data/cleanup")
    save_dir.mkdir(parents=True, exist_ok=True)
    
    import json
    with open(save_dir / f"{scan_id}.json", 'w') as f:
        json.dump(results, f, indent=2)

@router.get("/scan/latest")
async def get_latest_scan():
    """Get latest scan results"""
    save_dir = Path("/opt/shared-api-engine/revaudit/data/cleanup")
    
    if not save_dir.exists():
        return {"error": "No scans found"}
    
    scan_files = list(save_dir.glob("artifacts_*.json"))
    if not scan_files:
        return {"error": "No scans found"}
    
    latest = max(scan_files, key=lambda p: p.stat().st_mtime)
    
    import json
    with open(latest, 'r') as f:
        return json.load(f)

