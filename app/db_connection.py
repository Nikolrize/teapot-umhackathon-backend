import os
import psycopg2
from dotenv import load_dotenv

# Load .env at the very start
load_dotenv()

def get_db_connection():
    conn_string = os.getenv("DATABASE_URL")
    if not conn_string:
        raise ValueError("DATABASE_URL not found in environment variables!")
    
    # Neon sometimes needs the 'postgresql' prefix explicitly
    if conn_string.startswith("postgres://"):
        conn_string = conn_string.replace("postgres://", "postgresql://", 1)
        
    return psycopg2.connect(conn_string)