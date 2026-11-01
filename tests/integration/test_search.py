"""Integration tests for the book listing, search, filter, and pagination rules."""

from fastapi.testclient import TestClient

BOOKS_URL = "/api/v1/books"


def list_books(client: TestClient, **params):
    """Call the public book list endpoint."""
    return client.get(BOOKS_URL, params=params)


def test_list_is_public(client: TestClient, make_book) -> None:
    book = make_book(name="Intro to Algorithms")

    response = list_books(client)

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["items"]] == [book.id]
    assert body["has_more"] is False
    assert body["next_cursor"] is None


def test_q_matches_a_substring_of_the_name(client: TestClient, make_book) -> None:
    match = make_book(name="Intro to Algorithms")
    make_book(name="Linear Algebra")

    response = list_books(client, q="Algo")

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["items"]] == [match.id]


def test_q_is_case_insensitive(client: TestClient, make_book) -> None:
    book = make_book(name="Intro to Algorithms")

    response = list_books(client, q="ALGORITHMS")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [book.id]


def test_a_literal_percent_sign_matches_nothing(client: TestClient, make_book) -> None:
    make_book(name="Intro to Algorithms")
    make_book(name="Linear Algebra")

    response = list_books(client, q="%")

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_course_code_matches_and_ignores_case(client: TestClient, make_book) -> None:
    match = make_book(name="Intro to Algorithms", course_code="CSC201")
    make_book(name="Linear Algebra", course_code="MTH101")

    response = list_books(client, course_code="csc201")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [match.id]


def test_department_id_filters(client: TestClient, make_book, make_department) -> None:
    wanted = make_department(name="Computer Science")
    other = make_department(name="Mathematics")
    match = make_book(name="Intro to Algorithms", department_id=wanted.id)
    make_book(name="Linear Algebra", department_id=other.id)

    response = list_books(client, department_id=wanted.id)

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [match.id]


def test_combined_filters_return_the_intersection(
    client: TestClient, make_book, make_department
) -> None:
    wanted = make_department(name="Computer Science")
    other = make_department(name="Mathematics")
    match = make_book(name="Intro to Algorithms", course_code="CSC201", department_id=wanted.id)
    make_book(name="Intro to Algorithms", course_code="CSC201", department_id=other.id)
    make_book(name="Linear Algebra", course_code="MTH101", department_id=wanted.id)

    response = list_books(client, q="Intro", course_code="CSC201", department_id=wanted.id)

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["items"]] == [match.id]
    assert body["has_more"] is False


def test_unknown_filters_return_an_empty_list(client: TestClient, make_book) -> None:
    make_book(name="Intro to Algorithms")

    response = list_books(client, department_id=987654, course_code="NONE999")

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["has_more"] is False
    assert body["next_cursor"] is None


def test_pagination_walk_returns_every_id_once_in_ascending_order(
    client: TestClient, make_book
) -> None:
    created = [
        make_book(name=f"Book {index}", course_code=f"CSC10{index}").id for index in range(3)
    ]

    collected = []
    cursor = None
    for _ in range(5):
        params = {"limit": 1}
        if cursor is not None:
            params["cursor"] = cursor
        body = list_books(client, **params).json()
        collected.extend(item["id"] for item in body["items"])
        if not body["has_more"]:
            break
        cursor = body["next_cursor"]

    assert collected == sorted(created)
    assert len(collected) == len(set(collected)) == 3


def test_the_last_page_reports_no_more_items(client: TestClient, make_book) -> None:
    first = make_book(name="Book One")
    second = make_book(name="Book Two")

    page = list_books(client, limit=1).json()
    assert page["has_more"] is True
    assert page["next_cursor"] == first.id

    last = list_books(client, limit=1, cursor=page["next_cursor"]).json()

    assert [item["id"] for item in last["items"]] == [second.id]
    assert last["has_more"] is False
    assert last["next_cursor"] is None


def test_limit_bounds_return_400(client: TestClient) -> None:
    for limit in (0, 101):
        response = list_books(client, limit=limit)

        assert response.status_code == 400
        body = response.json()
        assert body["code"] == "INVALID_REQUEST"
        assert [error["field"] for error in body["errors"]] == ["limit"]


def test_a_cursor_beyond_the_last_id_returns_an_empty_page(client: TestClient, make_book) -> None:
    book = make_book()

    response = list_books(client, cursor=book.id + 1000)

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["has_more"] is False
    assert body["next_cursor"] is None
