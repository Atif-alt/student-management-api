"""
schemas.py
----------
Responsibility: Define Pydantic models (schemas) that control the shape
and validation of data entering and leaving the API.

These are NOT database models — they are pure Python/Pydantic data classes
used for request validation and response serialization.

Schema hierarchy:
  StudentBase      ← shared fields + validation rules
    ├── StudentCreate   ← POST /students  (no id; DB generates it)
    └── StudentResponse ← all responses   (includes id)
  StudentUpdate    ← PUT /students/{id}   (all fields optional)
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional


class StudentBase(BaseModel):
    """
    Shared fields between StudentCreate and StudentResponse.
    Validation rules are defined here once and inherited by both.
    """
    name: str = Field(
        ...,                           # "..." means this field is required
        min_length=2,
        max_length=100,
        description="Student's full name",
        examples=["Alice Johnson"],
    )
    email: EmailStr = Field(
        ...,
        description="Student's unique email address",
        examples=["alice@university.edu"],
    )
    age: int = Field(
        ...,
        ge=16,                         # ge = greater than or equal to
        le=100,
        description="Student's age (must be between 16 and 100)",
        examples=[20],
    )
    department: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Department the student belongs to",
        examples=["Computer Science"],
    )
    year_of_study: int = Field(
        ...,
        ge=1,                          # Minimum year: 1
        le=6,                          # Maximum year: 6 (for extended programs)
        description="Academic year (1 to 6)",
        examples=[2],
    )


class StudentCreate(StudentBase):
    """
    Schema for POST /students request body.
    Inherits all fields and validations from StudentBase.
    The client does NOT provide an id — the database generates it.
    """
    pass


class StudentUpdate(BaseModel):
    """
    Schema for PUT /students/{student_id} request body.
    All fields are Optional because a PUT request may update
    only some fields (partial update support).
    """
    name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
        description="Updated student name",
    )
    email: Optional[EmailStr] = Field(
        default=None,
        description="Updated email address",
    )
    age: Optional[int] = Field(
        default=None,
        ge=16,
        le=100,
        description="Updated age",
    )
    department: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
        description="Updated department",
    )
    year_of_study: Optional[int] = Field(
        default=None,
        ge=1,
        le=6,
        description="Updated year of study",
    )


class StudentResponse(StudentBase):
    """
    Schema for all API responses that include student data.
    Inherits all fields from StudentBase and adds the database-generated id.

    model_config: Tells Pydantic to read data from SQLAlchemy ORM objects
    (not just plain dicts). This is required when returning ORM model
    instances directly from route handlers.
    """
    id: int = Field(description="Database-generated unique student ID")

    model_config = ConfigDict(from_attributes=True)
