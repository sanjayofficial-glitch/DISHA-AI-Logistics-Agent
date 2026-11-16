"""Memory endpoints: list/add/correct/delete with strict per-user isolation."""
from .conftest import auth_headers, demo_token


def test_memory_lifecycle(client):
    tok = demo_token("demo-shipper-01")
    r = client.post("/memory", json={"text": "Shipper prefers early morning pickup"}, headers=auth_headers(tok))
    assert r.status_code == 200
    fid = r.json()["fact"]["id"]

    facts = client.get("/memory", headers=auth_headers(tok)).json()["facts"]
    assert any(f["id"] == fid for f in facts)

    r = client.patch(f"/memory/{fid}", json={"text": "Shipper prefers 7 AM pickup"}, headers=auth_headers(tok))
    assert r.status_code == 200
    assert r.json()["fact"]["text"] == "Shipper prefers 7 AM pickup"

    r = client.delete(f"/memory/{fid}", headers=auth_headers(tok))
    assert r.status_code == 200
    facts = client.get("/memory", headers=auth_headers(tok)).json()["facts"]
    assert all(f["id"] != fid for f in facts)


def test_memory_isolation(client):
    a = demo_token("demo-shipper-01")
    b = demo_token("demo-shipper-02")
    client.post("/memory", json={"text": "secret fact of user A"}, headers=auth_headers(a))
    facts_b = client.get("/memory", headers=auth_headers(b)).json()["facts"]
    assert all("secret fact" not in f["text"] for f in facts_b)
    # B cannot update/delete A's fact
    facts_a = client.get("/memory", headers=auth_headers(a)).json()["facts"]
    fid = facts_a[0]["id"]
    assert client.patch(f"/memory/{fid}", json={"text": "hacked"}, headers=auth_headers(b)).status_code == 404
    assert client.delete(f"/memory/{fid}", headers=auth_headers(b)).status_code == 404


def test_remember_via_chat(client):
    tok = demo_token("demo-shipper-01")
    r = client.post("/chat", json={"message": "remember that I prefer trailers only"}, headers=auth_headers(tok))
    assert r.status_code == 200
    facts = client.get("/memory", headers=auth_headers(tok)).json()["facts"]
    assert any("trailers" in f["text"] for f in facts)
