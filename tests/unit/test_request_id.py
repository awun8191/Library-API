"""Unit tests for the request identifier policy."""
from middleware.request_id import get_request_id, is_valid_request_id


def test_get_request_id_returns_the_default_value_outside_a_request() -> None:
    assert get_request_id() == "-"


def test_the_validator_allows_safe_values_only() -> None:
    assert is_valid_request_id("client.abc_123-XYZ") is True
    assert is_valid_request_id("a" * 64) is True
    assert is_valid_request_id("") is False
    assert is_valid_request_id("a" * 65) is False
    assert is_valid_request_id("has space") is False
    assert is_valid_request_id("semi;colon") is False
    assert is_valid_request_id("line\nbreak") is False
