# CardioSense

CardioSense is a production-oriented heart disease inference service built around:

- XGBoost prediction with leak-safe preprocessing
- Threshold optimization for imbalanced evaluation objectives
- FastAPI single and batch inference endpoints
- MongoDB-backed operational persistence
- Model registry, rollback support, and drift snapshots
- Feedback labeling and API request audit logs

## Key paths

- Architecture plan: `docs/architecture_plan.md`
- Runbook: `docs/runbook.md`
- Environment template: `.env.example`
- API entrypoint: `api.py`
- Training pipeline: `main.py`

## Structure

```text
heart-disease-inference/
|- api.py
|- config.py
|- main.py
|- .env.example
|- docs/
|- src/
|  |- core/
|  |- repositories/
|  |- schemas/
|  |- services/
|  \- existing ML modules
|- tests/
|- data/
|- outputs/
\- plots/
```

## Core operational features

- Registry-backed active model loading with rollback support
- Prediction persistence with `model_version`, threshold, probabilities, and confidence tier
- Pseudonymous subject records for operational linkage without storing plain identifiers
- Drift monitoring snapshots using feature PSI and prediction-rate shift alerts
- Feedback endpoint for attaching reviewed labels to stored predictions

## Quick start

```powershell
python -m pip install -r requirements.txt
python main.py
python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

## Docker quick start

Docker packages the API, Python dependencies, and saved model artifacts into a
repeatable container so the service runs the same way on another machine.

From the repository root, run the API only with the in-memory backend:

```powershell
docker build -t cardiosense-ml-api .\ml
docker run --rm -p 8000:8000 -e CARDIOSENSE_DB_BACKEND=inmemory cardiosense-ml-api
```

Or run the API with MongoDB persistence:

```powershell
docker compose up --build
```

Then check the service:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

The interactive API docs are available at `http://127.0.0.1:8000/docs`.

## Validation

```powershell
$env:CARDIOSENSE_DB_BACKEND="inmemory"
python -m pytest -q tests
```
