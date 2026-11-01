"""Integration tests for the shared error envelope and routing contracts."""

from fastapi.testclient import TestClient

from tests.integration.test_auth import signup_payload
from tests.integration.test_books import upload_book


def test_handled_errors_include_message_and_code(
    client: TestClient, make_user, auth_headers
) -> None:
    make_user(email="taken@school.edu")
    student = make_user(role="user")

    responses = [
        client.get("/api/v1/books/987654"),
        client.get("/api/v1/users/me"),
        client.post("/api/v1/auth/signup", json=signup_payload(email="taken@school.edu")),
        client.patch("/api/v1/books/987654", json={"name": "Nope"}, headers=auth_headers(student)),
    ]

    for response in responses:
        body = response.json()
        assert response.status_code >= 400
        assert set(body) == {"message", "code"}
        assert isinstance(body["message"], str) and body["message"]
        assert isinstance(body["code"], str) and body["code"]
        assert body["code"] == body["code"].upper()


def test_a_validation_error_includes_message_code_and_errors(
    client: TestClient,
) -> None:
    response = client.post("/api/v1/auth/signup", json=signup_payload(password="short"))

    assert response.status_code == 400
    body = response.json()
    assert set(body) == {"message", "code", "errors"}
    assert body["message"] == "Invalid request data"
    assert body["code"] == "INVALID_REQUEST"
    assert body["errors"]
    for error in body["errors"]:
        assert set(error) == {"field", "error"}
        assert error["field"]
        assert error["error"]


def test_a_401_sends_the_www_authenticate_header(client: TestClient) -> None:
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_an_unknown_route_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")


def test_a_wrong_method_returns_405(client: TestClient) -> None:
    response = client.delete("/api/v1/departments")

    assert response.status_code == 405
    assert "GET" in response.headers["allow"]


def test_the_duplicate_upload_error_does_not_leak_internals(
    client: TestClient, make_user, make_department, make_pdf, auth_headers
) -> None:
    admin = make_user(role="admin")
    department = make_department()
    content = make_pdf("contract-duplicate")
    upload_book(client, auth_headers(admin), department.id, content)

    response = upload_book(client, auth_headers(admin), department.id, content)

    assert response.status_code == 409
    text = response.text
    lowered = text.lower()
    assert "traceback" not in lowered
    assert "insert into" not in lowered
    assert "sqlalchemy" not in lowered
    assert "psycopg" not in lowered
    assert "detail:" not in lowered
    assert "file_hash" not in lowered
