# ============================================================
# database.py - Database Connection Setup
# Dito naka-configure ang koneksyon sa MySQL database
# Gumagamit ng SQLAlchemy ORM para sa secure na queries
# ============================================================

import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# I-load ang environment variables mula sa .env file
load_dotenv()

# --- Kuhanin ang database credentials mula sa environment ---
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "3306")
DB_NAME     = os.getenv("DB_NAME", "emr_district1")
DB_USER     = os.getenv("DB_USER", "emr_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# --- Gumawa ng database URL ---
# Ginagamit ang pymysql bilang driver para sa MySQL
DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    f"?charset=utf8mb4"
)

# --- Gumawa ng engine (koneksyon sa database) ---
# pool_pre_ping=True: Sinisigurado na buhay ang koneksyon bago gamitin
# pool_recycle=3600: Ire-recycle ang koneksyon bawat 1 oras
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20,
    echo=False  # I-set True kung gusto ng SQL logs sa development
)

# --- Session factory para sa bawat request ---
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Base class para sa lahat ng SQLAlchemy models ---
Base = declarative_base()


def get_db():
    """
    Database dependency para sa FastAPI routes.
    Gagawa ng bagong session bawat request at
    awtomatikong isasara pagkatapos ng request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection():
    """
    Subukan kung gumagana ang database connection.
    Tinatawag ito sa startup ng application.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connection successful!")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
