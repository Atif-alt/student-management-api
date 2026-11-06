"""
tests/test_students.py
-----------------------
Professional automated test suite for the Student Management REST API.

TESTING STRATEGY
================
1. Database Isolation
   - A separate in-memory SQLite database is created for each test function.
   - The real `students.db` file is never touched during testing.
   - FastAPI's dependency injection is overridden so the app uses the
     test database instead of the production database.

2. Fixture Hierarchy
   - test_engine    : SQLAlchemy engine pointing at in-memory SQLite
   - test_db        : Fresh DB session for each test (tables created & dropped)
   - client         : FastAPI TestClient wired to the test_db

3. Test Coverage
   A. Root endpoint
   B. Create student (success + 201)
   C. Get all students (empty list + multiple records)
   D. Get student by ID (200 + 404)
   E. Update student (partial update, 404)
   F. Delete student (204, 404, verify deleted)
   G. Duplicate email (409 on create + 409 on update)
   H. Input validation (email, age, year_of_study, name, missing fields)
   I. Edge cases (empty name, invalid types, no-op update)

HOW DEPENDENCY OVERRIDE WORKS
==============================
FastAPI's dependency injection system allows us to swap any dependency
(like get_db) for a different function at runtime. In tests we do:

    app.dependency_overrides[get_db] = override_get_db

This tells FastAPI: "whenever a route needs get_db, call override_get_db
instead." After each test we clear the override so tests don't leak state.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db

# ─────────────────────────────────────────────────────────────────────────────
# Test Database Configuration
# ─────────────────────────────────────────────────────────────────────────────
# We use ":memory:" (in-memory SQLite) for complete isolation from students.db.
#
# CRITICAL — Why StaticPool is required:
#   SQLite in-memory databases are per-connection. Without StaticPool, each
#   call to engine.connect() / SessionLocal() gets a fresh, empty database
#   with no tables. StaticPool forces every connection request to reuse the
#   SAME underlying connection, so the tables we create in the fixture are
#   visible to every session that runs during the test.
TEST_DATABASE_URL = "sqlite://"  # In-memory SQLite (no file on disk)

# ─────────────────────────────────────────────────────────────────────────────
# Reusable Sample Student Data
# ─────────────────────────────────────────────────────────────────────────────
# Define test payloads as module-level constants.
# This avoids duplicating the same dict in every test function.

STUDENT_ALICE = {
    "name": "Alice Johnson",
    "email": "alice@test.edu",
    "age": 20,
    "department": "Computer Science",
    "year_of_study": 2,
}

STUDENT_BOB = {
    "name": "Bob Martinez",
    "email": "bob@test.edu",
    "age": 22,
    "department": "Electrical Engineering",
    "year_of_study": 3,
}

STUDENT_CAROL = {
    "name": "Carol Williams",
    "email": "carol@test.edu",
    "age": 19,
    "department": "Mathematics",
    "year_of_study": 1,
}


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def client():
    """
    Provides a FastAPI TestClient backed by a fresh in-memory test database.

    Lifecycle (runs for every individual test function):
      1. Create a new SQLAlchemy engine connected to in-memory SQLite.
      2. Create all tables (students) in this engine.
      3. Build a test session factory bound to this engine.
      4. Define override_get_db — yields sessions from the test factory.
      5. Install the override into the FastAPI app.
      6. Yield the TestClient — the test runs here.
      7. Clear the override so the real app is unaffected.
      8. Drop all tables to clean up memory.

    Why function scope?
      Each test gets a completely empty database, so tests are fully
      independent and can be run in any order.
    """
    # Step 1: in-memory engine.
    #   - connect_args: required for SQLite threading in FastAPI.
    #   - poolclass=StaticPool: CRITICAL — forces all connections to reuse
    #     the SAME underlying SQLite connection. Without this, each new
    #     connection gets a blank in-memory database with no tables.
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Step 2: Create the students table in the test engine
    Base.metadata.create_all(bind=engine)

    # Step 3: Test session factory
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
    )

    # Step 4: Dependency override function
    def override_get_db():
        """Replaces get_db during tests — uses the test engine."""
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    # Step 5: Tell FastAPI to use our test dependency
    app.dependency_overrides[get_db] = override_get_db

    # Step 6: Yield the test client
    with TestClient(app) as test_client:
        yield test_client

    # Step 7: Clear the override after the test finishes
    app.dependency_overrides.clear()

    # Step 8: Drop all tables to free memory
    Base.metadata.drop_all(bind=engine)


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def create_student(client: TestClient, data: dict) -> dict:
    """
    Helper: POST a student and assert 201. Returns the response JSON.
    Used by multiple tests to avoid repeating the creation step.
    """
    response = client.post("/students/", json=data)
    assert response.status_code == 201, (
        f"Expected 201, got {response.status_code}: {response.text}"
    )
    return response.json()


# ═════════════════════════════════════════════════════════════════════════════
# A. ROOT ENDPOINT
# ═════════════════════════════════════════════════════════════════════════════

class TestRootEndpoint:
    """Tests for GET /"""

    def test_root_returns_200(self, client):
        """Root endpoint must respond with HTTP 200."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_welcome_message(self, client):
        """Root endpoint must return a welcome message."""
        response = client.get("/")
        body = response.json()
        assert "message" in body
        assert "Welcome" in body["message"]

    def test_root_returns_status_running(self, client):
        """Root endpoint must report status as 'running'."""
        response = client.get("/")
        body = response.json()
        assert body.get("status") == "running"

    def test_root_returns_docs_link(self, client):
        """Root endpoint must include a /docs link."""
        response = client.get("/")
        body = response.json()
        assert body.get("docs") == "/docs"


