# CardioSense Runbook

## 1. Install dependencies

```powershell
cd c:\Users\DAR\Desktop\PF_AI_Project\ml\heart-disease-inference
python -m pip install -r requirements.txt
```

Expected outcome:
- `pymongo`, `fastapi`, `xgboost`, `scikit-learn`, and test dependencies install successfully.

## 2. Start MongoDB

Option A: local service

```powershell
mongod --dbpath C:\data\db
```

Option B: Docker

```powershell
docker run --name cardiosense-mongo -p 27017:27017 -d mongo:7
```

Expected outcome:
- MongoDB listens on `mongodb://127.0.0.1:27017`.

For MongoDB Atlas instead of local MongoDB:

```powershell
$env:CARDIOSENSE_DB_BACKEND="mongodb"
$env:CARDIOSENSE_MONGODB_URI="mongodb+srv://<username>:<db_password>@<cluster-host>/?appName=Cluster0"
$env:CARDIOSENSE_MONGODB_PASSWORD="your-atlas-db-password"
$env:CARDIOSENSE_MONGODB_DATABASE="cardiosense"
$env:CARDIOSENSE_MONGODB_CONNECT_TIMEOUT_MS="10000"
```

Expected outcome:
- API connects to Atlas using TLS through the SRV URI.
- If URI contains `<db_password>`, the runtime replaces it using `CARDIOSENSE_MONGODB_PASSWORD`.

## 3. Configure environment

```powershell
$env:CARDIOSENSE_DB_BACKEND="mongodb"
$env:CARDIOSENSE_MONGODB_URI="mongodb://127.0.0.1:27017"
$env:CARDIOSENSE_MONGODB_PASSWORD=""
$env:CARDIOSENSE_MONGODB_DATABASE="cardiosense"
$env:CARDIOSENSE_HASH_SALT="replace-this"
$env:CARDIOSENSE_ENABLE_THRESHOLD_OPTIMIZATION="true"
$env:CARDIOSENSE_THRESHOLD_OPTIMIZATION_OBJECTIVE="balanced_accuracy"
```

Expected outcome:
- The API and training pipeline target MongoDB for operational state.
- On startup, required collections and indexes (including `users.email` unique index) are created automatically.

## 4. Train and register the active model

```powershell
python main.py
```

Expected outcome:
- Model artifacts are saved under `outputs/models/`.
- Metrics are saved under `outputs/results/`.
- A model version record is created and activated.
- A training baseline drift snapshot is persisted.

## 5. Start the API

```powershell
python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

Expected outcome:
- `GET http://127.0.0.1:8000/health` returns `status=ready`.
- `GET http://127.0.0.1:8000/models/active` returns the active model version.

## 6. Run automated validation

```powershell
$env:CARDIOSENSE_DB_BACKEND="inmemory"
python -m pytest -q tests
```

Expected outcome:
- All tests pass.
- In this workspace the expected result is `15 passed`.

## 7. Verify readiness manually

Single prediction:

```powershell
curl -X POST http://127.0.0.1:8000/predict ^
  -H "Content-Type: application/json" ^
  -H "X-Idempotency-Key: demo-1" ^
  -d "{\"id\":101,\"age\":18393,\"gender\":2,\"height\":168,\"weight\":62,\"ap_hi\":120,\"ap_lo\":80,\"cholesterol\":1,\"gluc\":1,\"smoke\":0,\"alco\":0,\"active\":1}"
```

Feedback attachment:

```powershell
curl -X POST http://127.0.0.1:8000/feedback ^
  -H "Content-Type: application/json" ^
  -d "{\"prediction_id\":\"<prediction_id>\",\"true_label\":1,\"label_source\":\"human_review\"}"
```

Rollback:

```powershell
curl -X POST http://127.0.0.1:8000/models/rollback ^
  -H "Content-Type: application/json" ^
  -d "{}"
```

Expected outcome:
- Prediction responses include `prediction_id`, `model_version`, `threshold_used`, and `result`.
- Feedback succeeds for known prediction ids.
- Rollback returns the newly activated model version metadata.

Auth signup/login:

```powershell
curl -X POST http://127.0.0.1:8000/auth/signup ^
  -H "Content-Type: application/json" ^
  -d "{\"full_name\":\"Demo User\",\"email\":\"demo@example.com\",\"password\":\"securepass123\",\"role\":\"student\"}"

curl -X POST http://127.0.0.1:8000/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"demo@example.com\",\"password\":\"securepass123\"}"
```

Expected outcome:
- Signup persists a user profile in MongoDB `users` collection.
- Login validates password hash and returns a bearer token payload.
