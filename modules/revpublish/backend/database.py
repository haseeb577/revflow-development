import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
DB_CONFIG = {'dbname': os.getenv('POSTGRES_DB', 'revflow'), 'user': os.getenv('POSTGRES_USER', 'postgres'), 'host': os.getenv('POSTGRES_HOST', 'localhost'), 'port': os.getenv('POSTGRES_PORT', '5432')}
if os.getenv('POSTGRES_PASSWORD'): DB_CONFIG['password'] = os.getenv('POSTGRES_PASSWORD')
@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        yield conn
        conn.commit()
    except Exception as e:
        if conn: conn.rollback()
        raise e
    finally:
        if conn: conn.close()
def test_connection():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            return {"status": "connected"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
