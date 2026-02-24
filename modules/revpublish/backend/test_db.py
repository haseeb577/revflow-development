"""
Test database connection and table existence
"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../../.env')
load_dotenv('.env')

def test_database():
    """Test database connection and tables"""
    print("=" * 50)
    print("RevPublish - Database Connection Test")
    print("=" * 50)
    print()
    
    # Get configuration
    db_config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'database': os.getenv('POSTGRES_DB', 'revflow'),
        'user': os.getenv('POSTGRES_USER', 'revflow'),
        'password': os.getenv('POSTGRES_PASSWORD', 'revflow2026')
    }
    
    print("Database Configuration:")
    print(f"  Host: {db_config['host']}")
    print(f"  Port: {db_config['port']}")
    print(f"  Database: {db_config['database']}")
    print(f"  User: {db_config['user']}")
    print()
    
    try:
        print("Testing connection...")
        conn = psycopg2.connect(**db_config)
        print("✅ Database connection successful!")
        print()
        
        cursor = conn.cursor()
        
        # Check PostgreSQL version
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"PostgreSQL Version: {version.split(',')[0]}")
        print()
        
        # Check if wordpress_sites table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'wordpress_sites'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            print("✅ wordpress_sites table exists")
            
            # Count rows
            cursor.execute("SELECT COUNT(*) FROM wordpress_sites")
            count = cursor.fetchone()[0]
            print(f"   Rows in table: {count}")
        else:
            print("❌ wordpress_sites table does NOT exist")
            print()
            print("To create the table, run:")
            print("  python setup_db.py")
        
        cursor.close()
        conn.close()
        
        print()
        print("=" * 50)
        print("✅ Database test complete!")
        print("=" * 50)
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Ensure PostgreSQL is running")
        print("  2. Check database credentials")
        print("  3. Verify database exists")
        print("  4. Check firewall settings")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_database()
    sys.exit(0 if success else 1)


