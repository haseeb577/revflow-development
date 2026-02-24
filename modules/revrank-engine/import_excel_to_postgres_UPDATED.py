#!/usr/bin/env python3
"""
SmarketSherpa R&R Automation - Excel to PostgreSQL Import (UPDATED)
Imports 53 PUBLISHED sites with corrected site ID extraction
"""

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import json
import re
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/opt/revrank_engine/.env')

# Database connection from environment
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'revrank_portfolio'),
    'user': os.getenv('DB_USER', 'revrank'),
    'password': os.getenv('DB_PASSWORD')
}

# Excel file path
EXCEL_FILE = '/opt/revrank_engine/SmarketSherpa_Digital_Landlord_websites__Shimon_and_Gianina_Sites_.xlsx'

def extract_site_id(site_id_str):
    """
    Extract actual site ID from malformed Excel column
    Input: "site_id — site_001, site_002"
    Output: "site_002"
    """
    if pd.isna(site_id_str):
        return None
    
    # Look for pattern like "site_XXX" after a comma
    match = re.search(r',\s*(site_\d+)', str(site_id_str))
    if match:
        return match.group(1)
    
    # If no comma, try to extract last site_XXX pattern
    match = re.search(r'(site_\d+)(?!.*site_\d)', str(site_id_str))
    if match:
        return match.group(1)
    
    return None

def create_schema(cursor):
    """Create PostgreSQL schema for portfolio"""
    
    cursor.execute("""
    DROP TABLE IF EXISTS rr_sites CASCADE;
    
    CREATE TABLE rr_sites (
        id SERIAL PRIMARY KEY,
        site_id VARCHAR(100) UNIQUE NOT NULL,
        business_name VARCHAR(255) NOT NULL,
        domain VARCHAR(255) NOT NULL,
        category VARCHAR(100),
        
        -- Technical Status
        domain_connected BOOLEAN DEFAULT FALSE,
        site_published BOOLEAN DEFAULT FALSE,
        ssl_generated BOOLEAN DEFAULT FALSE,
        indexed_by_google BOOLEAN DEFAULT FALSE,
        
        -- Location
        city VARCHAR(100),
        state VARCHAR(50),
        address TEXT,
        property_type VARCHAR(100),
        
        -- Contact
        area_codes VARCHAR(100),
        phone VARCHAR(50),
        email VARCHAR(255),
        owner_name VARCHAR(255),
        
        -- SEO
        backlinks TEXT[], -- Array of backlink URLs
        services_list TEXT,
        service_area TEXT,
        company_backstory TEXT,
        
        -- Scoring & Tiers
        tier VARCHAR(20), -- ACTIVATE, WATCHLIST, SUNSET
        score DECIMAL(3,2), -- 0.00-5.00
        monthly_potential INTEGER, -- Expected monthly revenue
        
        -- Content Generation (V3.0 Integration)
        content_generated BOOLEAN DEFAULT FALSE,
        last_content_update TIMESTAMP,
        geo_quality_score INTEGER, -- 0-100 (GEO Quality Score)
        
        -- Metadata
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );
    
    -- Create indexes
    CREATE INDEX idx_site_id ON rr_sites(site_id);
    CREATE INDEX idx_category ON rr_sites(category);
    CREATE INDEX idx_tier ON rr_sites(tier);
    CREATE INDEX idx_score ON rr_sites(score DESC);
    CREATE INDEX idx_published ON rr_sites(site_published);
    """)
    
    print("✅ Schema created")

def parse_city_state(location_str):
    """Parse 'City, State' into separate fields"""
    if pd.isna(location_str):
        return None, None
    
    parts = str(location_str).split(',')
    if len(parts) >= 2:
        return parts[0].strip(), parts[1].strip()
    return parts[0].strip(), None

def parse_backlinks(row):
    """Extract backlinks from three backlink columns"""
    backlinks = []
    for col in ['backlink', 'backlink.1', 'backlink.2']:
        val = row.get(col)
        if pd.notna(val) and str(val).strip():
            backlinks.append(str(val).strip())
    return backlinks

