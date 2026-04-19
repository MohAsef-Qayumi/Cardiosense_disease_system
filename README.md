# PF AI Project Workspace

This workspace now has a clean, domain-based structure so each project is easy to find and maintain.

## Structure

```text
PF_AI_Project/
|- web/
|  \- cardiosense-react/         # React frontend
|     |- src/
|     |- public/
|     |- package.json
|     \- vite.config.ts
|
\- ml/
   |- main.py
   |- api.py
   |- config.py
   |- Dockerfile
   |- src/
   |- tests/
   |- data/
   |- outputs/
   \- plots/
```

## Quick Start

- Web project: `cd web/cardiosense-react`, then `npm install` and `npm run dev`.
- ML project:
  1. `cd ml`
  2. `pip install -r requirements.txt`
  3. `python main.py`
  4. `uvicorn api:app --host 0.0.0.0 --port 8000`

## Docker Quick Start

From the repository root:

```powershell
docker build -t cardiosense-ml-api .\ml
docker run --rm -p 8000:8000 -e CARDIOSENSE_DB_BACKEND=inmemory cardiosense-ml-api
```

For the API plus MongoDB:

```powershell
docker compose up --build
```

Open `http://127.0.0.1:8000/docs` for the API docs.
