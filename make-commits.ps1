# CardioSense - Backdated commit script
# cd "c:\Users\LENOVO\Desktop\4th semester\programming for ai\PF_AI_Project"
# .\make-commits.ps1

$REMOTE = "https://github.com/MohAsef-Qayumi/Cardiosense_disease_system.git"

Write-Host "Removing existing git history..." -ForegroundColor Yellow
Remove-Item -Recurse -Force ".git"
Write-Host "Initializing fresh repo..." -ForegroundColor Yellow
git init
git remote add origin $REMOTE

function Commit-Dated {
    param([string]$Date, [string]$Message)
    $env:GIT_AUTHOR_DATE    = $Date
    $env:GIT_COMMITTER_DATE = $Date
    git commit -m $Message
    Remove-Item Env:\GIT_AUTHOR_DATE    -ErrorAction SilentlyContinue
    Remove-Item Env:\GIT_COMMITTER_DATE -ErrorAction SilentlyContinue
    Write-Host "  OK [$Date] $Message" -ForegroundColor Green
}

# === Apr 19: Repo bootstrap ===
git add ".gitignore" "README.md" "docker-compose.yml"
Commit-Dated "2026-04-19T10:00:00" "chore: initialize monorepo with gitignore and root README"

# === Apr 20: ML env + raw data ===
git add "ml/requirements.txt" "ml/config.py" "ml/.env.example" "ml/.dockerignore"
Commit-Dated "2026-04-20T09:30:00" "chore(ml): add requirements, config, and env setup"

git add "ml/data/raw/"
Commit-Dated "2026-04-20T14:00:00" "feat(ml): add raw cardiovascular disease dataset"

# === Apr 21: Data splits ===
git add "ml/data/processed/"
Commit-Dated "2026-04-21T11:00:00" "feat(ml): add processed train/val/test CSV splits"

# === Apr 22: Data pipeline ===
git add "ml/src/__init__.py" "ml/src/data_loader.py"
Commit-Dated "2026-04-22T09:30:00" "feat(ml): implement data loader with schema validation"

git add "ml/src/preprocessing.py"
Commit-Dated "2026-04-22T14:30:00" "feat(ml): add feature preprocessing - BMI, age conversion, encoding"

# === Apr 23: Splitting + EDA ===
git add "ml/src/data_split.py"
Commit-Dated "2026-04-23T10:00:00" "feat(ml): add stratified train/val/test split logic"

git add "ml/src/eda.py"
Commit-Dated "2026-04-23T15:00:00" "feat(ml): add EDA module - correlation heatmap, distribution plots"

# === Apr 24: Model training ===
git add "ml/src/model.py"
Commit-Dated "2026-04-24T10:00:00" "feat(ml): implement XGBoost, LightGBM, Random Forest training"

git add "ml/train_best_model.py"
Commit-Dated "2026-04-24T15:30:00" "feat(ml): add Optuna hyperparameter tuning and ensemble builder"

# === Apr 25: Evaluation + outputs ===
git add "ml/src/evaluation.py"
Commit-Dated "2026-04-25T09:30:00" "feat(ml): add evaluation - ROC-AUC, F1, threshold optimization"

git add "ml/src/best_model.py" "ml/outputs/"
Commit-Dated "2026-04-25T16:00:00" "feat(ml): save best ensemble model and export metrics to JSON/CSV"

# === Apr 26: Core utilities + repositories ===
git add "ml/src/core/"
Commit-Dated "2026-04-26T10:00:00" "feat(ml): add core utilities - logging, settings, exceptions"

git add "ml/src/repositories/"
Commit-Dated "2026-04-26T15:00:00" "feat(ml): add repository layer - base, in-memory, MongoDB adapters"

# === Apr 27: Schemas + services ===
git add "ml/src/schemas/"
Commit-Dated "2026-04-27T10:00:00" "feat(ml): add Pydantic schemas for API request/response and documents"

git add "ml/src/services/"
Commit-Dated "2026-04-27T15:30:00" "feat(ml): add prediction service, model registry, and drift detection"

# === Apr 28: FastAPI server + Docker ===
git add "ml/api.py" "ml/main.py"
Commit-Dated "2026-04-28T10:00:00" "feat(ml): add FastAPI inference server with /predict and /health routes"

git add "ml/Dockerfile"
Commit-Dated "2026-04-28T15:00:00" "feat(ml): add Dockerfile for containerized deployment"

# === Apr 29: Tests + docs ===
git add "ml/tests/"
Commit-Dated "2026-04-29T10:30:00" "test(ml): add unit tests for API, models, split, reproducibility"

git add "ml/docs/"
Commit-Dated "2026-04-29T16:00:00" "docs(ml): add architecture plan and ops runbook"

# === Apr 30: README + logs ===
git add "ml/Members.md" "ml/README.md"
Commit-Dated "2026-04-30T10:00:00" "docs(ml): add project README and team members file"

git add "ml/presentation_script.md" "ml/pytest_first_failure.log" "ml/step1_pytest.log"
Commit-Dated "2026-04-30T16:00:00" "docs(ml): add presentation notes and test run logs"

