from datetime import date


def test_create_and_list_entry(client, auth_headers):
    r = client.post("/entries", json={"name": "Oats", "calories": 320, "protein_g": 11},
                    headers=auth_headers)
    assert r.status_code == 201 and r.json()["name"] == "Oats"
    assert len(client.get("/entries", headers=auth_headers).json()) == 1


def test_entries_require_auth(client):
    assert client.get("/entries").status_code == 401
    assert client.post("/entries", json={"name": "x", "calories": 1}).status_code == 401


def test_negative_calories_rejected(client, auth_headers):
    r = client.post("/entries", json={"name": "x", "calories": -5}, headers=auth_headers)
    assert r.status_code == 422


def test_summary_aggregates_the_day(client, auth_headers):
    today = date.today().isoformat()
    for cals, p in [(300, 10), (500, 25), (200, 5)]:
        client.post("/entries", json={"name": "f", "calories": cals, "protein_g": p,
                                      "logged_on": today}, headers=auth_headers)
    s = client.get("/entries/summary", headers=auth_headers).json()
    assert s["total_calories"] == 1000
    assert s["total_protein_g"] == 40
    assert s["entry_count"] == 3
    assert s["remaining"] == 1000  # default goal 2000


def test_summary_of_empty_day_is_zero_not_error(client, auth_headers):
    s = client.get("/entries/summary?on=2020-01-01", headers=auth_headers).json()
    assert s["total_calories"] == 0 and s["entry_count"] == 0


def test_user_cannot_see_another_users_entries(client, auth_headers):
    """The core authorization guarantee."""
    client.post("/entries", json={"name": "Mine", "calories": 100}, headers=auth_headers)

    client.post("/auth/signup", json={"email": "other@example.com", "password": "password123"})
    r = client.post("/auth/login",
                    data={"username": "other@example.com", "password": "password123"})
    other = {"Authorization": f"Bearer {r.json()['access_token']}"}

    assert client.get("/entries", headers=other).json() == []
    assert client.get("/entries/summary", headers=other).json()["total_calories"] == 0


def test_user_cannot_delete_another_users_entry(client, auth_headers):
    entry_id = client.post("/entries", json={"name": "Mine", "calories": 100},
                           headers=auth_headers).json()["id"]

    client.post("/auth/signup", json={"email": "other@example.com", "password": "password123"})
    r = client.post("/auth/login",
                    data={"username": "other@example.com", "password": "password123"})
    other = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # 404, not 403: a 403 would confirm the id exists.
    assert client.delete(f"/entries/{entry_id}", headers=other).status_code == 404
    assert len(client.get("/entries", headers=auth_headers).json()) == 1


def test_delete_own_entry(client, auth_headers):
    eid = client.post("/entries", json={"name": "x", "calories": 1},
                      headers=auth_headers).json()["id"]
    assert client.delete(f"/entries/{eid}", headers=auth_headers).status_code == 204
    assert client.get("/entries", headers=auth_headers).json() == []


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