def import_sites(cursor, df):
    """Import sites from DataFrame - PUBLISHED SITES ONLY"""
    
    # Filter to published sites only
    df_published = df[df['Site published? '] == 1.0].copy()
    print(f"   Filtering to {len(df_published)} published sites (out of {len(df)} total)")
    
    # Extract clean site IDs
    df_published['clean_site_id'] = df_published['Site ID'].apply(extract_site_id)
    
    # Remove any rows where site ID extraction failed
    df_published = df_published[df_published['clean_site_id'].notna()]
    print(f"   Successfully extracted {len(df_published)} site IDs")
    
    sites_data = []
    
    for idx, row in df_published.iterrows():
        city, state = parse_city_state(row.get('City and State'))
        backlinks = parse_backlinks(row)
        
        site = {
            'site_id': row['clean_site_id'],
            'business_name': row.get('Business Names', 'Unknown Business'),
            'domain': row.get('Domain purchased', ''),
            'category': row.get('Category', 'Uncategorized'),
            
            # Technical Status (convert 1.0 to True)
            'domain_connected': bool(row.get('Domain connected? ') == 1.0),
            'site_published': bool(row.get('Site published? ') == 1.0),
            'ssl_generated': bool(row.get('SSL generated?') == 1.0),
            'indexed_by_google': bool(row.get('indexed by google') == 1.0),
            
            # Location
            'city': city,
            'state': state,
            'address': row.get('address ') if pd.notna(row.get('address ')) else None,
            'property_type': row.get('property type') if pd.notna(row.get('property type')) else None,
            
            # Contact
            'area_codes': str(row.get('Area code/s')) if pd.notna(row.get('Area code/s')) else None,
            'phone': str(row.get('phone number ')) if pd.notna(row.get('phone number ')) else None,
            'email': row.get('Email') if pd.notna(row.get('Email')) else None,
            'owner_name': row.get('Owner name') if pd.notna(row.get('Owner name')) else None,
            
            # SEO
            'backlinks': backlinks,
            'services_list': row.get('Services_List') if pd.notna(row.get('Services_List')) else None,
            'service_area': row.get('Service_Area') if pd.notna(row.get('Service_Area')) else None,
            'company_backstory': row.get('Company_Backstory') if pd.notna(row.get('Company_Backstory')) else None,
        }
        
        sites_data.append(site)
    
    # Bulk insert
    columns = list(sites_data[0].keys())
    values = [[site[col] for col in columns] for site in sites_data]
    
    insert_query = f"""
    INSERT INTO rr_sites ({', '.join(columns)})
    VALUES %s
    ON CONFLICT (site_id) DO UPDATE SET
        business_name = EXCLUDED.business_name,
        domain = EXCLUDED.domain,
        category = EXCLUDED.category,
        updated_at = NOW()
    """
    
    execute_values(cursor, insert_query, values, template=None, page_size=100)
    
    print(f"✅ Imported {len(sites_data)} sites")

def calculate_scores(cursor):
    """Calculate tier assignments and scores - matches tier analysis"""
    
    # ACTIVATE Tier 1: Highest-value categories (Concrete, Roofing, Water Damage)
    cursor.execute("""
    UPDATE rr_sites 
    SET 
        tier = 'ACTIVATE',
        score = 4.0,
        monthly_potential = 2000
    WHERE category IN ('Concrete', 'Roofing', 'Water damage restoration')
    """)
    
    # ACTIVATE Tier 2: High-value categories (Electric, Fence, Tree Care, Plumbing)
    cursor.execute("""
    UPDATE rr_sites 
    SET 
        tier = 'ACTIVATE',
        score = 3.7,
        monthly_potential = 1500
    WHERE category IN ('Electric', 'Fence', 'Tree Care', 'Plumbing')
        AND tier IS NULL
    """)
    
    # WATCHLIST: Medium-value categories
    cursor.execute("""
    UPDATE rr_sites 
    SET 
        tier = 'WATCHLIST',
        score = 3.3,
        monthly_potential = 1000
    WHERE category IN ('Drywall', 'Carpentry', 'Landscaping', 'Masonry', 'Painting')
        AND tier IS NULL
    """)
    
    # SUNSET: Low-value categories
    cursor.execute("""
    UPDATE rr_sites 
    SET 
        tier = 'SUNSET',
        score = 2.5,
        monthly_potential = 500
    WHERE tier IS NULL
    """)
    
    print("✅ Scores and tiers calculated")
    
    # Show distribution
    cursor.execute("""
    SELECT tier, COUNT(*) as count, SUM(monthly_potential) as revenue
    FROM rr_sites 
    GROUP BY tier 
    ORDER BY tier
    """)
    
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]} sites (${row[2]:,}/month)")

def main():
    """Main import process"""
    
    print("=" * 80)
    print("SMARKETSHERPA R&R AUTOMATION - EXCEL IMPORT (UPDATED)")
    print("=" * 80)
    
    # Read Excel
    print("\n📊 Reading Excel file...")
    try:
        df = pd.read_excel(EXCEL_FILE)
        print(f"   Found {len(df)} sites")
    except FileNotFoundError:
        print(f"❌ ERROR: Excel file not found at {EXCEL_FILE}")
        print("   Please update EXCEL_FILE path in script")
        return
    
    # Connect to PostgreSQL
    print("\n🔌 Connecting to PostgreSQL...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print(f"   Connected to {DB_CONFIG['database']}")
    except Exception as e:
        print(f"❌ ERROR: Could not connect to PostgreSQL")
        print(f"   {str(e)}")
        return
    
    try:
        # Create schema
        print("\n🏗️  Creating schema...")
        create_schema(cursor)
        conn.commit()
        
        # Import sites
        print("\n📥 Importing sites...")
        import_sites(cursor, df)
        conn.commit()
        
        # Calculate scores
        print("\n🎯 Calculating scores...")
        calculate_scores(cursor)
        conn.commit()
        
        # Final stats
        cursor.execute("SELECT COUNT(*), SUM(monthly_potential) FROM rr_sites")
        total_sites, total_revenue = cursor.fetchone()
        
        print("\n" + "=" * 80)
        print("✅ IMPORT COMPLETE!")
        print("=" * 80)
        print(f"""
Total Sites: {total_sites}
Total Revenue Potential: ${total_revenue:,}/month (${total_revenue * 12:,}/year)

Next Steps:
  1. Deploy PostgreSQL-backed API: python3 /opt/revrank_engine/backend/revrank_api_postgres.py
  2. Test API: curl http://localhost:8001/api/portfolio
  3. View dashboard: http://217.15.168.106:8080/
""")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ ERROR during import: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    main()
