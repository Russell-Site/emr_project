# ============================================================
# database.py — Dynamic dual-barangay database connection
# Ang BARANGAY_DB sa .env ang nagtatakda kung aling
# database ang gagamitin ng instance na ito.
# ============================================================

import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DB_HOST       = os.getenv("DB_HOST", "localhost")
DB_PORT       = os.getenv("DB_PORT", "3306")
DB_USER       = os.getenv("DB_USER", "root")
DB_PASSWORD   = os.getenv("DB_PASSWORD", "")
# Ang BARANGAY_DB ang nagtatakda kung aling barangay database ang gagamitin
BARANGAY_DB   = os.getenv("BARANGAY_DB", "emr_veinte_reales")
BARANGAY_NAME = os.getenv("BARANGAY_NAME", "Barangay Veinte Reales")

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{BARANGAY_DB}"
    f"?charset=utf8mb4"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Database session dependency para sa FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection():
    """Subukan ang database connection sa startup."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"✅ Connected to database: {BARANGAY_DB} ({BARANGAY_NAME})")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def get_barangay_name() -> str:
    """I-return ang pangalan ng barangay para sa display."""
    return BARANGAY_NAME