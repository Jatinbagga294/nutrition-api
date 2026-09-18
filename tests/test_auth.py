def test_signup_returns_user_without_password(client):
    r = client.post("/auth/signup", json={"email": "a@b.com", "password": "password123"})
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "a@b.com"
    # The hash must never leave the server.
    assert "password" not in body and "password_hash" not in body


def test_duplicate_email_rejected(client):
    payload = {"email": "a@b.com", "password": "password123"}
    client.post("/auth/signup", json=payload)
    assert client.post("/auth/signup", json=payload).status_code == 409


def test_short_password_rejected(client):
    r = client.post("/auth/signup", json={"email": "a@b.com", "password": "short"})
    assert r.status_code == 422


def test_login_wrong_password_is_401(client):
    client.post("/auth/signup", json={"email": "a@b.com", "password": "password123"})
    r = client.post("/auth/login", data={"username": "a@b.com", "password": "wrong"})
    assert r.status_code == 401


def test_unknown_email_and_wrong_password_look_identical(client):
    """No user enumeration: both failures must return the same message."""
    client.post("/auth/signup", json={"email": "a@b.com", "password": "password123"})
    bad_pw = client.post("/auth/login", data={"username": "a@b.com", "password": "wrong"})
    no_user = client.post("/auth/login", data={"username": "nobody@b.com", "password": "wrong"})
    assert bad_pw.json() == no_user.json()


def test_protected_route_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_garbage_token_rejected(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert r.status_code == 401


def test_me_returns_current_user(client, auth_headers):
    r = client.get("/auth/me", headers=auth_headers)
    assert r.status_code == 200 and r.json()["email"] == "test@example.com"
