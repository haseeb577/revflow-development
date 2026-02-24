-- RevPublish Database Schema
-- Run this SQL script to create the required tables

-- WordPress Sites Table
CREATE TABLE IF NOT EXISTS wordpress_sites (
    id SERIAL PRIMARY KEY,
    site_id VARCHAR(255) UNIQUE NOT NULL,
    site_name VARCHAR(255) NOT NULL,
    site_url VARCHAR(500) NOT NULL,
    wp_username VARCHAR(255),
    app_password TEXT,
    connection_status VARCHAR(50) DEFAULT 'pending',
    last_connection_test TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on site_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_wordpress_sites_site_id ON wordpress_sites(site_id);
CREATE INDEX IF NOT EXISTS idx_wordpress_sites_status ON wordpress_sites(status);

-- Content Queue Table (if needed)
CREATE TABLE IF NOT EXISTS content_queue (
    id SERIAL PRIMARY KEY,
    site_id VARCHAR(255) REFERENCES wordpress_sites(site_id),
    content_type VARCHAR(100),
    content_data JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Deployments Table (if needed)
CREATE TABLE IF NOT EXISTS deployments (
    id SERIAL PRIMARY KEY,
    site_id VARCHAR(255) REFERENCES wordpress_sites(site_id),
    deployment_data JSONB,
    status VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Grant permissions (adjust user as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO revflow;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO revflow;

