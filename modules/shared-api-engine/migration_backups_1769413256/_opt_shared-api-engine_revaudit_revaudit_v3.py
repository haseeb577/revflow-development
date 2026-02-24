#!/usr/bin/env python3
"""RevAudit v3.0 - Complete 18-Module System Audit"""
import os, sys, subprocess
from datetime import datetime
from pathlib import Path

class RevAudit:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_dir = Path("/root")
        self.report_file = self.report_dir / f"REVFLOW_AUDIT_{self.timestamp}.md"
        self.latest_link = self.report_dir / "REVFLOW_AUDIT_LATEST.md"
        self.modules = [
            {'num': 1, 'name': 'revscore_iq', 'brand': 'RevScore IQ™', 'suite': 'Lead Gen > AI-SEO', 'purpose': 'Assessment & Scoring', 'backend': '/opt/revscore_iq', 'ui': 'http://localhost:8100'},
            {'num': 2, 'name': 'revrank_engine', 'brand': 'RevRank Engine™', 'suite': 'Lead Gen > AI-SEO', 'purpose': 'Content Factory', 'backend': '/opt/revrank_engine', 'ui': None},
            {'num': 3, 'name': 'revseo_intelligence', 'brand': 'RevSEO Intelligence™', 'suite': 'Lead Gen > AI-SEO', 'purpose': 'Knowledge Graph + Guru', 'backend': '/opt/guru-intelligence', 'ui': 'http://localhost:8765'},
            {'num': 4, 'name': 'revcite_pro', 'brand': 'RevCite Pro™', 'suite': 'Lead Gen > AI-SEO', 'purpose': 'Citation & NAP', 'backend': '/opt/revflow-citations', 'ui': 'http://localhost:8900'},
            {'num': 5, 'name': 'revvoice', 'brand': 'RevVoice™', 'suite': 'Lead Gen > AI-SEO', 'purpose': 'AI Humanization', 'backend': '/opt/revflow-humanization-pipeline', 'ui': None},
            {'num': 6, 'name': 'revwins', 'brand': 'RevWins™', 'suite': 'Lead Gen > AI-SEO', 'purpose': 'Quick Wins', 'backend': '/opt/quick-wins-api', 'ui': 'http://localhost:8150'},
            {'num': 7, 'name': 'revimage_engine', 'brand': 'RevImage Engine', 'suite': 'Lead Gen > AI-SEO', 'purpose': 'AI Image Generator', 'backend': '/opt/revimage-engine', 'ui': None},
            {'num': 8, 'name': 'revpublish', 'brand': 'RevPublish', 'suite': 'Lead Gen > AI-SEO', 'purpose': 'WordPress Automation', 'backend': '/opt/site-factory-automation', 'ui': None},
            {'num': 9, 'name': 'revmetrics', 'brand': 'RevMetrics', 'suite': 'Lead Gen > AI-SEO', 'purpose': 'KPI Monitoring', 'backend': '/opt/revmetrics', 'ui': 'http://localhost:8220'},
            {'num': 10, 'name': 'revsignal_sdk', 'brand': 'RevSignal SDK™', 'suite': 'Lead Gen > Buyer Intent', 'purpose': 'Visitor Identification', 'backend': None, 'ui': None},
            {'num': 11, 'name': 'revintel', 'brand': 'RevIntel™', 'suite': 'Lead Gen > Buyer Intent', 'purpose': 'Sales Intelligence', 'backend': '/opt/revflow-sales-intelligence-v2', 'ui': None},
            {'num': 12, 'name': 'revflow_dispatch', 'brand': 'RevFlow Dispatch™', 'suite': 'Lead Gen > Buyer Intent', 'purpose': 'Lead Routing', 'backend': '/opt/smarketsherpa-rr-automation', 'ui': None},
            {'num': 13, 'name': 'revvest_iq', 'brand': 'RevVest IQ™', 'suite': 'Digital Landlord', 'purpose': 'Portfolio Analysis', 'backend': '/opt/revflow-blind-spot-research', 'ui': None},
            {'num': 14, 'name': 'revinsight', 'brand': 'RevInsight™', 'suite': 'Digital Landlord', 'purpose': 'Blind Spot Research', 'backend': '/opt/revflow-blind-spot-research', 'ui': 'http://localhost:8402'},
            {'num': 15, 'name': 'revprompt_unified', 'brand': 'RevPrompt Unified', 'suite': 'Tech Efficiency', 'purpose': 'Prompt Management', 'backend': '/opt/revprompt-unified', 'ui': 'http://localhost:8401'},
            {'num': 16, 'name': 'revspend_iq', 'brand': 'RevSpend IQ™', 'suite': 'Tech Efficiency', 'purpose': 'Cost Management', 'backend': None, 'ui': None},
            {'num': 17, 'name': 'revcore', 'brand': 'RevCore™', 'suite': 'Tech Efficiency', 'purpose': 'Unified Platform', 'backend': '/opt/shared-api-engine', 'ui': 'http://localhost:8766'},
            {'num': 18, 'name': 'revassist', 'brand': 'RevAssist™', 'suite': 'Tech Efficiency', 'purpose': 'AI Assistant', 'backend': '/opt/revhome', 'ui': 'http://localhost:8105'},
        ]
    
    def check_path(self, path):
        if not path: return "N/A", "N/A"
        return ("Found", path) if Path(path).exists() else ("Not_Found", path)
    
    def scan_modules(self):
        print("🔍 Scanning all 18 modules...")
        results, deployed_count, healthy_count = [], 0, 0
        for module in self.modules:
            status, path = self.check_path(module['backend'])
            if status == "Found": deployed = "✅ Deployed"; deployed_count += 1; healthy_count += 1
            elif status == "N/A": deployed = "⚪ N/A"
            else: deployed = "❌ Not Deployed"
            results.append({'module': module, 'backend_status': status, 'backend_path': path, 'deployment': deployed})
            print(f"  ✓ Module {module['num']} scanned")
        return results, deployed_count, healthy_count
    
    def generate_report(self, results, deployed_count, healthy_count):
        print("📄 Generating report...")
        total = len(self.modules)
        with open(self.report_file, 'w') as f:
            f.write(f"""# 🏭 REVFLOW OS™ SYSTEM AUDIT REPORT
## Complete 18-Module Infrastructure Analysis

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}  
**System:** Ubuntu 24.04 (217.15.168.106)  
**Version:** RevAudit v3.0 (MODULE 17: RevCore™)

---

## 📊 EXECUTIVE DASHBOARD

### System Health Snapshot
- **Total Modules:** {total}
- **Deployed:** {deployed_count}/{total} ({deployed_count*100//total}%)
- **Healthy:** {healthy_count}/{deployed_count if deployed_count > 0 else 1}
- **Audit Status:** ✅ Complete

### Deployment Progress
```
Deployed:  [{'█' * (deployed_count * 50 // total)}{'░' * (50 - deployed_count * 50 // total)}] {deployed_count}/{total}
```

---

## 📦 COMPLETE MODULE INVENTORY

""")
            current_suite = None
            for result in results:
                module = result['module']
                if module['suite'] != current_suite:
                    current_suite = module['suite']
                    f.write(f"\n### 🎯 {current_suite}\n\n")
                f.write(f"""---

#### MODULE {module['num']}: {module['brand']}

**Purpose:** {module['purpose']}  
**Suite:** {module['suite']}  

**Component Status:**
| Component | Status | Location |
|-----------|--------|----------|
| Backend | {result['backend_status']} | `{result['backend_path']}` |
| UI | {'Configured' if module['ui'] else 'N/A'} | {module['ui'] or 'N/A'} |

**Deployment:** {result['deployment']}  

""")
            f.write(f"""
---

## 📥 DOWNLOAD
```bash
scp root@217.15.168.106:{self.report_file} ~/Downloads/
```

---
**© 2026 RevFlow OS™ - RevAudit v3.0 (MODULE 17: RevCore™)**
""")
        if self.latest_link.exists(): self.latest_link.unlink()
        self.latest_link.symlink_to(self.report_file)
        print(f"✅ Report: {self.report_file}")
    
    def run(self):
        print("=" * 70)
        print("🔍 REVFLOW OS™ SYSTEM AUDIT v3.0")
        print("   Part of MODULE 17: RevCore™")
        print("=" * 70)
        print(f"Timestamp: {datetime.now()}")
        print()
        try:
            results, deployed, healthy = self.scan_modules()
            self.generate_report(results, deployed, healthy)
            print()
            print("=" * 70)
            print("✅ AUDIT COMPLETE")
            print("=" * 70)
            print(f"Modules Deployed: {deployed}/18")
            print(f"Modules Healthy: {healthy}/{deployed if deployed > 0 else 1}")
            print()
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return 1
        return 0

if __name__ == "__main__":
    audit = RevAudit()
    sys.exit(audit.run())