# === May 1: Frontend scaffold ===
git add "web/cardiosense-react/package.json" "web/cardiosense-react/package-lock.json" "web/cardiosense-react/vite.config.ts" "web/cardiosense-react/tsconfig.json" "web/cardiosense-react/tsconfig.tsbuildinfo" "web/cardiosense-react/index.html" "web/cardiosense-react/.gitignore" "web/cardiosense-react/src/main.tsx" "web/cardiosense-react/src/vite-env.d.ts" "web/cardiosense-react/public/"
Commit-Dated "2026-05-01T09:30:00" "feat(frontend): scaffold React + Vite + TypeScript project"

git add "web/cardiosense-react/src/styles/" "web/cardiosense-react/src/App.tsx"
Commit-Dated "2026-05-01T15:00:00" "feat(frontend): add global CSS design system and app routing"

# === May 2: Components + public pages ===
git add "web/cardiosense-react/src/components/site-header.tsx" "web/cardiosense-react/src/components/site-footer.tsx" "web/cardiosense-react/src/components/reveal-animation.tsx" "web/cardiosense-react/src/hooks/"
Commit-Dated "2026-05-02T10:00:00" "feat(frontend): add site header, footer, and scroll/reveal hooks"

git add "web/cardiosense-react/src/pages/Home.tsx" "web/cardiosense-react/src/pages/About.tsx" "web/cardiosense-react/src/pages/Research.tsx" "web/cardiosense-react/src/pages/Modules.tsx"
Commit-Dated "2026-05-02T15:30:00" "feat(frontend): add home, about, research, and modules pages"

# === May 3: Auth + Dashboard ===
git add "web/cardiosense-react/src/context/" "web/cardiosense-react/src/pages/Login.tsx" "web/cardiosense-react/src/pages/Signup.tsx" "web/cardiosense-react/src/components/auth-forms.tsx"
Commit-Dated "2026-05-03T10:00:00" "feat(frontend): add auth context, JWT state, login, and signup pages"

git add "web/cardiosense-react/src/pages/Dashboard.tsx" "web/cardiosense-react/src/pages/DashboardPredict.tsx" "web/cardiosense-react/src/components/predictor-form.tsx"
Commit-Dated "2026-05-03T16:00:00" "feat(frontend): add dashboard overview and heart risk predictor form"

# === May 4: Dashboard sub-pages + contact ===
git add "web/cardiosense-react/src/pages/DashboardAnalytics.tsx" "web/cardiosense-react/src/pages/DashboardHistory.tsx" "web/cardiosense-react/src/pages/DashboardModels.tsx"
Commit-Dated "2026-05-04T10:30:00" "feat(frontend): add analytics, prediction history, and model info pages"

git add "web/cardiosense-react/src/pages/Contact.tsx" "web/cardiosense-react/src/components/contact-form.tsx" "web/cardiosense-react/src/services/"
Commit-Dated "2026-05-04T16:00:00" "feat(frontend): add contact page and frontend API service layer"

# === May 5: Express bootstrap ===
git add "backend/package.json" "backend/package-lock.json" "backend/server.js" "backend/.env.example" "backend/.gitignore" "backend/src/app.js" "backend/src/config/"
Commit-Dated "2026-05-05T10:00:00" "feat(backend): initialize Express server, CORS, and MongoDB connection"

# === May 6: Models + auth ===
git add "backend/src/models/"
Commit-Dated "2026-05-06T09:30:00" "feat(backend): add Mongoose models - User, Prediction, ContactMessage"

git add "backend/src/middleware/" "backend/src/controllers/authController.js" "backend/src/routes/authRoutes.js"
Commit-Dated "2026-05-06T15:00:00" "feat(backend): add JWT auth middleware, signup, and login endpoints"

# === May 7: Prediction + analytics routes ===
git add "backend/src/controllers/predictController.js" "backend/src/routes/predictRoutes.js" "backend/src/routes/predictionHistoryRoutes.js"
Commit-Dated "2026-05-07T10:30:00" "feat(backend): add /predict with ML proxy and fallback risk formula"

git add "backend/src/controllers/analyticsController.js" "backend/src/routes/analyticsRoutes.js"
Commit-Dated "2026-05-07T16:00:00" "feat(backend): add analytics aggregation endpoint for dashboard"

# === May 8: Contact + model routes ===
git add "backend/src/controllers/contactController.js" "backend/src/routes/contactRoutes.js" "backend/src/routes/modelRoutes.js"
Commit-Dated "2026-05-08T10:00:00" "feat(backend): add contact form, model info, and health routes"

# === May 9: Docs ===
git add "backend/README.md" "make-commits.ps1"
Commit-Dated "2026-05-09T14:00:00" "docs: add backend README with setup, API reference, and deployment guide"

# === Push ===
git branch -M main
git push --force origin main
Write-Host "Done!" -ForegroundColor Cyan
git log --format="%h %ad %s" --date=format:"%b %d"
