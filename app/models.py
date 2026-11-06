"""
models.py
---------
Responsibility: Define the SQLAlchemy ORM model for the Student table.
SQLAlchemy maps this Python class to an actual database table named "students".
"""

from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Student(Base):
    """
    ORM model representing a row in the 'students' table.

    SQLAlchemy will create this table automatically when
    Base.metadata.create_all(engine) is called in main.py.
    """

    # The table name in the SQLite database
    __tablename__ = "students"

    # ── Columns ──────────────────────────────────────────────────────────────

    # Primary key: SQLite auto-increments this integer.
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,          # Creates a DB index for faster lookups by id
    )

    # Student's full name. Cannot be NULL in the database.
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # Email must be unique across all rows and cannot be NULL.
    # The database enforces the unique constraint at the storage level.
    email: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        nullable=False,
        index=True,          # Index for faster lookups by email
    )

    # Student age: a positive integer.
    age: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Department the student belongs to, e.g. "Computer Science".
    department: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # Academic year: 1, 2, 3, or 4.
    year_of_study: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    def __repr__(self) -> str:
        """Developer-friendly string representation for debugging."""
        return (
            f"<Student id={self.id} name='{self.name}' "
            f"email='{self.email}' department='{self.department}'>"
        )
