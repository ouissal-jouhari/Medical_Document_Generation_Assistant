from fastapi.testclient import TestClient


def test_N15_health_endpoint_is_reachable(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
