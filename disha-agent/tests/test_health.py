from .conftest import auth_headers, demo_token


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "DISHA"
    assert body["database"] == "reachable"
    assert body["demo_mode"] is True


def test_health_no_secrets(client):
    r = client.get("/health")
    assert "secret" not in r.text.lower()
    assert "api_key" not in r.text.lower()


def test_demo_login_returns_token(client):
    r = client.post("/auth/demo-login", json={"user_id": "demo-shipper-01", "display_name": "Demo Shipper 01"})
    assert r.status_code == 200
    body = r.json()
    assert body["token"]
    assert body["demo_mode"] is True


def test_api_requires_auth(client):
    r = client.get("/threads")
    assert r.status_code == 401
    r = client.post("/chat", json={"message": "hi"})
    assert r.status_code == 401
