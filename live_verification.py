"""
live_verification.py
--------------------
Automated live API verification script.
Uses httpx to test every endpoint against the running FastAPI server.
Handles HTTP 204 No Content properly (unlike PowerShell).
"""

import httpx
import sys
import time

BASE_URL = "http://127.0.0.1:8000"

# Track results
results = []


def log(test_name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    results.append((test_name, passed, detail))
    emoji = "✅" if passed else "❌"
    print(f"  {emoji} {status}: {test_name}")
    if detail:
        print(f"         {detail}")


def main():
    print("=" * 70)
    print("LIVE API VERIFICATION — Student Management API")
    print("=" * 70)

    # Wait for server to be ready
    print("\nWaiting for server at", BASE_URL, "...")
    for attempt in range(10):
        try:
            r = httpx.get(f"{BASE_URL}/", timeout=2.0)
            if r.status_code == 200:
                print("Server is ready!\n")
                break
        except httpx.ConnectError:
            time.sleep(1)
    else:
        print("ERROR: Server did not start in time.")
        sys.exit(1)

    client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    # ─────────────────────────────────────────────────────────────────────
    # 1. GET / — Root / Health Check
    # ─────────────────────────────────────────────────────────────────────
    print("─" * 70)
    print("1. GET /  (Root / Health Check)")
    print("─" * 70)

    r = client.get("/")
    log("GET / returns 200", r.status_code == 200, f"Status: {r.status_code}")
    body = r.json()
    log("Response has 'message' key", "message" in body)
    log("Message contains 'Welcome'", "Welcome" in body.get("message", ""))
    log("Status is 'running'", body.get("status") == "running")
    log("Docs link is '/docs'", body.get("docs") == "/docs")
    log("Version is '1.0.0'", body.get("version") == "1.0.0")
    print(f"  Response body: {body}\n")

    # ─────────────────────────────────────────────────────────────────────
    # 2. GET /students — Empty list
    # ─────────────────────────────────────────────────────────────────────
    print("─" * 70)
    print("2. GET /students/  (Empty database)")
    print("─" * 70)

    r = client.get("/students/")
    log("GET /students/ returns 200", r.status_code == 200, f"Status: {r.status_code}")
    log("Response is an empty list", r.json() == [], f"Body: {r.json()}")
    print()

    # ─────────────────────────────────────────────────────────────────────
    # 3. POST /students — Create student
    # ─────────────────────────────────────────────────────────────────────
    print("─" * 70)
    print("3. POST /students/  (Create a student)")
    print("─" * 70)

    student_data = {
        "name": "Alice Johnson",
        "email": "alice@university.edu",
        "age": 20,
        "department": "Computer Science",
        "year_of_study": 2,
    }
    r = client.post("/students/", json=student_data)
    log("POST /students/ returns 201", r.status_code == 201, f"Status: {r.status_code}")
    created = r.json()
    log("Response has 'id' field", "id" in created)
    log("ID is a positive integer", isinstance(created.get("id"), int) and created["id"] > 0)
    log("Name matches", created.get("name") == student_data["name"])
    log("Email matches", created.get("email") == student_data["email"])
    log("Age matches", created.get("age") == student_data["age"])
    log("Department matches", created.get("department") == student_data["department"])
    log("Year of study matches", created.get("year_of_study") == student_data["year_of_study"])
    alice_id = created.get("id")
    print(f"  Created student ID: {alice_id}")
    print(f"  Response body: {created}\n")

    # Create a second student for later tests
    student_bob = {
        "name": "Bob Martinez",
        "email": "bob@university.edu",
        "age": 22,
        "department": "Electrical Engineering",
        "year_of_study": 3,
    }
    r2 = client.post("/students/", json=student_bob)
    bob_id = r2.json().get("id")
    log("Second student created (Bob)", r2.status_code == 201, f"Bob ID: {bob_id}")
    print()

    # ─────────────────────────────────────────────────────────────────────
    # 4. GET /students — List with students
    # ─────────────────────────────────────────────────────────────────────
    print("─" * 70)
    print("4. GET /students/  (After creating 2 students)")
    print("─" * 70)

    r = client.get("/students/")
    log("GET /students/ returns 200", r.status_code == 200)
    students = r.json()
    log("Response is a list of 2", isinstance(students, list) and len(students) == 2,
        f"Count: {len(students)}")
    names = [s["name"] for s in students]
    log("Alice is in the list", "Alice Johnson" in names)
    log("Bob is in the list", "Bob Martinez" in names)
    print()

    # ─────────────────────────────────────────────────────────────────────
    # 5. GET /students/{id} — Get single student
    # ─────────────────────────────────────────────────────────────────────
    print("─" * 70)
    print("5. GET /students/{id}  (Get Alice by ID)")
    print("─" * 70)

    r = client.get(f"/students/{alice_id}")
    log("GET /students/{id} returns 200", r.status_code == 200, f"Status: {r.status_code}")
    alice = r.json()
    log("ID matches", alice.get("id") == alice_id)
    log("Name is Alice Johnson", alice.get("name") == "Alice Johnson")
    log("Email matches", alice.get("email") == "alice@university.edu")
    print(f"  Response body: {alice}\n")

    # ─────────────────────────────────────────────────────────────────────
    # 6. PUT /students/{id} — Update student
    # ─────────────────────────────────────────────────────────────────────
    print("─" * 70)
    print("6. PUT /students/{id}  (Update Alice's age and department)")
    print("─" * 70)

    update_data = {"age": 21, "department": "Data Science"}
    r = client.put(f"/students/{alice_id}", json=update_data)
    log("PUT /students/{id} returns 200", r.status_code == 200, f"Status: {r.status_code}")
    updated = r.json()
    log("Age updated to 21", updated.get("age") == 21)
    log("Department updated to 'Data Science'", updated.get("department") == "Data Science")
    log("Name unchanged", updated.get("name") == "Alice Johnson")
    log("Email unchanged", updated.get("email") == "alice@university.edu")
    log("Year of study unchanged", updated.get("year_of_study") == 2)
    print(f"  Response body: {updated}\n")

    # Verify update persisted
    r = client.get(f"/students/{alice_id}")
    persisted = r.json()
    log("Update persisted (GET confirms age=21)", persisted.get("age") == 21)
    log("Update persisted (GET confirms dept=Data Science)",
        persisted.get("department") == "Data Science")
    print()

    # ─────────────────────────────────────────────────────────────────────
    # 7. DELETE /students/{id} — Delete student (using httpx)
    # ─────────────────────────────────────────────────────────────────────
    print("─" * 70)
    print("7. DELETE /students/{id}  (Delete Bob — httpx handles 204 properly)")
    print("─" * 70)

    r = client.delete(f"/students/{bob_id}")
    log("DELETE /students/{id} returns 204", r.status_code == 204, f"Status: {r.status_code}")
    log("Response body is empty", r.content == b"", f"Body length: {len(r.content)} bytes")
    log("Content-Length is 0 or absent",
        r.headers.get("content-length", "0") == "0",
        f"Content-Length: {r.headers.get('content-length', 'absent')}")
    print()

    # Verify deletion
    print("  Verifying Bob is deleted...")
    r = client.get(f"/students/{bob_id}")
    log("GET deleted student returns 404", r.status_code == 404, f"Status: {r.status_code}")
    log("404 detail mentions student ID", str(bob_id) in r.json().get("detail", ""))
    print()

    # Verify Alice still exists
    r = client.get(f"/students/{alice_id}")
    log("Alice still exists after Bob's deletion", r.status_code == 200)
    print()

    # Verify student count decreased
    r = client.get("/students/")
    log("Student count is now 1", len(r.json()) == 1, f"Count: {len(r.json())}")
    print()

    # ─────────────────────────────────────────────────────────────────────
    # 8. Duplicate email handling (409 Conflict)
    # ─────────────────────────────────────────────────────────────────────
    print("─" * 70)
    print("8. Duplicate email handling  (POST with Alice's email again)")
    print("─" * 70)

    duplicate = {
        "name": "Fake Alice",
        "email": "alice@university.edu",
        "age": 25,
        "department": "Physics",
        "year_of_study": 1,
    }
    r = client.post("/students/", json=duplicate)
    log("Duplicate email returns 409", r.status_code == 409, f"Status: {r.status_code}")
    log("Error detail mentions email", "alice@university.edu" in r.json().get("detail", ""))
    print(f"  Response body: {r.json()}\n")

    # ─────────────────────────────────────────────────────────────────────
    # 9. Invalid input handling (422 Unprocessable Entity)
    # ─────────────────────────────────────────────────────────────────────
    print("─" * 70)
    print("9. Invalid input handling  (422 Unprocessable Entity)")
    print("─" * 70)

    # Invalid email
    bad_email = {**student_data, "email": "not-an-email"}
    r = client.post("/students/", json=bad_email)
    log("Invalid email → 422", r.status_code == 422, f"Status: {r.status_code}")

    # Age too low
    bad_age_low = {**student_data, "email": "unique1@test.edu", "age": 10}
    r = client.post("/students/", json=bad_age_low)
    log("Age < 16 → 422", r.status_code == 422, f"Status: {r.status_code}")

    # Age too high
    bad_age_high = {**student_data, "email": "unique2@test.edu", "age": 200}
    r = client.post("/students/", json=bad_age_high)
    log("Age > 100 → 422", r.status_code == 422, f"Status: {r.status_code}")

    # Missing required field
    missing = {"name": "Test", "age": 20}
    r = client.post("/students/", json=missing)
    log("Missing fields → 422", r.status_code == 422, f"Status: {r.status_code}")

    # Empty body
    r = client.post("/students/", json={})
    log("Empty body → 422", r.status_code == 422, f"Status: {r.status_code}")
    print()

    # ─────────────────────────────────────────────────────────────────────
    # 10. Nonexistent student handling (404)
    # ─────────────────────────────────────────────────────────────────────
    print("─" * 70)
    print("10. Nonexistent student handling  (404 Not Found)")
    print("─" * 70)

    r = client.get("/students/99999")
    log("GET nonexistent → 404", r.status_code == 404, f"Status: {r.status_code}")

    r = client.put("/students/99999", json={"age": 25})
    log("PUT nonexistent → 404", r.status_code == 404, f"Status: {r.status_code}")

    r = client.delete("/students/99999")
    log("DELETE nonexistent → 404", r.status_code == 404, f"Status: {r.status_code}")
    print()

    # ─────────────────────────────────────────────────────────────────────
    # 11. Swagger docs accessibility
    # ─────────────────────────────────────────────────────────────────────
    print("─" * 70)
    print("11. Swagger documentation  (GET /docs)")
    print("─" * 70)

    r = client.get("/docs")
    log("GET /docs returns 200", r.status_code == 200, f"Status: {r.status_code}")
    log("Response is HTML", "text/html" in r.headers.get("content-type", ""))
    log("HTML contains 'swagger'", "swagger" in r.text.lower())
    print()

    r = client.get("/openapi.json")
    log("GET /openapi.json returns 200", r.status_code == 200)
    openapi = r.json()
    log("OpenAPI title correct", openapi.get("info", {}).get("title") == "Student Management API")
    log("OpenAPI version correct", openapi.get("info", {}).get("version") == "1.0.0")
    print()

    # ─────────────────────────────────────────────────────────────────────
    # CLEANUP: Delete Alice to restore empty database state
    # ─────────────────────────────────────────────────────────────────────
    print("─" * 70)
    print("CLEANUP: Deleting test data (Alice)")
    print("─" * 70)
    r = client.delete(f"/students/{alice_id}")
    log("Cleanup: Alice deleted", r.status_code == 204)
    r = client.get("/students/")
    log("Database is empty after cleanup", r.json() == [])
    print()

    client.close()

    # ─────────────────────────────────────────────────────────────────────
    # SUMMARY
    # ─────────────────────────────────────────────────────────────────────
    print("=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, p, _ in results if p)
    failed = sum(1 for _, p, _ in results if not p)
    total = len(results)

    print(f"\n  Total:  {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")

    if failed > 0:
        print("\n  ❌ FAILED TESTS:")
        for name, p, detail in results:
            if not p:
                print(f"    - {name}: {detail}")

    print()
    if failed == 0:
        print("  🎉 ALL LIVE VERIFICATION TESTS PASSED!")
    else:
        print("  ⚠️  Some tests failed. Review the output above.")

    print("=" * 70)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
