"""
RevPublish Database Setup Script
Creates required tables if they don't exist
"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

# Load environment variables
# Try multiple locations for .env file
env_paths = [
    '/opt/shared-api-engine/.env',  # Docker shared location
    '../../.env',  # Project root
    '../.env',     # Module root
    '.env'         # Backend folder
]
for path in env_paths:
    if os.path.exists(path):
        load_dotenv(path)
        break

def get_db_connection():
    """Get database connection with Docker port detection"""
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = int(os.getenv('POSTGRES_PORT', '5432'))
    database = os.getenv('POSTGRES_DB', 'revflow')
    user = os.getenv('POSTGRES_USER', 'revflow')
    password = os.getenv('POSTGRES_PASSWORD', 'revflow2026')
    
    # If connecting to localhost and default port, try Docker port (5433) first
    if host == "localhost" and port == 5432:
        try:
            test_conn = psycopg2.connect(
                host=host,
                port=5433,
                database=database,
                user=user,
                password=password,
                connect_timeout=2
            )
            test_conn.close()
            port = 5433  # Use Docker mapped port
        except:
            pass  # Fall back to default port 5432
    
    return psycopg2.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password
    )

def setup_database():
    """Create required database tables"""
    print("=" * 50)
    print("RevPublish - Database Setup")
    print("=" * 50)
    print()
    
    try:
        print("Connecting to database...")
        conn = get_db_connection()
        cursor = conn.cursor()
        print("✅ Connected to database")
        print()
        
        # Read SQL file
        sql_file = os.path.join(os.path.dirname(__file__), 'setup_database.sql')
        if os.path.exists(sql_file):
            print(f"Reading SQL file: {sql_file}")
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql = f.read()
            
            # Execute SQL
            print("Creating tables...")
            cursor.execute(sql)
            conn.commit()
            print("✅ Tables created successfully")
        else:
            # Create tables directly if SQL file doesn't exist
            print("Creating tables directly...")
            
            # WordPress Sites Table
            cursor.execute("""
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
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_wordpress_sites_site_id 
                ON wordpress_sites(site_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_wordpress_sites_status 
                ON wordpress_sites(status)
            """)
            
            conn.commit()
            print("✅ Tables created successfully")
        
        # Verify tables exist
        print()
        print("Verifying tables...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'wordpress_sites'
        """)
        if cursor.fetchone():
            print("✅ wordpress_sites table exists")
        else:
            print("❌ wordpress_sites table not found")
        
        cursor.close()
        conn.close()
        
        print()
        print("=" * 50)
        print("✅ Database setup complete!")
        print("=" * 50)
        return True
        
    except psycopg2.OperationalError as e:
        print(f"[ERROR] Database connection failed: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Ensure PostgreSQL is running")
        print("  2. Check database credentials in .env file")
        print("  3. Verify database exists")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = setup_database()
    sys.exit(0 if success else 1)