# ═════════════════════════════════════════════════════════════════════════════
# B. CREATE STUDENT — POST /students/
# ═════════════════════════════════════════════════════════════════════════════

class TestCreateStudent:
    """Tests for POST /students/"""

    def test_create_student_returns_201(self, client):
        """Creating a valid student must return HTTP 201 Created."""
        response = client.post("/students/", json=STUDENT_ALICE)
        assert response.status_code == 201

    def test_create_student_returns_correct_data(self, client):
        """Response must echo back all submitted fields correctly."""
        response = client.post("/students/", json=STUDENT_ALICE)
        body = response.json()
        assert body["name"] == STUDENT_ALICE["name"]
        assert body["email"] == STUDENT_ALICE["email"]
        assert body["age"] == STUDENT_ALICE["age"]
        assert body["department"] == STUDENT_ALICE["department"]
        assert body["year_of_study"] == STUDENT_ALICE["year_of_study"]

    def test_create_student_generates_id(self, client):
        """Response must include a database-generated integer id."""
        response = client.post("/students/", json=STUDENT_ALICE)
        body = response.json()
        assert "id" in body
        assert isinstance(body["id"], int)
        assert body["id"] > 0

    def test_create_multiple_students_get_unique_ids(self, client):
        """Each created student must receive a different id."""
        alice = create_student(client, STUDENT_ALICE)
        bob = create_student(client, STUDENT_BOB)
        assert alice["id"] != bob["id"]

    def test_create_student_minimum_valid_age(self, client):
        """Age exactly at the minimum boundary (16) must be accepted."""
        data = {**STUDENT_ALICE, "age": 16}
        response = client.post("/students/", json=data)
        assert response.status_code == 201
        assert response.json()["age"] == 16

    def test_create_student_maximum_valid_age(self, client):
        """Age exactly at the maximum boundary (100) must be accepted."""
        data = {**STUDENT_ALICE, "age": 100}
        response = client.post("/students/", json=data)
        assert response.status_code == 201
        assert response.json()["age"] == 100

    def test_create_student_minimum_valid_year(self, client):
        """year_of_study = 1 (minimum) must be accepted."""
        data = {**STUDENT_ALICE, "year_of_study": 1}
        response = client.post("/students/", json=data)
        assert response.status_code == 201

    def test_create_student_maximum_valid_year(self, client):
        """year_of_study = 6 (maximum) must be accepted."""
        data = {**STUDENT_ALICE, "year_of_study": 6}
        response = client.post("/students/", json=data)
        assert response.status_code == 201


