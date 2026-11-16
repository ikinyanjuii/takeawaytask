from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    assert client.get("/health").json()["status"] == "ok"

def test_create_and_list_request():
    response = client.post("/api/requests", json={
        "title": "Add project notifications",
        "description": "I need to receive timely notifications when a project task is assigned to me.",
        "customer_segment": "SMB"})
    assert response.status_code == 201
    request_id = response.json()["id"]
    assert any(row["id"] == request_id for row in client.get("/api/requests").json())

def test_demo_seed_is_idempotent():
    first = client.post("/api/demo/seed")
    second = client.post("/api/demo/seed")
    assert first.status_code == 200 and second.status_code == 200
