"""
crud.py
-------
Responsibility: All database operations (Create, Read, Update, Delete).

This is the SERVICE LAYER — it handles all business logic and database
interaction. It knows nothing about HTTP requests or responses.

Design principle: Keep routes thin, keep crud functions reusable.
Every function accepts a SQLAlchemy Session and returns ORM model
instances (or None), never raw HTTP responses.
"""

from sqlalchemy.orm import Session

from app import models, schemas


# ─────────────────────────────────────────────────────────────────────────────
# READ Operations
# ─────────────────────────────────────────────────────────────────────────────

def get_student(db: Session, student_id: int) -> models.Student | None:
    """
    Retrieve a single student by their primary key (id).

    Returns the Student ORM object if found, or None if not found.
    The router will convert None into a 404 response.
    """
    return db.query(models.Student).filter(models.Student.id == student_id).first()


def get_student_by_email(db: Session, email: str) -> models.Student | None:
    """
    Retrieve a student by their email address.

    Used to check for duplicate emails before creating or updating a student.
    Returns the Student ORM object if found, or None if not found.
    """
    return db.query(models.Student).filter(models.Student.email == email).first()


def get_students(db: Session, skip: int = 0, limit: int = 100) -> list[models.Student]:
    """
    Retrieve all students with optional pagination.

    Args:
        skip:  Number of records to skip (for pagination). Default: 0.
        limit: Maximum number of records to return. Default: 100.

    Returns a list of Student ORM objects (empty list if no students exist).
    """
    return db.query(models.Student).offset(skip).limit(limit).all()


# ─────────────────────────────────────────────────────────────────────────────
# CREATE Operation
# ─────────────────────────────────────────────────────────────────────────────

def create_student(db: Session, student: schemas.StudentCreate) -> models.Student:
    """
    Insert a new student record into the database.

    Flow:
      1. Convert the Pydantic schema to a SQLAlchemy ORM model instance.
      2. Add the instance to the session (marks it as "pending insert").
      3. Commit the transaction (writes to disk).
      4. Refresh the instance to load the database-generated id.
      5. Return the refreshed instance.

    Note: Duplicate email check is the caller's responsibility (router).
    """
    # model_dump() converts the Pydantic model to a plain dict.
    # ** unpacks the dict as keyword arguments to Student().
    db_student = models.Student(**student.model_dump())

    db.add(db_student)       # Stage the INSERT
    db.commit()              # Execute INSERT and persist to disk
    db.refresh(db_student)   # Reload from DB to populate auto-generated fields (id)
    return db_student


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE Operation
# ─────────────────────────────────────────────────────────────────────────────

def update_student(
    db: Session,
    student_id: int,
    student_data: schemas.StudentUpdate,
) -> models.Student | None:
    """
    Update an existing student's details.

    Supports partial updates — only fields provided in student_data are changed.
    Fields left as None in the request body are skipped entirely.

    Returns the updated Student ORM object, or None if not found.
    """
    db_student = get_student(db, student_id)
    if db_student is None:
        return None

    # exclude_unset=True: only include fields the client actually sent.
    # This enables partial updates — fields not sent are left unchanged.
    update_data = student_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_student, field, value)  # Update each field on the ORM object

    db.commit()              # Persist changes
    db.refresh(db_student)   # Reload to reflect the committed state
    return db_student


# ─────────────────────────────────────────────────────────────────────────────
# DELETE Operation
# ─────────────────────────────────────────────────────────────────────────────

def delete_student(db: Session, student_id: int) -> bool:
    """
    Delete a student by ID.

    Returns True if the student was found and deleted.
    Returns False if no student with that ID exists.
    """
    db_student = get_student(db, student_id)
    if db_student is None:
        return False

    db.delete(db_student)   # Stage the DELETE
    db.commit()             # Execute and persist
    return True