# ═════════════════════════════════════════════════════════════════════════════
# C. GET ALL STUDENTS — GET /students/
# ═════════════════════════════════════════════════════════════════════════════

class TestGetAllStudents:
    """Tests for GET /students/"""

    def test_empty_database_returns_empty_list(self, client):
        """With no students in the database, response must be an empty list."""
        response = client.get("/students/")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_all_returns_200(self, client):
        """GET /students/ must always return HTTP 200."""
        response = client.get("/students/")
        assert response.status_code == 200

    def test_get_all_after_one_creation(self, client):
        """After creating one student, GET /students/ must return a list of one."""
        create_student(client, STUDENT_ALICE)
        response = client.get("/students/")
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert len(body) == 1

    def test_get_all_after_three_creations(self, client):
        """After creating three students, GET /students/ must return all three."""
        create_student(client, STUDENT_ALICE)
        create_student(client, STUDENT_BOB)
        create_student(client, STUDENT_CAROL)
        response = client.get("/students/")
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert len(body) == 3

    def test_get_all_response_contains_expected_fields(self, client):
        """Each student record in the list must include all required fields."""
        create_student(client, STUDENT_ALICE)
        response = client.get("/students/")
        student = response.json()[0]
        required_fields = {"id", "name", "email", "age", "department", "year_of_study"}
        assert required_fields.issubset(student.keys())

    def test_get_all_contains_correct_names(self, client):
        """Names of all created students must appear in the response."""
        create_student(client, STUDENT_ALICE)
        create_student(client, STUDENT_BOB)
        response = client.get("/students/")
        names = [s["name"] for s in response.json()]
        assert STUDENT_ALICE["name"] in names
        assert STUDENT_BOB["name"] in names


# ═════════════════════════════════════════════════════════════════════════════
# D. GET STUDENT BY ID — GET /students/{student_id}
# ═════════════════════════════════════════════════════════════════════════════

class TestGetStudentById:
    """Tests for GET /students/{student_id}"""

    def test_get_existing_student_returns_200(self, client):
        """Getting an existing student by ID must return HTTP 200."""
        created = create_student(client, STUDENT_ALICE)
        response = client.get(f"/students/{created['id']}")
        assert response.status_code == 200

    def test_get_existing_student_returns_correct_data(self, client):
        """Response must include the exact fields that were submitted."""
        created = create_student(client, STUDENT_ALICE)
        response = client.get(f"/students/{created['id']}")
        body = response.json()
        assert body["name"] == STUDENT_ALICE["name"]
        assert body["email"] == STUDENT_ALICE["email"]
        assert body["age"] == STUDENT_ALICE["age"]
        assert body["department"] == STUDENT_ALICE["department"]
        assert body["year_of_study"] == STUDENT_ALICE["year_of_study"]

    def test_get_existing_student_returns_id(self, client):
        """Response must include the student's id."""
        created = create_student(client, STUDENT_ALICE)
        response = client.get(f"/students/{created['id']}")
        body = response.json()
        assert body["id"] == created["id"]

    def test_get_nonexistent_student_returns_404(self, client):
        """Requesting a student ID that doesn't exist must return 404."""
        response = client.get("/students/99999")
        assert response.status_code == 404

    def test_get_nonexistent_student_returns_error_detail(self, client):
        """404 response must include a descriptive error message."""
        response = client.get("/students/99999")
        body = response.json()
        assert "detail" in body
        assert "99999" in body["detail"]

    def test_get_specific_student_among_multiple(self, client):
        """Fetching by ID must return the correct student, not another one."""
        alice = create_student(client, STUDENT_ALICE)
        bob = create_student(client, STUDENT_BOB)
        response = client.get(f"/students/{bob['id']}")
        assert response.json()["email"] == STUDENT_BOB["email"]
        assert response.json()["email"] != STUDENT_ALICE["email"]


