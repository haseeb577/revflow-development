#!/usr/bin/env python3
"""
RevAudit™ Layer 8: UI Health Validation
Ensures all frontend UIs are accessible and functional
"""

import subprocess
import requests
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# UI REGISTRY - All known RevFlow UIs
UI_REGISTRY = [
    {
        "name": "RevAudit Dashboard",
        "module": "RevAudit",
        "port": 3100,
        "service": "revaudit-frontend.service",
        "path": "/opt/revaudit/frontend",
        "expected_title": "RevAudit",
        "url": "http://localhost:3100",
        "public_url": None
    },
    {
        "name": "RevFlow Platform",
        "module": "RevFlow Platform",
        "port": 3200,
        "service": "revflow-platform-frontend.service",
        "path": "/opt/revflow-platform/frontend",
        "expected_title": "RevFlow OS Platform",
        "url": "http://localhost:3200",
        "public_url": None
    },
    {
        "name": "RevDispatch Admin Portal",
        "module": "RevDispatch",
        "port": 3401,
        "service": "revdispatch-real-frontend.service",
        "path": "/opt/revdispatch-real/frontend/build",
        "expected_title": "RevDispatch",
        "url": "http://localhost:3401",
        "public_url": None
    },
    {
        "name": "RevPublish Dashboard",
        "module": "RevPublish",
        "port": 3550,
        "service": "revpublish-frontend.service",
        "path": "/opt/revpublish/frontend",
        "expected_title": "RevPublish",
        "url": "http://localhost:3550",
        "public_url": None
    },
    {
        "name": "RevImage UI",
        "module": "RevImage",
        "port": 8601,
        "service": "revimage-ui.service",
        "path": "/opt/revimage-ui",
        "expected_title": "RevImage",
        "url": "http://localhost:8601",
        "public_url": None
    },
    {
        "name": "RevRank Admin (Static)",
        "module": "RevRank Engine",
        "port": None,
        "service": None,
        "path": "/var/www/automation.smarketsherpa.ai/admin",
        "expected_title": "RevFlow",
        "url": None,
        "public_url": "https://automation.smarketsherpa.ai/admin/"
    },
    {
        "name": "RevRank Admin (React)",
        "module": "RevRank Engine",
        "port": None,
        "service": None,
        "path": "/opt/revrank-admin/frontend/dist",
        "expected_title": "RevRank Admin",
        "url": None,
        "public_url": "https://automation.smarketsherpa.ai/revrank-admin/"
    },
    {
        "name": "Development Agent Dashboard",
        "module": "Dev Tools",
        "port": 9000,
        "service": None,
        "path": None,
        "expected_title": "Development Agent Dashboard",
        "url": "http://localhost:9000",
        "public_url": None
    },
    {
        "name": "MinIO Console",
        "module": "MinIO",
        "port": 9011,
        "service": "revflow-minio.service",
        "path": None,
        "expected_title": "MinIO Console",
        "url": "http://localhost:9011",
        "public_url": None
    },
]


