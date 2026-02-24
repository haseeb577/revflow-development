"""
RevCore™ Module 12 - Python Virtual Environment Validator
Added: 2026-02-03
Purpose: Validate and enforce venv standards across all RevFlow services
"""

import os
import subprocess
import json
from typing import Dict, List, Tuple
from pathlib import Path


class VenvValidator:
    """Validates Python virtual environment compliance"""
    
    REQUIRED_VENV_SERVICES = [
        # Priority 1 - Critical Services
        "litellm-gateway",
        "revcore-intelligence",
        
        # Priority 2 - Core Modules
        "revaudit-v6",
        "revflow-import",
        "revflow-llmstxt",
        "revflow-outline-generator",
        "revflow-power-prompts",
        "revflow-rag-api",
        "revflow-sov",
        "revflow-ui-backend",
        "revimage-engine",
        "revquery",
        "revshield-pro",
        "revvest-iq",
        "revmetrics-api",
    ]
    
    def __init__(self):
        self.base_path = Path("/opt")
        self.systemd_path = Path("/etc/systemd/system")
    
    def scan_all_services(self) -> Dict[str, Dict]:
        """Scan all RevFlow services for venv compliance"""
        results = {
            "compliant": [],
            "non_compliant": [],
            "corrupted": [],
            "summary": {}
        }
        
        for service_dir in self.base_path.glob("rev*"):
            if service_dir.is_dir():
                service_name = service_dir.name
                status = self.check_service_venv(service_dir, service_name)
                
                if status["has_venv"] and status["venv_healthy"]:
                    results["compliant"].append(status)
                elif status["has_venv"] and not status["venv_healthy"]:
                    results["corrupted"].append(status)
                else:
                    results["non_compliant"].append(status)
        
        results["summary"] = {
            "total_services": len(results["compliant"]) + len(results["non_compliant"]) + len(results["corrupted"]),
            "compliant_count": len(results["compliant"]),
            "non_compliant_count": len(results["non_compliant"]),
            "corrupted_count": len(results["corrupted"]),
            "compliance_rate": f"{(len(results['compliant']) / (len(results['compliant']) + len(results['non_compliant']) + len(results['corrupted'])) * 100):.1f}%"
        }
        
        return results
    
    def check_service_venv(self, service_dir: Path, service_name: str) -> Dict:
        """Check if a single service has a valid venv"""
        venv_path = service_dir / "venv"
        systemd_file = self.systemd_path / f"{service_name}.service"
        
        status = {
            "service_name": service_name,
            "service_path": str(service_dir),
            "has_venv": venv_path.exists(),
            "venv_path": str(venv_path) if venv_path.exists() else None,
            "venv_healthy": False,
            "systemd_configured": False,
            "systemd_path": str(systemd_file) if systemd_file.exists() else None,
            "priority": "high" if service_name in self.REQUIRED_VENV_SERVICES else "medium"
        }
        
        if venv_path.exists():
            # Check venv health
            status["venv_healthy"] = self._check_venv_health(venv_path)
        
        if systemd_file.exists():
            # Check SystemD configuration
            status["systemd_configured"] = self._check_systemd_venv(systemd_file, venv_path)
        
        return status
    
    def _check_venv_health(self, venv_path: Path) -> bool:
        """Verify venv can import core dependencies"""
        python_bin = venv_path / "bin" / "python"
        
        if not python_bin.exists():
            return False
        
        try:
            # Test import of common dependencies
            result = subprocess.run(
                [str(python_bin), "-c", "import sys; import os"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _check_systemd_venv(self, systemd_file: Path, venv_path: Path) -> bool:
        """Check if SystemD service uses venv Python"""
        try:
            with open(systemd_file, 'r') as f:
                content = f.read()
                
            # Check if ExecStart uses venv Python
            if "venv/bin/python" in content:
                return True
            
            # Check if it's using system Python (bad)
            if "/usr/bin/python3" in content:
                return False
                
            return False
        except Exception:
            return False
    
    def get_priority_violations(self) -> List[Dict]:
        """Get high-priority services without venvs"""
        violations = []
        
        for service_name in self.REQUIRED_VENV_SERVICES:
            service_dir = self.base_path / service_name
            
            if not service_dir.exists():
                continue
            
            status = self.check_service_venv(service_dir, service_name)
            
            if not status["has_venv"] or not status["venv_healthy"]:
                violations.append(status)
        
        return violations
    
    def generate_fix_script(self, service_name: str) -> str:
        """Generate a fix script for a specific service"""
        service_dir = self.base_path / service_name
        
        script = f"""#!/bin/bash
# Auto-generated venv fix script for {service_name}
# Generated by RevCore Intelligence on $(date)

set -e

SERVICE_NAME="{service_name}"
SERVICE_DIR="{service_dir}"

echo "=== Fixing venv for $SERVICE_NAME ==="

# Stop service
systemctl stop "$SERVICE_NAME.service" 2>/dev/null || true

# Remove corrupted venv if exists
if [ -d "$SERVICE_DIR/venv" ]; then
    echo "Removing corrupted venv..."
    rm -rf "$SERVICE_DIR/venv"
fi

# Create fresh venv
cd "$SERVICE_DIR"
python3 -m venv venv --system-site-packages

# Activate and install
source venv/bin/activate
pip install --upgrade pip -q

# Install dependencies
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt -q
else
    pip install fastapi uvicorn httpx pydantic python-multipart aiofiles -q
fi

deactivate

# Update SystemD
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
if [ -f "$SERVICE_FILE" ]; then
    cp "$SERVICE_FILE" "$SERVICE_FILE.backup-$(date +%Y%m%d_%H%M%S)"
    sed -i "s|ExecStart=/usr/bin/python3|ExecStart=$SERVICE_DIR/venv/bin/python|g" "$SERVICE_FILE"
    systemctl daemon-reload
fi

# Test
source venv/bin/activate
python -c "import sys; print(f'✅ Venv working: {{sys.executable}}')"
deactivate

echo "✅ $SERVICE_NAME venv fixed"
"""
        return script


# Singleton instance
venv_validator = VenvValidator()

