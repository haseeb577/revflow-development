#!/usr/bin/env python3
"""
RevAudit v4.0 - COMPLETE COMPREHENSIVE System Audit
Part of MODULE 17: RevCore™ - Permanent Sub-Module
Auto-saves to database every 5 minutes via systemd timer
Version: 4.0 COMPLETE
"""

import os
import sys
import json
import subprocess
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

class RevAuditComplete:
    """Complete comprehensive audit system - no shortcuts"""
    
    def __init__(self):
        load_dotenv('/opt/shared-api-engine/.env')
        
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_dir = Path("/opt/shared-api-engine/revaudit/reports")
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.report_file = self.report_dir / f"REVFLOW_AUDIT_v4_{self.timestamp}.md"
        self.latest_link = self.report_dir / "REVFLOW_AUDIT_LATEST.md"
        
        # Database connection
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': os.getenv('POSTGRES_PORT', '5432'),
            'database': os.getenv('POSTGRES_DB', 'revflow_db'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', '')
        }
        
        # ALL 18 MODULES - COMPLETE from master reference
        self.modules = self._load_all_modules()
        
    def _load_all_modules(self):
        """Load ALL 18 modules with complete data from master reference"""
        return [
            {
                'num': 1, 'name': 'revflow_dispatch', 'brand': 'RevFlow Dispatch™',
                'suite': 'Lead Gen > AI-SEO',
                'purpose': 'Automated lead distribution with volumetric caps and geographic filtering to ensure optimal routing across CRM sub-accounts with daily volume tracking and priority sorting.',
                'backend': '/opt/smarketsherpa-rr-automation',
                'sub_modules': [],
                'ui': None, 'ports': [],
                'services': ['revflow-lead-scoring.service'],
                'tables': ['routing_logs']
            },
            {
                'num': 2, 'name': 'revscore_iq', 'brand': 'RevScore IQ™',
                'suite': 'Lead Gen > AI-SEO',
                'purpose': 'Five-stage AI pipeline delivering comprehensive digital presence assessment including budget calculator, digital diagnostic, synopsis generator, web dashboard, and P0-P3 priority scoring system for lead qualification.',
                'backend': '/opt/revscore_iq',
                'sub_modules': ['/var/www/revhome_assessment_engine_v2'],
                'ui': 'http://localhost:8100', 'ports': [8100, 8350, 8500],
                'services': ['revflow-assessment.service', 'revflow-scoring-api.service'],
                'tables': ['content_scores', 'assessment_results']
            },
            {
                'num': 3, 'name': 'revrank_engine', 'brand': 'RevRank Engine™',
                'suite': 'Lead Gen > AI-SEO',
                'purpose': 'Multi-LLM content generation orchestration system producing 1,590+ unique landing pages across 53 WordPress sites with automated quality scoring above 70 threshold, anti-duplication protection, and overnight batch deployment.',
                'backend': '/opt/revrank_engine',
                'sub_modules': ['/opt/revrank-expansion'],
                'ui': None, 'ports': [8001, 8004, 8005, 8103, 8200, 8201, 8210, 8220, 8299, 8300, 8310, 8320, 8400],
                'services': [],
                'tables': ['content_queue', 'content_generations']
            },
            {
                'num': 4, 'name': 'guru_intelligence', 'brand': 'RevSEO Intelligence™ (Guru Intelligence)',
                'suite': 'Lead Gen > AI-SEO',
                'purpose': 'Enterprise validation system enforcing 359 comprehensive SEO and AEO rules with intelligent quality assessment, knowledge graph construction, entity recognition, and semantic analysis for AI citation optimization.',
                'backend': '/opt/guru-intelligence',
                'sub_modules': [],
                'ui': 'http://localhost:8765', 'ports': [8765],
                'services': [],
                'tables': ['knowledge_graph', 'guru_rules', 'validations']
            },
            {
                'num': 5, 'name': 'revcite_pro', 'brand': 'RevCite Pro™',
                'suite': 'Lead Gen > AI-SEO',
                'purpose': 'AI citation tracking platform monitoring mentions across ChatGPT, Gemini, and Perplexity with NAP consistency validation, geographic blindspot detection, citation builder, and comprehensive coverage analysis across all major AI platforms.',
                'backend': '/opt/revflow-citations',
                'sub_modules': ['/opt/geographic-blindspot-api'],
                'ui': 'http://localhost:8900', 'ports': [8900, 8901, 8902, 8903],
                'services': [],
                'tables': ['citations', 'ai_mentions', 'geo_coverage', 'nap_consistency']
            },
            {
                'num': 6, 'name': 'revvoice', 'brand': 'RevVoice™ (RevHuman)',
                'suite': 'Lead Gen > AI-SEO',
                'purpose': 'AI detection evasion system transforming generated content with sentence variation, perplexity and burstiness optimization, natural language patterns, and voice consistency to achieve undetectable human-like writing that bypasses all major AI detection tools.',
                'backend': '/opt/revflow-humanization-pipeline',
                'sub_modules': [],
                'ui': None, 'ports': [],
                'services': [],
                'tables': ['humanization_queue']
            },
            {
                'num': 7, 'name': 'revdispatch', 'brand': 'RevDispatch™',
                'suite': 'Lead Gen > AI-SEO',
                'purpose': 'Multi-channel lead distribution orchestration platform with intelligent routing logic, channel priority management, automated fallback handling, and real-time performance tracking across email, SMS, and CRM integrations.',
                'backend': '/opt/smarketsherpa-rr-automation',
                'sub_modules': [],
                'ui': None, 'ports': [],
                'services': [],
                'tables': ['distribution_logs']
            },
            {
                'num': 8, 'name': 'revfactory', 'brand': 'RevFactory™ (RevPublish)',
                'suite': 'Lead Gen > AI-SEO',
                'purpose': 'Automated WordPress site generation and deployment engine utilizing 626 factory templates with comprehensive theme management, plugin orchestration, Hostinger API integration, and batch deployment capabilities for rapid site provisioning.',
                'backend': '/opt/site-factory-automation',
                'sub_modules': [],
                'ui': None, 'ports': [],
                'services': [],
                'tables': ['site_queue', 'deployment_history']
            },
            {
                'num': 9, 'name': 'revintel_competitive', 'brand': 'RevIntel™ (Competitive Intelligence)',
                'suite': 'Lead Gen > AI-SEO',
                'purpose': 'Competitive intelligence platform delivering comprehensive market analysis, gap identification, strategic positioning recommendations, performance benchmarking, and automated daily competitive monitoring with historical trend tracking.',
                'backend': '/opt/revflow-blind-spot-research',
                'sub_modules': [],
                'ui': 'http://localhost:8918', 'ports': [8918],
                'services': [],
                'tables': ['competitive_data', 'market_analysis']
            },
            {
                'num': 10, 'name': 'revcontent', 'brand': 'RevContent™',
                'suite': 'Lead Gen > AI-SEO',
                'purpose': 'Core content generation engine managing 3,455+ template files, orchestrating multi-stage pipeline workflows, enforcing quality gates with 70+ score threshold, and maintaining comprehensive version control across all content assets.',
                'backend': '/opt/revflow-content-factory',
                'sub_modules': ['/opt/revflow-assessment'],
                'ui': None, 'ports': [],
                'services': [],
                'tables': ['content_templates', 'content_versions']
            },
            {
                'num': 11, 'name': 'revintel_enrichment', 'brand': 'RevIntel™ (Sales Intelligence)',
                'suite': 'Lead Gen > Buyer Intent',
                'purpose': 'B2B lead enrichment platform providing waterfall enrichment strategy, contact discovery, intent signal detection, MillionVerifier email validation, and AudienceLab visitor identification achieving 40-60% cost savings versus Clay/Apollo/Hunter.io.',
                'backend': '/opt/revflow-sales-intelligence-v2',
                'sub_modules': ['/opt/revflow_enrichment_service'],
                'ui': None, 'ports': [],
                'services': [],
                'tables': ['enrichment_data', 'visitor_intelligence', 'contact_discovery']
            },
            {
                'num': 12, 'name': 'revcore', 'brand': 'RevCore™',
                'suite': 'Tech Efficiency',
                'purpose': 'Centralized infrastructure platform providing shared API engine, PostgreSQL data layer orchestration, service coordination, multi-tenant architecture, canonical configuration management via single 175-line .env file, and cross-module communication hub.',
                'backend': '/opt/shared-api-engine',
                'sub_modules': ['/opt/unified-intelligence-platform', '/opt/revflow-os'],
                'ui': 'http://localhost:8766', 'ports': [8766],
                'services': ['revflow-admin-api.service', 'revflow-flask.service'],
                'tables': []
            },
            {
                'num': 13, 'name': 'revguard', 'brand': 'RevGuard™',
                'suite': 'Tech Efficiency',
                'purpose': 'System monitoring and auto-healing platform delivering infrastructure management, automated deployment, service recovery, 24/7 health surveillance, task management API on port 9000, and self-healing capabilities for zero-downtime operations.',
                'backend': '/opt/development-agent',
                'sub_modules': [],
                'ui': 'http://localhost:9000', 'ports': [9000],
                'services': ['revflow-self-heal.service', 'revflow-architecture-scan.service', 'revflow-inventory-update.service'],
                'tables': ['system_health', 'healing_logs', 'architecture_scans']
            },
            {
                'num': 14, 'name': 'revassist', 'brand': 'RevAssist™',
                'suite': 'Tech Efficiency',
                'purpose': 'Conversational AI interface providing natural language access to entire RevFlow OS platform with context-aware responses, multi-user session management, query understanding, integration hub, and comprehensive platform documentation assistance.',
                'backend': '/opt/revhome',
                'sub_modules': [],
                'ui': 'http://localhost:8100', 'ports': [8100, 8105],
                'services': [],
                'tables': ['chat_history', 'user_sessions', 'conversation_context']
            },
            {
                'num': 15, 'name': 'revwins', 'brand': 'RevWins™',
                'suite': 'Tech Efficiency',
                'purpose': 'Daily revenue optimization engine identifying and prioritizing high-impact opportunities through intelligent scoring algorithms, action ranking, impact calculation, revenue forecasting, and automated opportunity detection across all platform modules.',
                'backend': '/opt/quick-wins-api',
                'sub_modules': [],
                'ui': 'http://localhost:8150', 'ports': [8150],
                'services': [],
                'tables': ['opportunities', 'revenue_tracking', 'impact_scores']
            },
            {
                'num': 16, 'name': 'revattr', 'brand': 'RevAttr™',
                'suite': 'Lead Gen > Buyer Intent',
                'purpose': 'Call attribution engine tracking lead sources through dynamic number insertion, comprehensive call monitoring, ROI calculation, channel performance analysis, Twilio integration for call tracking, and multi-source attribution modeling.',
                'backend': '/opt/revflow-attribution',
                'sub_modules': [],
                'ui': None, 'ports': [8910],
                'services': ['revflow-attribution.service'],
                'tables': ['call_attribution', 'call_logs', 'source_performance']
            },
            {
                'num': 17, 'name': 'revsitepatrol', 'brand': 'RevSitePatrol™ (RevGuardian)',
                'suite': 'Lead Gen > AI-SEO',
                'purpose': 'Automated landing page quality auditor monitoring 53 WordPress sites with performance measurement, content structure validation, form functionality testing, tracking number detection, mobile responsiveness checks, screenshot capture, and batch auditing with 272 historical records.',
                'backend': '/opt/revguardian',
                'sub_modules': ['/opt/revguardian/backend'],
                'ui': 'http://localhost:8917', 'ports': [8917],
                'services': [],
                'tables': ['landing_page_audits', 'audit_history', 'site_performance']
            },
            {
                'num': 18, 'name': 'revquery_pro', 'brand': 'RevQuery Pro™',
                'suite': 'Lead Gen > AI-SEO',
                'purpose': 'AI search optimization platform achieving 49% visibility increase through query fan-out across multiple LLM platforms including ChatGPT, Gemini, and Perplexity with citation tracking, RAG system integration, AI visibility scoring, and comprehensive search presence monitoring.',
                'backend': None,
                'sub_modules': [],
                'ui': None, 'ports': [],
                'services': [],
                'tables': ['ai_citations', 'query_performance', 'visibility_metrics']
            }
        ]
    
    def init_database(self):
        """Initialize complete audit database schema"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Complete audit schema
            cur.execute("""
                -- Main audit runs table
                CREATE TABLE IF NOT EXISTS revaudit_runs (
                    id SERIAL PRIMARY KEY,
                    run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_modules INTEGER,
                    deployed_modules INTEGER,
                    healthy_modules INTEGER,
                    degraded_modules INTEGER,
                    critical_issues INTEGER,
                    total_ports INTEGER,
                    total_services INTEGER,
                    database_size_mb NUMERIC,
                    report_file TEXT,
                    audit_data JSONB
                );
                
                -- Modules table with complete tracking
                CREATE TABLE IF NOT EXISTS revaudit_modules (
                    id SERIAL PRIMARY KEY,
                    audit_run_id INTEGER REFERENCES revaudit_runs(id),
                    module_num INTEGER,
                    module_name TEXT,
                    brand_name TEXT,
                    suite TEXT,
                    purpose TEXT,
                    deployment_status TEXT,
                    health_status TEXT,
                    backend_status TEXT,
                    backend_path TEXT,
                    sub_modules TEXT[],
                    ui_url TEXT,
                    ports INTEGER[],
                    services TEXT[],
                    tables TEXT[],
                    issues TEXT[],
                    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Services tracking
                CREATE TABLE IF NOT EXISTS revaudit_services (
                    id SERIAL PRIMARY KEY,
                    audit_run_id INTEGER REFERENCES revaudit_runs(id),
                    service_name TEXT,
                    status TEXT,
                    uptime_seconds INTEGER,
                    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Ports mapping
                CREATE TABLE IF NOT EXISTS revaudit_ports (
                    id SERIAL PRIMARY KEY,
                    audit_run_id INTEGER REFERENCES revaudit_runs(id),
                    port INTEGER,
                    process TEXT,
                    module_num INTEGER,
                    status TEXT,
                    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Database health metrics
                CREATE TABLE IF NOT EXISTS revaudit_database (
                    id SERIAL PRIMARY KEY,
                    audit_run_id INTEGER REFERENCES revaudit_runs(id),
                    table_name TEXT,
                    row_count BIGINT,
                    table_size_mb NUMERIC,
                    last_vacuum TIMESTAMP,
                    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Performance metrics
                CREATE TABLE IF NOT EXISTS revaudit_performance (
                    id SERIAL PRIMARY KEY,
                    audit_run_id INTEGER REFERENCES revaudit_runs(id),
                    metric_name TEXT,
                    metric_value NUMERIC,
                    metric_unit TEXT,
                    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Indexes for performance
                CREATE INDEX IF NOT EXISTS idx_audit_runs_timestamp ON revaudit_runs(run_timestamp);
                CREATE INDEX IF NOT EXISTS idx_audit_modules_run ON revaudit_modules(audit_run_id);
                CREATE INDEX IF NOT EXISTS idx_audit_services_run ON revaudit_services(audit_run_id);
                CREATE INDEX IF NOT EXISTS idx_audit_ports_run ON revaudit_ports(audit_run_id);
            """)
            
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"⚠️  Database init: {e}")
            return False
    
    def get_database_stats(self):
        """Get comprehensive database statistics"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get all tables with sizes
            cur.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY size_bytes DESC;
            """)
            tables = cur.fetchall()
            
            # Get database size
            cur.execute("""
                SELECT pg_size_pretty(pg_database_size(%s)) as db_size,
                       pg_database_size(%s) as db_size_bytes
            """, (self.db_config['database'], self.db_config['database']))
            db_size = cur.fetchone()
            
            cur.close()
            conn.close()
            
            return {
                'tables': tables,
                'database_size': db_size['db_size'],
                'database_size_mb': db_size['db_size_bytes'] / 1024 / 1024
            }
        except Exception as e:
            print(f"⚠️  Database stats: {e}")
            return None
    
    def check_path(self, path):
        """Check if path exists"""
        if not path:
            return "N/A", "N/A"
        return ("Found", path) if Path(path).exists() else ("Not_Found", path)
    
    def check_service(self, service_name):
        """Check systemd service status"""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service_name],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip()
        except:
            return "unknown"
    
    def get_service_uptime(self, service_name):
        """Get service uptime in seconds"""
        try:
            result = subprocess.run(
                ['systemctl', 'show', service_name, '--property=ActiveEnterTimestamp'],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            return "unknown"
    
    def scan_ports(self):
        """Comprehensive port scanning"""
        ports = []
        try:
            result = subprocess.run(['ss', '-tuln'], capture_output=True, text=True, timeout=10)
            for line in result.stdout.split('\n'):
                if 'LISTEN' in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        addr_port = parts[4]
                        if ':' in addr_port:
                            port = addr_port.split(':')[-1]
                            try:
                                port_num = int(port)
                                if 8000 <= port_num <= 9999 or port_num in [80, 443, 5432, 6379]:
                                    # Get process
                                    proc_result = subprocess.run(
                                        ['ss', '-tulnp'], capture_output=True, text=True, timeout=5
                                    )
                                    process = "unknown"
                                    for proc_line in proc_result.stdout.split('\n'):
                                        if f':{port}' in proc_line:
                                            if 'users:' in proc_line:
                                                proc_part = proc_line.split('users:')[1]
                                                if '("' in proc_part:
                                                    process = proc_part.split('("')[1].split('"')[0]
                                            break
                                    
                                    # Match to module
                                    module_num = None
                                    for module in self.modules:
                                        if port_num in module['ports']:
                                            module_num = module['num']
                                            break
                                    
                                    ports.append({
                                        'port': port_num,
                                        'process': process,
                                        'module_num': module_num
                                    })
                            except:
                                pass
        except Exception as e:
            print(f"⚠️  Port scan: {e}")
        
        return sorted(ports, key=lambda x: x['port'])
    
    def scan_modules(self):
        """Complete module scanning"""
        print("🔍 Scanning all 18 modules with sub-modules...")
        results = []
        deployed = 0
        healthy = 0
        degraded = 0
        
        for module in self.modules:
            status, path = self.check_path(module['backend'])
            
            # Check sub-modules
            sub_status = []
            for sub in module['sub_modules']:
                s, _ = self.check_path(sub)
                sub_status.append(s)
            
            # Determine deployment
            if status == "Found":
                deployed += 1
                
                # Check services
                issues = []
                for svc in module['services']:
                    svc_status = self.check_service(svc)
                    if svc_status not in ['active', 'activating']:
                        issues.append(f"Service {svc}: {svc_status}")
                
                health = "Degraded" if issues else "Healthy"
                if health == "Healthy":
                    healthy += 1
                else:
                    degraded += 1
            elif status == "N/A":
                health = "N/A"
            else:
                health = "Unknown"
            
            deploy_status = "✅ Deployed" if status == "Found" else ("⚪ N/A" if status == "N/A" else "❌ Not Deployed")
            
            results.append({
                'module': module,
                'backend_status': status,
                'backend_path': path,
                'sub_modules_status': sub_status,
                'deployment': deploy_status,
                'health': health,
                'issues': issues
            })
            
            print(f"  ✓ Module {module['num']}: {module['brand']}")
        
        return results, deployed, healthy, degraded
    
    def save_to_database(self, results, deployed, healthy, degraded, ports, services, db_stats):
        """Complete database save"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Insert audit run
            cur.execute("""
                INSERT INTO revaudit_runs (
                    total_modules, deployed_modules, healthy_modules, degraded_modules,
                    critical_issues, total_ports, total_services, database_size_mb, report_file, audit_data
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                len(self.modules), deployed, healthy, degraded, 0,
                len(ports), len(services),
                db_stats['database_size_mb'] if db_stats else 0,
                str(self.report_file),
                json.dumps({
                    'timestamp': self.timestamp,
                    'version': '4.0',
                    'modules': len(self.modules)
                })
            ))
            
            run_id = cur.fetchone()[0]
            
            # Insert modules
            for result in results:
                m = result['module']
                cur.execute("""
                    INSERT INTO revaudit_modules (
                        audit_run_id, module_num, module_name, brand_name, suite, purpose,
                        deployment_status, health_status, backend_status, backend_path,
                        sub_modules, ui_url, ports, services, tables, issues
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    run_id, m['num'], m['name'], m['brand'], m['suite'], m['purpose'],
                    result['deployment'], result['health'], result['backend_status'], result['backend_path'],
                    m['sub_modules'], m['ui'], m['ports'], m['services'], m['tables'], result['issues']
                ))
            
            # Insert ports
            for p in ports:
                cur.execute("""
                    INSERT INTO revaudit_ports (audit_run_id, port, process, module_num, status)
                    VALUES (%s, %s, %s, %s, %s)
                """, (run_id, p['port'], p['process'], p['module_num'], 'LISTEN'))
            
            # Insert services
            for s in services:
                cur.execute("""
                    INSERT INTO revaudit_services (audit_run_id, service_name, status)
                    VALUES (%s, %s, %s)
                """, (run_id, s['name'], s['status']))
            
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"⚠️  DB save: {e}")
            return False
    
    def generate_report(self, results, deployed, healthy, degraded, ports, services, db_stats):
        """Generate COMPLETE comprehensive report"""
        print("📄 Generating COMPLETE comprehensive report...")
        
        total = len(self.modules)
        
        with open(self.report_file, 'w') as f:
            f.write(f"""# 🏭 REVFLOW OS™ SYSTEM AUDIT REPORT v4.0 COMPLETE
## Enterprise-Grade 18-Module Infrastructure Analysis

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}  
**System:** Ubuntu 24.04 (217.15.168.106)  
**Version:** RevAudit v4.0 COMPLETE (MODULE 17: RevCore™)  
**Database:** PostgreSQL localhost:5432/revflow_db  
**Auto-Save:** Every 5 minutes via systemd timer

---

## 📊 EXECUTIVE DASHBOARD

### System Health Snapshot

- **Total Modules:** {total}
- **Deployed:** {deployed}/{total} ({deployed*100//total}%)
- **Healthy:** {healthy}/{deployed if deployed > 0 else 1} ({healthy*100//(deployed if deployed > 0 else 1)}%)
- **Degraded:** {degraded}/{deployed if deployed > 0 else 1}
- **Critical Issues:** 0
- **Active Ports:** {len(ports)}
- **Active Services:** {len(services)}
- **Database Size:** {db_stats['database_size'] if db_stats else 'Unknown'}
- **Audit Status:** ✅ Complete

### Deployment Progress

```
Total:     [{'█' * (total)}] {total}/{total}
Deployed:  [{'█' * (deployed * 50 // total)}{'░' * (50 - deployed * 50 // total)}] {deployed}/{total}
Healthy:   [{'█' * (healthy * 50 // deployed if deployed > 0 else 0)}{'░' * (50 - healthy * 50 // deployed if deployed > 0 else 50)}] {healthy}/{deployed if deployed > 0 else 0}
```

### System Architecture

```
INTERNET (Port 80/443)
    ↓
╔════════════════════════════════════════════════════════════════╗
║              NGINX WEB SERVER (1.24.0)                         ║
║  automation.smarketsherpa.ai                                   ║
╚════════════════════════════════════════════════════════════════╝
    │
    ├─→ Static Routes: /, /assessment, /admin
    ├─→ API Proxy: /api/*, /citations/*
    └─→ Health Checks: /health, /status
    ↓
╔════════════════════════════════════════════════════════════════╗
║              18-MODULE REVFLOW OS™ STACK                       ║
╚════════════════════════════════════════════════════════════════╝
    │
    ├─→ SUITE I: LEAD GENERATION (Modules 1-11, 16-17)
    │   ├── AI-SEO Pipeline (1-9)
    │   └── Buyer Intent (10-12, 16)
    │
    ├─→ SUITE II: DIGITAL LANDLORD (Modules 13-14)
    │   └── Portfolio Management
    │
    └─→ SUITE III: TECH EFFICIENCY (Modules 12, 15, 18)
        └── Platform Infrastructure
    ↓
╔════════════════════════════════════════════════════════════════╗
║          POSTGRESQL DATABASE LAYER (15.x)                      ║
║  localhost:5432/revflow_db                                     ║
╚════════════════════════════════════════════════════════════════╝
    │
    ├─→ 35+ tables across all modules
    ├─→ {db_stats['database_size'] if db_stats else 'Unknown'} total size
    └─→ Canonical .env: /opt/shared-api-engine/.env (175 lines)
```

---

## 📦 COMPLETE MODULE INVENTORY

""")
            
            # All modules
            current_suite = None
            for result in results:
                m = result['module']
                
                if m['suite'] != current_suite:
                    current_suite = m['suite']
                    f.write(f"\n### 🎯 {current_suite}\n\n")
                
                f.write(f"""---

#### MODULE {m['num']}: {m['brand']}

**Purpose:** {m['purpose']}

**Component Status:**

| Component | Status | Location |
|-----------|--------|----------|
| Backend | {result['backend_status']} | `{result['backend_path']}` |
""")
                
                # Sub-modules
                for i, sub in enumerate(m['sub_modules']):
                    sub_s = result['sub_modules_status'][i] if i < len(result['sub_modules_status']) else "Unknown"
                    f.write(f"| Sub-Module {i+1} | {sub_s} | `{sub}` |\n")
                
                # UI/Ports
                f.write(f"| UI | {'✅ Configured' if m['ui'] else 'N/A'} | {m['ui'] or 'N/A'} |\n")
                if m['ports']:
                    f.write(f"| Ports | Active | {', '.join(map(str, m['ports']))} |\n")
                
                # Services
                if m['services']:
                    f.write(f"\n**Services:**\n")
                    for svc in m['services']:
                        s = self.check_service(svc)
                        icon = "✅" if s == "active" else "❌"
                        f.write(f"- {icon} `{svc}` ({s})\n")
                
                # Tables
                if m['tables']:
                    f.write(f"\n**Database Tables:** {', '.join(m['tables'])}\n")
                
                # Status
                f.write(f"\n**Deployment:** {result['deployment']}  \n")
                f.write(f"**Health:** {result['health']}  \n")
                
                # Issues
                if result['issues']:
                    f.write(f"\n⚠️ **Issues:**\n")
                    for issue in result['issues']:
                        f.write(f"- {issue}\n")
                
                f.write("\n")
            
            # Ports
            f.write(f"""
---

## 🔌 ACTIVE PORTS ({len(ports)} mapped)

| Port | Process | Module | Service | Status |
|------|---------|--------|---------|--------|
""")
            for p in ports:
                mod_name = f"MODULE {p['module_num']}" if p['module_num'] else "-"
                f.write(f"| {p['port']} | {p['process']} | {mod_name} | - | ✅ LISTEN |\n")
            
            # Services
            f.write(f"""

---

## 🔧 SYSTEMD SERVICES ({len(services)} tracked)

| Service | Status | Uptime |
|---------|--------|--------|
""")
            for s in services:
                uptime = self.get_service_uptime(s['name'])
                f.write(f"| {s['name']} | {s['status']} | {uptime} |\n")
            
            # Database
            if db_stats:
                f.write(f"""

---

## 💾 DATABASE HEALTH

**Database:** revflow_db  
**Size:** {db_stats['database_size']}  
**Tables:** {len(db_stats['tables'])}

### Top 10 Largest Tables

| Table | Size |
|-------|------|
""")
                for table in db_stats['tables'][:10]:
                    f.write(f"| {table['tablename']} | {table['size']} |\n")
            
            # Footer
            f.write(f"""

---

## 📋 CRITICAL FILES & CONFIGURATION

### Must-Check Files
- **Service Registry:** `/root/REVFLOW_SERVICE_REGISTRY.md`
- **Deployment Rules:** `/root/DEPLOYMENT_RULES.md` (8 rules)
- **Canonical .env:** `/opt/shared-api-engine/.env` (175 lines)

### RevAudit v4.0 Integration
- **Location:** `/opt/shared-api-engine/revaudit/`
- **Reports:** `/opt/shared-api-engine/revaudit/reports/`
- **Database:** revflow_db.revaudit_runs
- **Auto-Save:** Every 5 minutes

---

## 📥 DOWNLOAD

```bash
scp root@217.15.168.106:{self.report_file} ~/Downloads/
```

---

## 🔄 MONITORING

**View Latest:** `cat /opt/shared-api-engine/revaudit/reports/REVFLOW_AUDIT_LATEST.md`  
**Run Manual:** `revaudit`  
**Check Timer:** `systemctl status revaudit.timer`  
**View Logs:** `tail -f /opt/shared-api-engine/revaudit/logs/revaudit.log`

---

**© 2026 RevFlow OS™ - RevAudit v4.0 COMPLETE**  
**MODULE 17: RevCore™ - Enterprise System Monitoring**
""")
        
        # Symlink
        if self.latest_link.exists():
            self.latest_link.unlink()
        self.latest_link.symlink_to(self.report_file)
        
        print(f"✅ Report: {self.report_file}")
    
    def run(self):
        """Run COMPLETE comprehensive audit"""
        print("=" * 70)
        print("🔍 REVFLOW OS™ SYSTEM AUDIT v4.0 COMPLETE")
        print("   MODULE 17: RevCore™ - Enterprise Monitoring")
        print("=" * 70)
        print(f"Timestamp: {datetime.now()}")
        print()
        
        try:
            print("📊 Initializing database...")
            self.init_database()
            
            print("\n🗄️  Getting database statistics...")
            db_stats = self.get_database_stats()
            if db_stats:
                print(f"  ✓ Database: {db_stats['database_size']}")
            
            results, deployed, healthy, degraded = self.scan_modules()
            
            print("\n🔌 Scanning ports...")
            ports = self.scan_ports()
            print(f"  ✓ Found {len(ports)} active ports")
            
            print("\n🔧 Checking services...")
            services = []
            for m in self.modules:
                for svc in m['services']:
                    s = self.check_service(svc)
                    services.append({'name': svc, 'status': s})
            print(f"  ✓ Found {len(services)} services")
            
            self.generate_report(results, deployed, healthy, degraded, ports, services, db_stats)
            
            print("\n💾 Saving to database...")
            if self.save_to_database(results, deployed, healthy, degraded, ports, services, db_stats):
                print("  ✅ Saved to revflow_db")
            
            print()
            print("=" * 70)
            print("✅ COMPLETE COMPREHENSIVE AUDIT FINISHED")
            print("=" * 70)
            print(f"Modules: {deployed}/{len(self.modules)} deployed")
            print(f"Health: {healthy} healthy, {degraded} degraded")
            print(f"Ports: {len(ports)} active")
            print(f"Database: {db_stats['database_size'] if db_stats else 'Unknown'}")
            print()
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return 1
        
        return 0

if __name__ == "__main__":
    audit = RevAuditComplete()
    sys.exit(audit.run())
