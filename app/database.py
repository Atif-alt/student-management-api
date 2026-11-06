"""
database.py
-----------
Responsibility: Configure the database connection, session factory, and
provide a reusable FastAPI dependency that opens/closes a DB session
for every incoming HTTP request.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# ─────────────────────────────────────────────────────────────────────────────
# Database URL
# ─────────────────────────────────────────────────────────────────────────────
# SQLite stores everything in a single file called "students.db" in the
# project root. The three slashes (///) mean "relative to the current
# working directory". This is fine for development; in production you would
# use a DATABASE_URL from an environment variable.
DATABASE_URL = "sqlite:///./students.db"

# ─────────────────────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────────────────────
# The engine is the core interface between SQLAlchemy and the database.
# connect_args={"check_same_thread": False} is required ONLY for SQLite
# because SQLite's default behaviour is to allow a connection to be used
# on only one thread. FastAPI can serve requests from multiple threads, so
# we disable that restriction here.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# ─────────────────────────────────────────────────────────────────────────────
# Session Factory
# ─────────────────────────────────────────────────────────────────────────────
# SessionLocal is a class (factory). Every time you call SessionLocal()
# you get a brand-new database session — an isolated unit of work.
#   autocommit=False → we control when changes are committed (safe default)
#   autoflush=False  → we control when pending changes are flushed to the DB
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# ─────────────────────────────────────────────────────────────────────────────
# Base Class for ORM Models
# ─────────────────────────────────────────────────────────────────────────────
# All SQLAlchemy models (tables) must inherit from this Base class.
# DeclarativeBase is the SQLAlchemy 2.x way to create a base class.
class Base(DeclarativeBase):
    pass

# ─────────────────────────────────────────────────────────────────────────────
# Database Dependency
# ─────────────────────────────────────────────────────────────────────────────
# This generator function is a FastAPI dependency. FastAPI calls it
# automatically for every route that declares `db: Session = Depends(get_db)`.
#
# Flow:
#   1. FastAPI calls get_db()
#   2. A new session is opened (db = SessionLocal())
#   3. The session is passed to the route handler via `yield`
#   4. After the route finishes (success OR exception), the finally block
#      closes the session — preventing connection leaks.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
