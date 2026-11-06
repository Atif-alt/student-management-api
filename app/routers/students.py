"""
routers/students.py
--------------------
Responsibility: Define all HTTP routes for the /students resource.

This is the HTTP LAYER — it handles:
  - Parsing incoming request data (FastAPI does this automatically via Pydantic)
  - Calling the appropriate crud.py function
  - Checking for errors (not found, duplicate email)
  - Returning the correct HTTP status code and response body

All actual database logic lives in crud.py, NOT here.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
# APIRouter is like a mini-FastAPI app. We mount it in main.py with a prefix.
# tags=["Students"] groups all these endpoints under "Students" in Swagger UI.
router = APIRouter(
    prefix="/students",
    tags=["Students"],
)


# ─────────────────────────────────────────────────────────────────────────────
# GET /students — Retrieve all students
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/",
    response_model=list[schemas.StudentResponse],
    summary="Get all students",
    description="Returns a list of all registered students. Returns an empty list if none exist.",
)
def read_students(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),   # FastAPI injects the DB session automatically
):
    """
    Retrieve all students.

    - **skip**: records to skip (pagination)
    - **limit**: max records to return
    """
    students = crud.get_students(db, skip=skip, limit=limit)
    return students


# ─────────────────────────────────────────────────────────────────────────────
# GET /students/{student_id} — Retrieve one student
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/{student_id}",
    response_model=schemas.StudentResponse,
    summary="Get a student by ID",
)
def read_student(
    student_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieve a single student by their ID.

    Returns **404 Not Found** if no student with the given ID exists.
    """
    db_student = crud.get_student(db, student_id=student_id)
    if db_student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with id {student_id} not found.",
        )
    return db_student


# ─────────────────────────────────────────────────────────────────────────────
# POST /students — Create a new student
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/",
    response_model=schemas.StudentResponse,
    status_code=status.HTTP_201_CREATED,   # 201 = resource was successfully created
    summary="Create a new student",
)
def create_student(
    student: schemas.StudentCreate,         # Pydantic validates the request body
    db: Session = Depends(get_db),
):
    """
    Register a new student.

    Returns **409 Conflict** if the email is already registered.
    Returns **201 Created** with the new student data on success.
    """
    # Check for duplicate email BEFORE inserting
    existing = crud.get_student_by_email(db, email=student.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{student.email}' is already registered.",
        )
    return crud.create_student(db=db, student=student)


# ─────────────────────────────────────────────────────────────────────────────
# PUT /students/{student_id} — Update a student
# ─────────────────────────────────────────────────────────────────────────────
@router.put(
    "/{student_id}",
    response_model=schemas.StudentResponse,
    summary="Update a student's details",
)
def update_student(
    student_id: int,
    student_data: schemas.StudentUpdate,
    db: Session = Depends(get_db),
):
    """
    Update one or more fields of an existing student.

    - Supports **partial updates** — you can send only the fields you want to change.
    - Returns **404 Not Found** if no student with the given ID exists.
    - Returns **409 Conflict** if the new email is already in use by a different student.
    """
    # If the client is updating the email, make sure it's not taken
    if student_data.email is not None:
        existing = crud.get_student_by_email(db, email=student_data.email)
        if existing and existing.id != student_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{student_data.email}' is already registered to another student.",
            )

    updated = crud.update_student(db=db, student_id=student_id, student_data=student_data)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with id {student_id} not found.",
        )
    return updated


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /students/{student_id} — Delete a student
# ─────────────────────────────────────────────────────────────────────────────
@router.delete(
    "/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,  # 204 = success, no body to return
    summary="Delete a student",
)
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
):
    """
    Permanently delete a student by ID.

    Returns **404 Not Found** if no student with the given ID exists.
    Returns **204 No Content** on success (no response body).
    """
    deleted = crud.delete_student(db=db, student_id=student_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with id {student_id} not found.",
        )
    # For 204 responses, FastAPI automatically returns no body