class UIHealthValidator:
    """Layer 8: UI Health Validation for RevAudit"""
    
    def __init__(self):
        self.registry = UI_REGISTRY
        self.results = []
        
    def check_path_exists(self, ui: Dict) -> Dict:
        """Check if UI path exists and has required files"""
        path = ui.get("path")
        if not path:
            return {"status": "SKIP", "reason": "No path configured"}
        
        path_obj = Path(path)
        if not path_obj.exists():
            return {
                "status": "CRITICAL",
                "reason": f"Path does not exist: {path}",
                "fix": f"mkdir -p {path}",
                "auto_fixable": False
            }
        
        # Check for index.html or dist folder
        has_index = (path_obj / "index.html").exists()
        has_dist = (path_obj / "dist").exists()
        has_build = (path_obj / "build").exists()
        
        if has_index:
            return {"status": "PASS", "has": "index.html"}
        elif has_dist:
            dist_index = (path_obj / "dist" / "index.html").exists()
            if dist_index:
                return {"status": "PASS", "has": "dist/index.html"}
            else:
                return {
                    "status": "WARNING",
                    "reason": "dist/ exists but no index.html",
                    "fix": "npm run build",
                    "auto_fixable": True
                }
        elif has_build:
            build_index = (path_obj / "build" / "index.html").exists()
            if build_index:
                return {"status": "PASS", "has": "build/index.html"}
            else:
                return {
                    "status": "WARNING",
                    "reason": "build/ exists but no index.html",
                    "fix": "npm run build",
                    "auto_fixable": True
                }
        else:
            return {
                "status": "CRITICAL",
                "reason": "No index.html, dist/, or build/ found",
                "fix": "npm install && npm run build",
                "auto_fixable": True
            }
    
    def check_service_status(self, ui: Dict) -> Dict:
        """Check if systemd service is running"""
        service = ui.get("service")
        if not service:
            return {"status": "SKIP", "reason": "No service configured"}
        
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service],
                capture_output=True, text=True
            )
            
            if result.stdout.strip() == 'active':
                return {"status": "PASS", "service_status": "active"}
            else:
                # Check if service file exists
                svc_exists = subprocess.run(
                    ['systemctl', 'cat', service],
                    capture_output=True, text=True
                )
                
                if svc_exists.returncode != 0:
                    return {
                        "status": "CRITICAL",
                        "reason": f"Service file does not exist: {service}",
                        "fix": "Create systemd service file",
                        "auto_fixable": False
                    }
                
                return {
                    "status": "WARNING",
                    "reason": f"Service not running: {result.stdout.strip()}",
                    "fix": f"systemctl start {service}",
                    "auto_fixable": True
                }
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}
    
    def check_http_response(self, ui: Dict) -> Dict:
        """Check if UI responds to HTTP requests"""
        url = ui.get("url") or ui.get("public_url")
        if not url:
            return {"status": "SKIP", "reason": "No URL configured"}
        
        try:
            response = requests.get(url, timeout=5, verify=False)
            
            if response.status_code == 200:
                # Check for expected title
                expected_title = ui.get("expected_title", "")
                if expected_title and expected_title.lower() in response.text.lower():
                    return {
                        "status": "PASS",
                        "http_code": 200,
                        "title_match": True
                    }
                elif "<title>" in response.text:
                    # Extract actual title
                    import re
                    title_match = re.search(r'<title>([^<]+)</title>', response.text, re.IGNORECASE)
                    actual_title = title_match.group(1) if title_match else "Unknown"
                    
                    if "404" in actual_title or "Not Found" in actual_title:
                        return {
                            "status": "WARNING",
                            "reason": f"UI returns 404 page",
                            "actual_title": actual_title,
                            "fix": "Check if static files are served correctly"
                        }
                    
                    return {
                        "status": "DEGRADED",
                        "http_code": 200,
                        "expected_title": expected_title,
                        "actual_title": actual_title,
                        "title_match": False
                    }
                else:
                    return {
                        "status": "PASS",
                        "http_code": 200,
                        "note": "Response OK but no title tag found"
                    }
            else:
                return {
                    "status": "WARNING",
                    "http_code": response.status_code,
                    "reason": f"Non-200 response"
                }
        except requests.exceptions.ConnectionError:
            return {
                "status": "CRITICAL",
                "reason": "Connection refused - service not running",
                "fix": f"Check if port {ui.get('port')} is listening"
            }
        except requests.exceptions.Timeout:
            return {
                "status": "WARNING",
                "reason": "Request timed out",
                "fix": "Service may be overloaded or starting"
            }
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}
    
    def validate_ui(self, ui: Dict) -> Dict:
        """Run all validation checks for a single UI"""
        result = {
            "name": ui["name"],
            "module": ui["module"],
            "port": ui.get("port"),
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }
        
        # Run checks
        result["checks"]["path"] = self.check_path_exists(ui)
        result["checks"]["service"] = self.check_service_status(ui)
        result["checks"]["http"] = self.check_http_response(ui)
        
        # Calculate overall status
        statuses = [c.get("status", "SKIP") for c in result["checks"].values()]
        
        if "CRITICAL" in statuses:
            result["overall_status"] = "CRITICAL"
            result["score"] = 0
        elif "ERROR" in statuses:
            result["overall_status"] = "ERROR"
            result["score"] = 0
        elif "WARNING" in statuses:
            result["overall_status"] = "WARNING"
            result["score"] = 50
        elif "DEGRADED" in statuses:
            result["overall_status"] = "DEGRADED"
            result["score"] = 75
        else:
            result["overall_status"] = "PASS"
            result["score"] = 100
        
        return result
    
    def validate_all(self) -> Dict:
        """Validate all registered UIs"""
        results = []
        
        for ui in self.registry:
            result = self.validate_ui(ui)
            results.append(result)
        
        # Summary
        total = len(results)
        passing = len([r for r in results if r["overall_status"] == "PASS"])
        warnings = len([r for r in results if r["overall_status"] in ["WARNING", "DEGRADED"]])
        critical = len([r for r in results if r["overall_status"] in ["CRITICAL", "ERROR"]])
        
        return {
            "timestamp": datetime.now().isoformat(),
            "layer": 8,
            "layer_name": "UI Health Validation",
            "summary": {
                "total_uis": total,
                "passing": passing,
                "warnings": warnings,
                "critical": critical,
                "health_score": round((passing / total) * 100) if total > 0 else 0
            },
            "results": results
        }
    
    def get_broken_uis(self) -> List[Dict]:
        """Get list of UIs that need attention"""
        all_results = self.validate_all()
        broken = []
        
        for result in all_results["results"]:
            if result["overall_status"] in ["CRITICAL", "ERROR", "WARNING"]:
                broken.append({
                    "name": result["name"],
                    "module": result["module"],
                    "status": result["overall_status"],
                    "issues": [
                        {"check": k, "issue": v.get("reason", v.get("error"))}
                        for k, v in result["checks"].items()
                        if v.get("status") in ["CRITICAL", "ERROR", "WARNING"]
                    ],
                    "fixes": [
                        v.get("fix")
                        for v in result["checks"].values()
                        if v.get("fix")
                    ]
                })
        
        return broken


