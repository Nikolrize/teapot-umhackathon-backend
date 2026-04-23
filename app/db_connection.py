import os
import psycopg2
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from app.core.config import DATABASE_URL

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

engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

<<<<<<< HEAD

# For chat features
=======
>>>>>>> a3251f4bb394e063d1bcee5efcd60aef72c74c42
class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()