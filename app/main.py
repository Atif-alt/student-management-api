"""
main.py
-------
Responsibility: Application entry point.

This file:
  1. Creates the FastAPI application instance with metadata
  2. Creates database tables on startup (if they don't exist)
  3. Registers the students router
  4. Provides the root GET / welcome endpoint

To run the server:
  uvicorn app.main:app --reload
"""

from fastapi import FastAPI

from app.database import engine, Base
from app.routers import students

# ─────────────────────────────────────────────────────────────────────────────
# Create Database Tables
# ─────────────────────────────────────────────────────────────────────────────
# This creates all tables defined in models.py if they don't already exist.
# It is safe to call on every startup — SQLAlchemy checks before creating.
# In a large production app this would be replaced by Alembic migrations.
Base.metadata.create_all(bind=engine)

# ─────────────────────────────────────────────────────────────────────────────
# FastAPI Application Instance
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Student Management API",
    description=(
        "A RESTful API for managing student records. "
        "Built with FastAPI, SQLAlchemy, SQLite, and Pydantic."
    ),
    version="1.0.0",
    contact={
        "name": "Student Management API",
        "url": "https://github.com",
    },
    license_info={
        "name": "MIT",
    },
)

# ─────────────────────────────────────────────────────────────────────────────
# Register Routers
# ─────────────────────────────────────────────────────────────────────────────
# include_router mounts all routes from students.py under the /students prefix.
# The tags= parameter groups them in the Swagger UI.
app.include_router(students.router)


# ─────────────────────────────────────────────────────────────────────────────
# Root Endpoint
# ─────────────────────────────────────────────────────────────────────────────
@app.get(
    "/",
    tags=["Health"],
    summary="Welcome / Health Check",
)
def root():
    """
    Root endpoint — confirms the API is running.
    Use this as a health check in production deployments.
    """
    return {
        "message": "Welcome to the Student Management API!",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running",
    }
