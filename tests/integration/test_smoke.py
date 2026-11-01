"""Integration tests that prove the test harness works."""

from fastapi.testclient import TestClient


def test_departments_endpoint_returns_a_list(client: TestClient, make_department) -> None:
    department = make_department(name="Computer Science")

    response = client.get("/api/v1/departments")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert [item["id"] for item in body] == [department.id]
    assert body[0]["name"] == "Computer Science"


def test_signup_returns_the_public_fields_only(client: TestClient) -> None:
    payload = {
        "first_name": "Ada",
        "last_name": "Obi",
        "email": "ada@school.edu",
        "password": "strong-password",
    }

    response = client.post("/api/v1/auth/signup", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {
        "id",
        "first_name",
        "last_name",
        "email",
        "role",
        "is_active",
        "department_id",
    }
    assert body["email"] == "ada@school.edu"
    assert body["role"] == "user"
    assert body["is_active"] is True
    assert "password_hash" not in body
