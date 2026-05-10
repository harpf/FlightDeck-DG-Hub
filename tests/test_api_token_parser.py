from app.routes import _parse_api_token


def test_parse_api_token_valid():
    token_id, secret = _parse_api_token("12.abc")
    assert token_id == 12
    assert secret == "abc"


def test_parse_api_token_invalid():
    token_id, secret = _parse_api_token("bad-token")
    assert token_id is None
    assert secret is None
