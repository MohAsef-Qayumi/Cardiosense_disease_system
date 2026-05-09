# CardioSense — Express Backend

Node.js / Express REST API for the CardioSense MERN stack project.  
Handles user authentication (JWT), cardiovascular risk predictions, analytics aggregation, and contact messages — all persisted in **MongoDB Atlas**.

---

## Tech Stack

| Layer      | Technology                      |
| ---------- | ------------------------------- |
| Runtime    | Node.js 18+                     |
| Framework  | Express 4                       |
| Database   | MongoDB Atlas via Mongoose 8    |
| Auth       | JSON Web Tokens (jsonwebtoken)  |
| Passwords  | bcryptjs (salted hash, cost 12) |
| Validation | express-validator               |
| Logging    | morgan                          |
| Dev server | nodemon                         |

---

## Project Structure

```
backend/
├── server.js                     ← Entry point (loads .env, connects DB, starts server)
├── src/
│   ├── app.js                    ← Express app, middleware, route mounting
│   ├── config/
│   │   └── db.js                 ← Mongoose connection helper
│   ├── models/
│   │   ├── User.js               ← User schema (email unique, hashed password, role)
│   │   ├── Prediction.js         ← Prediction schema (input, result, user ref)
│   │   └── ContactMessage.js     ← Contact form submissions
│   ├── middleware/
│   │   ├── authMiddleware.js     ← requireAuth / optionalAuth (JWT verify)
│   │   └── errorHandler.js       ← Central error → JSON response
│   ├── controllers/
│   │   ├── authController.js     ← signup, login
│   │   ├── predictController.js  ← predict (proxy + fallback), history
│   │   ├── analyticsController.js← MongoDB aggregation for dashboard
│   │   └── contactController.js  ← Save contact messages
│   └── routes/
│       ├── authRoutes.js
│       ├── predictRoutes.js
│       ├── predictionHistoryRoutes.js
│       ├── analyticsRoutes.js
│       ├── modelRoutes.js
│       └── contactRoutes.js
├── .env.example                  ← Copy this to .env and fill in your values
├── .gitignore
└── package.json
```

---

## API Endpoints

### Authentication

| Method | Endpoint       | Auth | Description                     |
| ------ | -------------- | ---- | ------------------------------- |
| POST   | `/auth/signup` | —    | Register a new user             |
| POST   | `/auth/login`  | —    | Login, returns JWT access token |

**Signup body:**

```json
{
  "full_name": "John Doe",
  "email": "j@example.com",
  "password": "secret123",
  "role": "student"
}
```

**Response (both):**

```json
{
  "access_token": "<jwt>",
  "user": { "email": "...", "full_name": "...", "role": "..." }
}
```

---

### Prediction

| Method | Endpoint               | Auth     | Description                        |
| ------ | ---------------------- | -------- | ---------------------------------- |
| POST   | `/predict`             | optional | Run risk prediction, saves to DB   |
| GET    | `/predictions/history` | required | Get current user's prediction list |
| POST   | `/predictions`         | required | Manually save a prediction record  |

**Predict body:**

```json
{
  "id": 1,
  "age": 18980,
  "gender": 2,
  "height": 172,
  "weight": 82,
  "ap_hi": 140,
  "ap_lo": 90,
  "cholesterol": 2,
  "gluc": 1,
  "smoke": 0,
  "alco": 0,
  "active": 1
}
```

**Response:**

```json
{
  "result": {
    "prob_disease": 0.62,
    "confidence_tier": "HIGH",
    "model_version": "fallback-v1"
  },
  "model_version": "fallback-v1"
}
```

> The `/predict` endpoint first tries to proxy to the Python ML API (`ML_API_URL` env var).  
> If that is unreachable or not configured, it silently falls back to a built-in logistic formula.

---

### Analytics

| Method | Endpoint                        | Auth | Description                           |
| ------ | ------------------------------- | ---- | ------------------------------------- |
| GET    | `/analytics/summary?bucket=day` | —    | Aggregated prediction stats (per day) |

**Response:**

```json
{
  "groups": [
    {
      "date_bucket": "2026-05-10",
      "confidence_tier": "HIGH",
      "model_version": "fallback-v1",
      "total_predictions": 12,
      "positive_predictions": 7,
      "negative_predictions": 5,
      "average_probability": 0.63,
      "average_confidence_score": 0.63
    }
  ]
}
```

---

### Model Info & Health

| Method | Endpoint         | Auth | Description                |
| ------ | ---------------- | ---- | -------------------------- |
| GET    | `/health`        | —    | API liveness check         |
| GET    | `/models/active` | —    | Active model configuration |

