import os

os.environ["CARDIOSENSE_DB_BACKEND"] = "inmemory"

from fastapi.testclient import TestClient

from src.core.settings import get_settings

get_settings.cache_clear()

from api import app


def _request(method: str, path: str, **kwargs):
    with TestClient(app) as client:
        return client.request(method, path, **kwargs)


def _valid_payload():
    return {
        "id": 101,
        "age": 18393,
        "gender": 2,
        "height": 168,
        "weight": 62.0,
        "ap_hi": 120,
        "ap_lo": 80,
        "cholesterol": 1,
        "gluc": 1,
        "smoke": 0,
        "alco": 0,
        "active": 1,
    }


def _signup_payload():
    return {
        "full_name": "Asef User",
        "email": "asef@example.com",
        "password": "securepass123",
        "role": "student",
    }


def test_health_endpoint():
    resp = _request("GET", "/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in {"ready", "degraded", "loading"}
    assert body["db_backend"] == "inmemory"


def test_predict_valid_payload():
    resp = _request("POST", "/predict", json=_valid_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["model_version"]
    assert body["prediction_id"]
    assert body["result"]["confidence_tier"] in {"HIGH", "MEDIUM", "LOW"}


def test_predict_validation_error():
    payload = _valid_payload()
    payload["ap_lo"] = 20
    resp = _request("POST", "/predict", json=payload)
    assert resp.status_code == 422


def test_feedback_round_trip_after_prediction():
    with TestClient(app) as client:
        predict_resp = client.post("/predict", json=_valid_payload())
        prediction_id = predict_resp.json()["prediction_id"]
        feedback_resp = client.post(
            "/feedback",
            json={
                "prediction_id": prediction_id,
                "true_label": 1,
                "label_source": "human_review",
                "reviewer": "qa",
            },
        )
    assert feedback_resp.status_code == 200
    assert feedback_resp.json()["prediction_id"] == prediction_id


def test_feedback_not_found_returns_404():
    resp = _request(
        "POST",
        "/feedback",
        json={
            "prediction_id": "prediction_missing",
            "true_label": 1,
            "label_source": "human_review",
        },
    )
    assert resp.status_code == 404


def test_predict_idempotency_replay_returns_same_prediction_id():
    with TestClient(app) as client:
        headers = {"X-Idempotency-Key": "predict-123"}
        first = client.post("/predict", json=_valid_payload(), headers=headers)
        second = client.post("/predict", json=_valid_payload(), headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["prediction_id"] == second.json()["prediction_id"]
    assert first.json()["request_id"] == second.json()["request_id"]


def test_predict_idempotency_conflict_returns_409():
    with TestClient(app) as client:
        headers = {"X-Idempotency-Key": "predict-456"}
        first = client.post("/predict", json=_valid_payload(), headers=headers)
        changed = _valid_payload()
        changed["weight"] = 72.0
        second = client.post("/predict", json=changed, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 409


def test_analytics_summary_endpoint_returns_grouped_results():
    with TestClient(app) as client:
        client.post("/predict", json=_valid_payload(), headers={"X-Idempotency-Key": "analytics-1"})
        resp = client.get("/analytics/summary", params={"bucket": "day"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["bucket"] == "day"
    assert body["groups"]
    assert {"model_version", "date_bucket", "confidence_tier"}.issubset(body["groups"][0])


def test_auth_signup_and_login_round_trip():
    payload = _signup_payload()
    with TestClient(app) as client:
        signup_resp = client.post("/auth/signup", json=payload)
        login_resp = client.post(
            "/auth/login",
            json={"email": payload["email"], "password": payload["password"]},
        )

    assert signup_resp.status_code == 200
    signup_body = signup_resp.json()
    assert signup_body["token_type"] == "bearer"
    assert signup_body["user"]["email"] == payload["email"]

    assert login_resp.status_code == 200
    login_body = login_resp.json()
    assert login_body["token_type"] == "bearer"
    assert login_body["user"]["email"] == payload["email"]
    assert login_body["user"]["last_login_at"] is not None


def test_auth_signup_duplicate_email_returns_409():
    payload = _signup_payload()
    with TestClient(app) as client:
        first = client.post("/auth/signup", json=payload)
        second = client.post("/auth/signup", json=payload)

    assert first.status_code == 200
    assert second.status_code == 409


def test_auth_login_invalid_password_returns_401():
    payload = _signup_payload()
    with TestClient(app) as client:
        signup_resp = client.post("/auth/signup", json=payload)
        bad_login = client.post(
            "/auth/login",
            json={"email": payload["email"], "password": "wrongpass123"},
        )

    assert signup_resp.status_code == 200
    assert bad_login.status_code == 401
