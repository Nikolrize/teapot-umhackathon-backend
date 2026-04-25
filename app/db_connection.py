import os
import psycopg2
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from app.core.config import DATABASE_URL

# Load .env at the very start
load_dotenv()

def get_db_connection():
    # Use SQLAlchemy's connection pool to reuse connections
    # This prevents establishing a new physical connection for every query
    return engine.raw_connection()

engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()