---

### Contact

| Method | Endpoint   | Auth | Description               |
| ------ | ---------- | ---- | ------------------------- |
| POST   | `/contact` | —    | Save contact form message |

**Body:** `{ "firstName", "lastName", "email", "topic", "message" }`

---

## Local Setup

### 1. Prerequisites

- Node.js 18+ installed
- A free [MongoDB Atlas](https://www.mongodb.com/atlas) account

### 2. MongoDB Atlas Setup

1. Log in to MongoDB Atlas → **Create a free cluster** (M0 free tier)
2. Under **Database Access** → Add a database user with a username and password
3. Under **Network Access** → Add IP address `0.0.0.0/0` (allow all, for dev)
4. Click **Connect** on your cluster → **Drivers** → copy the connection string  
   It looks like: `mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/`

### 3. Environment Variables

```bash
# In the backend/ folder:
cp .env.example .env
```

Edit `.env`:

```
PORT=5000
NODE_ENV=development
MONGODB_URI=mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/cardiosense?retryWrites=true&w=majority
JWT_SECRET=paste-a-long-random-string-here
```

Generate a secure JWT secret:

```bash
node -e "console.log(require('crypto').randomBytes(64).toString('hex'))"
```

### 4. Install & Run

```bash
cd backend
npm install
npm run dev        # development (nodemon, auto-restarts)
# or
npm start          # production
```

Server starts at `http://localhost:5000`

### 5. Frontend connection

In `web/cardiosense-react/.env.local`:

```
VITE_API_BASE_URL=http://localhost:5000
```

---

## How It Works

### Authentication Flow

```
Client ──POST /auth/signup──► authController.signup
                               ├── Validate input (express-validator)
                               ├── Check duplicate email
                               ├── Hash password (bcrypt, cost 12)
                               ├── Save User to MongoDB
                               └── Return JWT (7 day) + user object

Client ──POST /auth/login───► authController.login
                               ├── Find user by email
                               ├── Compare password hash
                               └── Return JWT + user object
```

### Prediction Flow

```
Client ──POST /predict──► optionalAuth middleware (attaches req.user if token present)
                          └── predictController.predict
                               ├── Try proxy to ML_API_URL/predict (5s timeout)
                               │   ├── Success → use ML probability
                               │   └── Fail (unreachable) → use fallback formula
                               ├── Compute confidence tier (HIGH / MEDIUM / LOW)
                               ├── Save Prediction to MongoDB (async, non-blocking)
                               └── Return { result, model_version }
```

### Fallback Risk Formula

When the Python ML API is unavailable, a logistic regression approximation runs locally:

- Factors: age, BMI, systolic/diastolic BP, cholesterol, glucose, smoking, alcohol, activity
- Output: probability 0–1 via sigmoid function
- Confidence: HIGH if prob < 0.30 or > 0.75, MEDIUM if near-boundary, LOW if ambiguous

### Analytics Aggregation

`GET /analytics/summary` runs a MongoDB aggregation pipeline on the `Prediction` collection:

- Groups by: date (day), confidence tier, model version
- Computes: counts (total, positive, negative), average probability
- Used by the React dashboard for charts and statistics

### MVC Pattern

- **Models** (`src/models/`) — Mongoose schemas, data shape, pre-save hooks
- **Controllers** (`src/controllers/`) — Business logic, DB queries
- **Routes** (`src/routes/`) — URL mapping, validation, middleware chaining
- **Middleware** — Cross-cutting concerns: auth, error handling, CORS, logging

---

## Deployment (Render — Free Tier)

1. Push this folder to a GitHub repository (see below)
2. Go to [render.com](https://render.com) → **New Web Service**
3. Connect your GitHub repo
4. Settings:
   - **Root Directory:** _(leave blank if backend is its own repo, or set to `backend/` if monorepo)_
   - **Build Command:** `npm install`
   - **Start Command:** `node server.js`
   - **Environment:** Node
5. Under **Environment Variables**, add:
   ```
   MONGODB_URI=your-atlas-uri
   JWT_SECRET=your-secret
   FRONTEND_URL=https://your-app.vercel.app
   NODE_ENV=production
   ```
6. Deploy — Render gives you a URL like `https://cardiosense-backend.onrender.com`
7. Update your Vercel frontend env var: `VITE_API_BASE_URL=https://cardiosense-backend.onrender.com`

---

## Security Notes

- Passwords are never stored in plaintext — bcrypt hash with cost factor 12
- JWT tokens expire after 7 days
- Input is validated at every boundary with express-validator
- CORS is restricted to allowed origins only
- `Content-Type: application/json` body size limited to 10kb
