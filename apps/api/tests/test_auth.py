from speechify_api import auth


def test_hash_and_verify_password_roundtrip():
    hashed = auth.hash_password("correct horse battery staple")
    assert auth.verify_password("correct horse battery staple", hashed)
    assert not auth.verify_password("wrong password", hashed)


def test_create_and_decode_access_token_roundtrip():
    token = auth.create_access_token(42)
    assert auth.decode_access_token(token) == 42
