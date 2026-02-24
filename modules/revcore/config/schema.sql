-- RevCore Module 12 Database Schema
-- Database: revflow_db (existing)

-- Service Registry: All 18 RevFlow OS modules
CREATE TABLE IF NOT EXISTS revcore_service_registry (
    id SERIAL PRIMARY KEY,
    module_number INTEGER NOT NULL,
    module_name VARCHAR(255) NOT NULL UNIQUE,
    service_name VARCHAR(255),
    category VARCHAR(50) NOT NULL, -- CORE, ESSENTIAL, OPTIONAL
    port INTEGER,
    directory_path TEXT,
    auto_heal BOOLEAN DEFAULT false,
    restart_mechanism VARCHAR(100), -- systemd, docker, cron, tmux, direct
    cpu_limit_percent DECIMAL(5,2) DEFAULT 25.0,
    memory_limit_mb INTEGER DEFAULT 500,
    status VARCHAR(50) DEFAULT 'unknown',
    last_discovered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Real-time service metrics
CREATE TABLE IF NOT EXISTS revcore_service_metrics (
    id SERIAL PRIMARY KEY,
    service_id INTEGER REFERENCES revcore_service_registry(id),
    cpu_percent DECIMAL(5,2),
    memory_mb INTEGER,
    process_count INTEGER,
    port_status VARCHAR(20),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Service action audit log
CREATE TABLE IF NOT EXISTS revcore_service_actions (
    id SERIAL PRIMARY KEY,
    service_id INTEGER REFERENCES revcore_service_registry(id),
    action VARCHAR(50) NOT NULL,
    triggered_by VARCHAR(100),
    result VARCHAR(20),
    error_message TEXT,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Database connection registry
CREATE TABLE IF NOT EXISTS revcore_database_registry (
    id SERIAL PRIMARY KEY,
    db_type VARCHAR(50) NOT NULL, -- postgresql, chromadb
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL,
    database_name VARCHAR(255),
    connection_status VARCHAR(20),
    last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Port allocation registry
CREATE TABLE IF NOT EXISTS revcore_port_registry (
    id SERIAL PRIMARY KEY,
    port INTEGER NOT NULL UNIQUE,
    service_id INTEGER REFERENCES revcore_service_registry(id),
    process_name VARCHAR(255),
    status VARCHAR(20), -- active, reserved, conflict
    last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Hidden restart mechanism tracker
CREATE TABLE IF NOT EXISTS revcore_restart_mechanisms (
    id SERIAL PRIMARY KEY,
    mechanism_type VARCHAR(50) NOT NULL, -- systemd, docker, cron, tmux, screen, startup_script
    service_name VARCHAR(255),
    location TEXT,
    enabled BOOLEAN DEFAULT true,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Auto-discovery history
CREATE TABLE IF NOT EXISTS revcore_discovery_log (
    id SERIAL PRIMARY KEY,
    discovery_type VARCHAR(50) NOT NULL,
    items_found INTEGER,
    items_changed INTEGER,
    full_report JSONB,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_service_registry_module ON revcore_service_registry(module_number);
CREATE INDEX IF NOT EXISTS idx_service_metrics_service_id ON revcore_service_metrics(service_id);
CREATE INDEX IF NOT EXISTS idx_service_metrics_recorded_at ON revcore_service_metrics(recorded_at);
CREATE INDEX IF NOT EXISTS idx_service_actions_service_id ON revcore_service_actions(service_id);
CREATE INDEX IF NOT EXISTS idx_port_registry_port ON revcore_port_registry(port);
CREATE INDEX IF NOT EXISTS idx_restart_mechanisms_type ON revcore_restart_mechanisms(mechanism_type);

-- Initial data: 18 RevFlow OS Modules
INSERT INTO revcore_service_registry (module_number, module_name, service_name, category, port, directory_path) VALUES
(1, 'RevFlow Dispatch', 'smarketsherpa-platform.service', 'OPTIONAL', 8000, '/opt/smarketsherpa-rr-automation'),
(2, 'RevScore IQ', 'revflow-assessment.service', 'OPTIONAL', 8100, '/opt/revscore_iq'),
(3, 'RevRank Engine', 'revrank-engine.service', 'OPTIONAL', 8200, '/opt/revrank_engine'),
(4, 'Guru Intelligence', 'guru-intelligence.service', 'OPTIONAL', 8300, '/opt/guru-intelligence'),
(5, 'RevCite Pro', 'revflow-citations.service', 'OPTIONAL', 8901, '/opt/revflow-citations'),
(6, 'RevVoice', 'revflow-humanization.service', 'OPTIONAL', NULL, '/opt/revflow-humanization-pipeline'),
(7, 'RevDispatch', NULL, 'OPTIONAL', NULL, '/opt/smarketsherpa-rr-automation'),
(8, 'RevPublish', 'revflow-data-import.service', 'OPTIONAL', 8766, '/opt/revflow-data-import'),
(9, 'RevIntel', 'revflow-sales-intelligence.service', 'OPTIONAL', NULL, '/opt/revflow-blind-spot-research'),
(10, 'RevPublish Data Import', 'revflow-data-import.service', 'OPTIONAL', 8766, '/opt/revflow-data-import'),
(11, 'RevQuery', NULL, 'OPTIONAL', 8203, '/opt/revquery'),
(12, 'RevCore', 'revcore-api.service', 'ESSENTIAL', 8950, '/opt/revcore'),
(13, 'RevFlow Portfolio', NULL, 'OPTIONAL', NULL, NULL),
(14, 'RevFlow Management', NULL, 'OPTIONAL', NULL, NULL),
(15, 'RevWins', 'revmetrics-api.service', 'OPTIONAL', 8220, '/opt/revmetrics-api'),
(16, 'RevAudit', 'revaudit-backend.service', 'OPTIONAL', 8920, '/opt/revaudit'),
(17, 'RevShield', 'revflow-security-monitor.service', 'OPTIONAL', 8910, '/opt/revflow-security-monitor'),
(18, 'RevMetrics', NULL, 'OPTIONAL', NULL, NULL)
ON CONFLICT (module_name) DO NOTHING;

-- Core infrastructure services
INSERT INTO revcore_service_registry (module_number, module_name, service_name, category, port, auto_heal) VALUES
(0, 'PostgreSQL', 'postgresql@16-main.service', 'CORE', 5432, true),
(0, 'Nginx', 'nginx.service', 'CORE', 80, true)
ON CONFLICT (module_name) DO NOTHING;
