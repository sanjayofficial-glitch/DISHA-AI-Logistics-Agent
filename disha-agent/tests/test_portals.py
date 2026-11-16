"""Portal endpoints tests."""
from .conftest import auth_headers, demo_token


def test_shipper_requests(client):
    tok = demo_token("demo-shipper-01")
    r = client.get("/portal/shipper/requests", headers=auth_headers(tok))
    assert r.status_code == 200
    reqs = r.json()["requests"]
    assert isinstance(reqs, list)
    # seed contains requests for demo-shipper-01
    assert any(x["shipper_user_id"] == "demo-shipper-01" for x in reqs)


def test_trucker_shipments_scored(client):
    tok = demo_token("demo-transporter-01")
    r = client.get("/portal/trucker/shipments", headers=auth_headers(tok))
    assert r.status_code == 200
    shipments = r.json()["shipments"]
    assert shipments
    for s in shipments:
        assert "score" in s
        assert "factors" in s
        assert s["is_demo"] is True
    scores = [s["score"] for s in shipments]
    assert scores == sorted(scores, reverse=True)


def test_trucker_offers(client):
    tok = demo_token("demo-transporter-01")
    r = client.get("/portal/trucker/offers", headers=auth_headers(tok))
    assert r.status_code == 200
    offers = r.json()["offers"]
    assert offers
    assert all(o["transporter_user_id"] == "demo-transporter-01" for o in offers)


def test_notifications(client):
    tok = demo_token("demo-transporter-01")
    r = client.get("/portal/notifications", headers=auth_headers(tok))
    assert r.status_code == 200
    assert isinstance(r.json()["notifications"], list)