# ═════════════════════════════════════════════════════════════════════════════
# E. UPDATE STUDENT — PUT /students/{student_id}
# ═════════════════════════════════════════════════════════════════════════════

class TestUpdateStudent:
    """Tests for PUT /students/{student_id}"""

    def test_update_age_returns_200(self, client):
        """Updating a student's age must return HTTP 200."""
        created = create_student(client, STUDENT_ALICE)
        response = client.put(f"/students/{created['id']}", json={"age": 25})
        assert response.status_code == 200

    def test_update_age_reflects_in_response(self, client):
        """The updated age must appear in the response body."""
        created = create_student(client, STUDENT_ALICE)
        response = client.put(f"/students/{created['id']}", json={"age": 25})
        assert response.json()["age"] == 25

    def test_update_department_returns_200(self, client):
        """Updating a student's department must return HTTP 200."""
        created = create_student(client, STUDENT_ALICE)
        response = client.put(
            f"/students/{created['id']}",
            json={"department": "Data Science"},
        )
        assert response.status_code == 200

    def test_update_department_reflects_in_response(self, client):
        """The updated department must appear in the response body."""
        created = create_student(client, STUDENT_ALICE)
        response = client.put(
            f"/students/{created['id']}",
            json={"department": "Data Science"},
        )
        assert response.json()["department"] == "Data Science"

    def test_update_does_not_change_unset_fields(self, client):
        """Fields not included in the update request must remain unchanged."""
        created = create_student(client, STUDENT_ALICE)
        # Update only age — all other fields must stay the same
        response = client.put(f"/students/{created['id']}", json={"age": 30})
        body = response.json()
        assert body["name"] == STUDENT_ALICE["name"]
        assert body["email"] == STUDENT_ALICE["email"]
        assert body["department"] == STUDENT_ALICE["department"]
        assert body["year_of_study"] == STUDENT_ALICE["year_of_study"]

    def test_update_multiple_fields_at_once(self, client):
        """Multiple fields can be updated in a single PUT request."""
        created = create_student(client, STUDENT_ALICE)
        response = client.put(
            f"/students/{created['id']}",
            json={"age": 24, "year_of_study": 4, "department": "AI & ML"},
        )
        body = response.json()
        assert body["age"] == 24
        assert body["year_of_study"] == 4
        assert body["department"] == "AI & ML"

    def test_update_name_field(self, client):
        """Name can be updated via PUT."""
        created = create_student(client, STUDENT_ALICE)
        response = client.put(
            f"/students/{created['id']}",
            json={"name": "Alice Smith"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Alice Smith"

    def test_update_email_field(self, client):
        """Email can be updated to a new, unique address."""
        created = create_student(client, STUDENT_ALICE)
        response = client.put(
            f"/students/{created['id']}",
            json={"email": "newalice@test.edu"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == "newalice@test.edu"

    def test_update_nonexistent_student_returns_404(self, client):
        """Updating a student that doesn't exist must return 404."""
        response = client.put("/students/99999", json={"age": 25})
        assert response.status_code == 404

    def test_update_nonexistent_student_returns_error_detail(self, client):
        """404 error response must mention the missing student ID."""
        response = client.put("/students/99999", json={"age": 25})
        assert "detail" in response.json()
        assert "99999" in response.json()["detail"]

    def test_update_with_empty_body_is_no_op(self, client):
        """
        Sending an empty JSON body {} performs no changes (no-op update).
        The API contract supports this: exclude_unset=True means no fields
        are updated when none are sent.
        """
        created = create_student(client, STUDENT_ALICE)
        response = client.put(f"/students/{created['id']}", json={})
        assert response.status_code == 200
        body = response.json()
        # All original fields remain intact
        assert body["name"] == STUDENT_ALICE["name"]
        assert body["email"] == STUDENT_ALICE["email"]
        assert body["age"] == STUDENT_ALICE["age"]


# ═════════════════════════════════════════════════════════════════════════════
# F. DELETE STUDENT — DELETE /students/{student_id}
# ═════════════════════════════════════════════════════════════════════════════

class TestDeleteStudent:
    """Tests for DELETE /students/{student_id}"""

    def test_delete_existing_student_returns_204(self, client):
        """Deleting an existing student must return HTTP 204 No Content."""
        created = create_student(client, STUDENT_ALICE)
        response = client.delete(f"/students/{created['id']}")
        assert response.status_code == 204

    def test_delete_response_has_no_body(self, client):
        """204 response must have an empty body."""
        created = create_student(client, STUDENT_ALICE)
        response = client.delete(f"/students/{created['id']}")
        assert response.content == b""

    def test_deleted_student_cannot_be_retrieved(self, client):
        """After deletion, GET by the same ID must return 404."""
        created = create_student(client, STUDENT_ALICE)
        student_id = created["id"]
        # Delete the student
        client.delete(f"/students/{student_id}")
        # Attempt to retrieve the deleted student
        response = client.get(f"/students/{student_id}")
        assert response.status_code == 404

    def test_delete_reduces_total_count(self, client):
        """After deleting one student, the total list count must decrease by 1."""
        create_student(client, STUDENT_ALICE)
        create_student(client, STUDENT_BOB)
        # Confirm 2 students
        assert len(client.get("/students/").json()) == 2
        # Delete Alice
        alice_id = client.get("/students/").json()[0]["id"]
        client.delete(f"/students/{alice_id}")
        # Confirm 1 student remains
        assert len(client.get("/students/").json()) == 1

    def test_delete_nonexistent_student_returns_404(self, client):
        """Deleting a student ID that doesn't exist must return 404."""
        response = client.delete("/students/99999")
        assert response.status_code == 404

    def test_delete_nonexistent_returns_error_detail(self, client):
        """404 error response must mention the missing student ID."""
        response = client.delete("/students/99999")
        assert "detail" in response.json()
        assert "99999" in response.json()["detail"]

    def test_delete_does_not_affect_other_students(self, client):
        """Deleting one student must leave all other students intact."""
        alice = create_student(client, STUDENT_ALICE)
        bob = create_student(client, STUDENT_BOB)
        # Delete Alice
        client.delete(f"/students/{alice['id']}")
        # Bob must still be retrievable
        response = client.get(f"/students/{bob['id']}")
        assert response.status_code == 200
        assert response.json()["email"] == STUDENT_BOB["email"]


# ═════════════════════════════════════════════════════════════════════════════
# G. DUPLICATE EMAIL
# ═════════════════════════════════════════════════════════════════════════════

class TestDuplicateEmail:
    """Tests for 409 Conflict on duplicate email scenarios."""

    def test_create_duplicate_email_returns_409(self, client):
        """Creating two students with the same email must return 409."""
        create_student(client, STUDENT_ALICE)
        response = client.post("/students/", json=STUDENT_ALICE)
        assert response.status_code == 409

    def test_create_duplicate_email_returns_error_detail(self, client):
        """409 error response must mention the conflicting email."""
        create_student(client, STUDENT_ALICE)
        response = client.post("/students/", json=STUDENT_ALICE)
        body = response.json()
        assert "detail" in body
        assert STUDENT_ALICE["email"] in body["detail"]

    def test_duplicate_email_different_name_still_409(self, client):
        """
        Even if the name and other fields differ, sharing an email must
        return 409. Email is the unique identifier — not the name.
        """
        create_student(client, STUDENT_ALICE)
        impostor = {**STUDENT_BOB, "email": STUDENT_ALICE["email"]}  # Same email, different student
        response = client.post("/students/", json=impostor)
        assert response.status_code == 409

    def test_update_to_another_students_email_returns_409(self, client):
        """
        Updating Student A's email to Student B's existing email must
        return 409 Conflict.
        """
        alice = create_student(client, STUDENT_ALICE)
        create_student(client, STUDENT_BOB)
        # Try to give Alice's email to Bob's email address
        response = client.put(
            f"/students/{alice['id']}",
            json={"email": STUDENT_BOB["email"]},
        )
        assert response.status_code == 409

    def test_update_to_own_email_does_not_conflict(self, client):
        """
        Updating a student while keeping their own email must succeed (200),
        not trigger a 409 conflict with themselves.
        """
        alice = create_student(client, STUDENT_ALICE)
        response = client.put(
            f"/students/{alice['id']}",
            json={"email": STUDENT_ALICE["email"], "age": 21},
        )
        assert response.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# H. INPUT VALIDATION
# ═════════════════════════════════════════════════════════════════════════════

class TestInputValidation:
    """
    Tests that Pydantic correctly rejects invalid input.
    FastAPI returns 422 Unprocessable Entity when validation fails.
    """

    def test_invalid_email_format_returns_422(self, client):
        """An email string that is not a valid email must be rejected (422)."""
        data = {**STUDENT_ALICE, "email": "not-a-valid-email"}
        response = client.post("/students/", json=data)
        assert response.status_code == 422

    def test_age_below_minimum_returns_422(self, client):
        """Age below 16 (the defined minimum) must be rejected with 422."""
        data = {**STUDENT_ALICE, "age": 15}
        response = client.post("/students/", json=data)
        assert response.status_code == 422

    def test_age_above_maximum_returns_422(self, client):
        """Age above 100 (the defined maximum) must be rejected with 422."""
        data = {**STUDENT_ALICE, "age": 101}
        response = client.post("/students/", json=data)
        assert response.status_code == 422

    def test_year_of_study_below_minimum_returns_422(self, client):
        """year_of_study = 0 (below minimum of 1) must be rejected."""
        data = {**STUDENT_ALICE, "year_of_study": 0}
        response = client.post("/students/", json=data)
        assert response.status_code == 422

    def test_year_of_study_above_maximum_returns_422(self, client):
        """year_of_study = 7 (above maximum of 6) must be rejected."""
        data = {**STUDENT_ALICE, "year_of_study": 7}
        response = client.post("/students/", json=data)
        assert response.status_code == 422

    def test_missing_name_returns_422(self, client):
        """Omitting the required 'name' field must return 422."""
        data = {k: v for k, v in STUDENT_ALICE.items() if k != "name"}
        response = client.post("/students/", json=data)
        assert response.status_code == 422

    def test_missing_email_returns_422(self, client):
        """Omitting the required 'email' field must return 422."""
        data = {k: v for k, v in STUDENT_ALICE.items() if k != "email"}
        response = client.post("/students/", json=data)
        assert response.status_code == 422

    def test_missing_age_returns_422(self, client):
        """Omitting the required 'age' field must return 422."""
        data = {k: v for k, v in STUDENT_ALICE.items() if k != "age"}
        response = client.post("/students/", json=data)
        assert response.status_code == 422

    def test_missing_department_returns_422(self, client):
        """Omitting the required 'department' field must return 422."""
        data = {k: v for k, v in STUDENT_ALICE.items() if k != "department"}
        response = client.post("/students/", json=data)
        assert response.status_code == 422

    def test_missing_year_of_study_returns_422(self, client):
        """Omitting the required 'year_of_study' field must return 422."""
        data = {k: v for k, v in STUDENT_ALICE.items() if k != "year_of_study"}
        response = client.post("/students/", json=data)
        assert response.status_code == 422

    def test_completely_empty_body_returns_422(self, client):
        """Sending an empty JSON body to POST /students/ must return 422."""
        response = client.post("/students/", json={})
        assert response.status_code == 422

    def test_age_as_string_returns_422(self, client):
        """
        Sending age as a non-numeric string must be rejected.
        Pydantic performs type coercion but rejects clearly invalid types.
        """
        data = {**STUDENT_ALICE, "age": "twenty"}
        response = client.post("/students/", json=data)
        assert response.status_code == 422

    def test_year_of_study_as_string_returns_422(self, client):
        """Sending year_of_study as a non-numeric string must be rejected."""
        data = {**STUDENT_ALICE, "year_of_study": "second"}
        response = client.post("/students/", json=data)
        assert response.status_code == 422

    def test_update_age_below_minimum_returns_422(self, client):
        """Updating age to below 16 via PUT must be rejected with 422."""
        created = create_student(client, STUDENT_ALICE)
        response = client.put(f"/students/{created['id']}", json={"age": 10})
        assert response.status_code == 422

    def test_update_age_above_maximum_returns_422(self, client):
        """Updating age to above 100 via PUT must be rejected with 422."""
        created = create_student(client, STUDENT_ALICE)
        response = client.put(f"/students/{created['id']}", json={"age": 200})
        assert response.status_code == 422


# ═════════════════════════════════════════════════════════════════════════════
# I. EDGE CASES
# ═════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Tests for boundary conditions and unusual but valid scenarios."""

    def test_name_too_short_returns_422(self, client):
        """
        Name with fewer than 2 characters must be rejected.
        The schema defines min_length=2 for name.
        """
        data = {**STUDENT_ALICE, "name": "A"}
        response = client.post("/students/", json=data)
        assert response.status_code == 422

    def test_name_exactly_minimum_length_accepted(self, client):
        """Name with exactly 2 characters (minimum) must be accepted."""
        data = {**STUDENT_ALICE, "name": "Al"}
        response = client.post("/students/", json=data)
        assert response.status_code == 201

    def test_get_student_with_string_id_returns_422(self, client):
        """
        Passing a non-integer path parameter for student_id must return 422.
        FastAPI validates path parameter types automatically.
        """
        response = client.get("/students/abc")
        assert response.status_code == 422

    def test_delete_student_with_string_id_returns_422(self, client):
        """Non-integer student_id on DELETE must return 422."""
        response = client.delete("/students/abc")
        assert response.status_code == 422

    def test_created_student_persists_across_requests(self, client):
        """
        A student created in one request must still exist in the next request
        within the same test (same test database session).
        """
        created = create_student(client, STUDENT_ALICE)
        # Retrieve in a separate request
        response = client.get(f"/students/{created['id']}")
        assert response.status_code == 200
        assert response.json()["email"] == STUDENT_ALICE["email"]

    def test_age_boundary_exactly_16_accepted(self, client):
        """Age = 16 is exactly at the lower boundary and must be accepted."""
        data = {**STUDENT_ALICE, "age": 16}
        assert client.post("/students/", json=data).status_code == 201

    def test_age_boundary_exactly_15_rejected(self, client):
        """Age = 15 is one below the lower boundary and must be rejected."""
        data = {**STUDENT_ALICE, "age": 15}
        assert client.post("/students/", json=data).status_code == 422

    def test_age_boundary_exactly_100_accepted(self, client):
        """Age = 100 is exactly at the upper boundary and must be accepted."""
        data = {**STUDENT_ALICE, "age": 100}
        assert client.post("/students/", json=data).status_code == 201

    def test_age_boundary_exactly_101_rejected(self, client):
        """Age = 101 is one above the upper boundary and must be rejected."""
        data = {**STUDENT_ALICE, "age": 101}
        assert client.post("/students/", json=data).status_code == 422

    def test_year_boundary_exactly_1_accepted(self, client):
        """year_of_study = 1 is the minimum and must be accepted."""
        data = {**STUDENT_ALICE, "year_of_study": 1}
        assert client.post("/students/", json=data).status_code == 201

    def test_year_boundary_exactly_0_rejected(self, client):
        """year_of_study = 0 is below minimum and must be rejected."""
        data = {**STUDENT_ALICE, "year_of_study": 0}
        assert client.post("/students/", json=data).status_code == 422

    def test_year_boundary_exactly_6_accepted(self, client):
        """year_of_study = 6 is the maximum and must be accepted."""
        data = {**STUDENT_ALICE, "year_of_study": 6}
        assert client.post("/students/", json=data).status_code == 201

    def test_year_boundary_exactly_7_rejected(self, client):
        """year_of_study = 7 is above maximum and must be rejected."""
        data = {**STUDENT_ALICE, "year_of_study": 7}
        assert client.post("/students/", json=data).status_code == 422
