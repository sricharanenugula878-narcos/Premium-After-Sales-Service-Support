import sqlite3
import os
import logging
from config import Config

# Path to SQLite database file
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'furniture_service.db')

def get_db_connection():
    """Get a connection to the SQLite or MySQL database"""
    use_mysql = os.environ.get('USE_MYSQL', 'false').lower() == 'true'
    if use_mysql:
        try:
            import pymysql
            conn = pymysql.connect(
                host=Config.DB_HOST,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME,
                cursorclass=pymysql.cursors.DictCursor
            )
            return conn
        except Exception as err:
            logging.error(f"Error connecting to MySQL database: {err}. Falling back to SQLite...")

    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Allow dictionary-like access
        # Enable foreign key support in SQLite
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as err:
        logging.error(f"Error connecting to SQLite database: {err}")
        return None

def init_db():
    """Initialize the database with schema and seed data if not already initialized"""
    conn = get_db_connection()
    if not conn:
        logging.error("Failed to connect to database for initialization.")
        return

    # For MySQL, we don't auto-initialize schema here to prevent conflicts; 
    # we initialize only for SQLite fallback.
    is_sqlite = isinstance(conn, sqlite3.Connection)
    if not is_sqlite:
        conn.close()
        return

    try:
        # Check if tables already exist
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if cursor.fetchone():
            # Already initialized
            conn.close()
            return
        
        logging.info("Initializing SQLite database with schema and seed data...")
        
        # Read and execute schema
        schema_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'schema.sql'))
        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            conn.executescript(schema_sql)
            logging.info("Schema imported successfully.")
        else:
            logging.error(f"Schema file not found at {schema_path}")

        # Read and execute seed data
        seed_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'seed.sql'))
        if os.path.exists(seed_path):
            with open(seed_path, 'r', encoding='utf-8') as f:
                seed_sql = f.read()
            conn.executescript(seed_sql)
            logging.info("Seed data imported successfully.")
        else:
            logging.error(f"Seed file not found at {seed_path}")
            
        conn.commit()
    except sqlite3.Error as err:
        logging.error(f"Error during database initialization: {err}")
    finally:
        conn.close()

# Initialize the database immediately
init_db()

def execute_query(query, params=None, fetch_one=False, fetch_all=False, commit=False):
    """Utility function to execute queries safely across SQLite and MySQL"""
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed", "status": 500}
    
    is_sqlite = isinstance(conn, sqlite3.Connection)
    if is_sqlite:
        # Translate MySQL style %s placeholders to SQLite ? placeholders
        query = query.replace('%s', '?')
    
    cursor = conn.cursor()
    result = None
    try:
        cursor.execute(query, params or ())
        
        if fetch_one:
            row = cursor.fetchone()
            result = dict(row) if row and not isinstance(row, dict) else row
        elif fetch_all:
            rows = cursor.fetchall()
            result = [dict(row) if not isinstance(row, dict) else row for row in rows]
            
        if commit:
            conn.commit()
            result = cursor.lastrowid
            
    except Exception as err:
        logging.error(f"Database error: {err} | Query: {query}")
        return {"error": str(err), "status": 500}
    finally:
        cursor.close()
        conn.close()
        
    return result