if __name__ == "__main__":
    import sys
    
    validator = UIHealthValidator()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "all":
            results = validator.validate_all()
            print(json.dumps(results, indent=2))
        elif sys.argv[1] == "broken":
            broken = validator.get_broken_uis()
            print(json.dumps(broken, indent=2))
        elif sys.argv[1] == "summary":
            results = validator.validate_all()
            print(f"\n📊 UI Health Summary")
            print(f"   Total UIs: {results['summary']['total_uis']}")
            print(f"   ✅ Passing: {results['summary']['passing']}")
            print(f"   ⚠️  Warnings: {results['summary']['warnings']}")
            print(f"   ❌ Critical: {results['summary']['critical']}")
            print(f"   Health Score: {results['summary']['health_score']}%")
    else:
        # Default: show summary and broken UIs
        results = validator.validate_all()
        
        print(f"\n{'='*60}")
        print(f"  RevAudit™ Layer 8: UI Health Validation")
        print(f"{'='*60}")
        print(f"\n📊 Summary:")
        print(f"   Total UIs: {results['summary']['total_uis']}")
        print(f"   ✅ Passing: {results['summary']['passing']}")
        print(f"   ⚠️  Warnings: {results['summary']['warnings']}")
        print(f"   ❌ Critical: {results['summary']['critical']}")
        print(f"   Health Score: {results['summary']['health_score']}%")
        
        broken = validator.get_broken_uis()
        if broken:
            print(f"\n❌ UIs Needing Attention:")
            for ui in broken:
                print(f"\n   {ui['name']} [{ui['status']}]")
                for issue in ui["issues"]:
                    print(f"      - {issue['check']}: {issue['issue']}")
                if ui["fixes"]:
                    print(f"      Fixes:")
                    for fix in ui["fixes"]:
                        print(f"         $ {fix}")
        else:
            print(f"\n✅ All UIs are healthy!")
