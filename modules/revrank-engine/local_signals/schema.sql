-- RevFlow Local Signals Database Schema
-- Component 1: Local Signals (Landmarks, Neighborhoods, Climate, Events)
-- Created: February 8, 2026

-- Local landmarks table
CREATE TABLE IF NOT EXISTS local_landmarks (
    id SERIAL PRIMARY KEY,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(2) NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    osm_type VARCHAR(20),
    osm_id BIGINT,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    importance INTEGER DEFAULT 50,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(city, state, name)
);

CREATE INDEX IF NOT EXISTS idx_landmarks_city_state ON local_landmarks(city, state);
CREATE INDEX IF NOT EXISTS idx_landmarks_importance ON local_landmarks(importance DESC);

-- Local neighborhoods table
CREATE TABLE IF NOT EXISTS local_neighborhoods (
    id SERIAL PRIMARY KEY,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(2) NOT NULL,
    name VARCHAR(255) NOT NULL,
    admin_level INTEGER,
    osm_type VARCHAR(20),
    osm_id BIGINT,
    center_latitude DECIMAL(10, 8),
    center_longitude DECIMAL(11, 8),
    boundary_geojson TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(city, state, name)
);

CREATE INDEX IF NOT EXISTS idx_neighborhoods_city_state ON local_neighborhoods(city, state);

-- Local climate table
CREATE TABLE IF NOT EXISTS local_climate (
    id SERIAL PRIMARY KEY,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(2) NOT NULL,
    month INTEGER,
    avg_temp_high DECIMAL(5, 2),
    avg_temp_low DECIMAL(5, 2),
    precipitation DECIMAL(5, 2),
    snow DECIMAL(5, 2),
    extreme_cold_risk BOOLEAN DEFAULT FALSE,
    extreme_heat_risk BOOLEAN DEFAULT FALSE,
    freeze_risk BOOLEAN DEFAULT FALSE,
    climate_summary TEXT,
    service_impacts JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(city, state, month)
);

CREATE INDEX IF NOT EXISTS idx_climate_city_state ON local_climate(city, state);
CREATE INDEX IF NOT EXISTS idx_climate_month ON local_climate(month);

-- Local events table
CREATE TABLE IF NOT EXISTS local_events (
    id SERIAL PRIMARY KEY,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(2) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    start_date DATE,
    end_date DATE,
    venue VARCHAR(255),
    event_type VARCHAR(100),
    source_url TEXT,
    data_source VARCHAR(100),
    is_major BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_city_state ON local_events(city, state);
CREATE INDEX IF NOT EXISTS idx_events_date ON local_events(start_date);
CREATE INDEX IF NOT EXISTS idx_events_major ON local_events(is_major);

-- Verification query
DO $$
BEGIN
    RAISE NOTICE '✅ Schema created successfully!';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '  - local_landmarks';
    RAISE NOTICE '  - local_neighborhoods';
    RAISE NOTICE '  - local_climate';
    RAISE NOTICE '  - local_events';
END $$;
