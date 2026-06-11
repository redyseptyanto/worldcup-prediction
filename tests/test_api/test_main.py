from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_api_root_and_predict_match() -> None:
    root_response = client.get("/")
    assert root_response.status_code == 200
    assert root_response.json()["status"] == "ok"

    prediction_response = client.post(
        "/predict/match",
        json={"home_team": "Brazil", "away_team": "United States"},
    )
    assert prediction_response.status_code == 200
    payload = prediction_response.json()
    assert payload["home_team"] == "Brazil"
    assert payload["away_team"] == "United States"
