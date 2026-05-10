const express = require("express");
const cors = require("cors");
const morgan = require("morgan");

const authRoutes = require("./routes/authRoutes");
const predictRoutes = require("./routes/predictRoutes");
const predictionHistoryRoutes = require("./routes/predictionHistoryRoutes");
const analyticsRoutes = require("./routes/analyticsRoutes");
const modelRoutes = require("./routes/modelRoutes");
const contactRoutes = require("./routes/contactRoutes");
const errorHandler = require("./middleware/errorHandler");

const app = express();

// ── CORS ──────────────────────────────────────────────────────────────────────
const allowedOrigins = [
  process.env.FRONTEND_URL,
  "https://cardiosense-disease-system.vercel.app",
  "http://localhost:5173",
  "http://localhost:3000",
].filter(Boolean);

app.use(
  cors({
    origin: (origin, callback) => {
      if (!origin || allowedOrigins.includes(origin)) {
        callback(null, true);
      } else {
        callback(null, false);
      }
    },
    credentials: true,
  }),
);

// ── BODY + LOGGING ────────────────────────────────────────────────────────────
app.use(express.json({ limit: "10kb" }));
app.use(morgan(process.env.NODE_ENV === "production" ? "combined" : "dev"));

// ── HEALTH CHECK ──────────────────────────────────────────────────────────────
app.get("/health", (req, res) => {
  res.json({ status: "ok", active_model_version: "express-v1.0" });
});

// ── ROUTES ────────────────────────────────────────────────────────────────────
app.use("/auth", authRoutes);
app.use("/predict", predictRoutes);
app.use("/predictions", predictionHistoryRoutes);
app.use("/analytics", analyticsRoutes);
app.use("/models", modelRoutes);
app.use("/contact", contactRoutes);

// ── 404 ───────────────────────────────────────────────────────────────────────
app.use((req, res) => {
  res.status(404).json({ detail: "Route not found" });
});

// ── CENTRAL ERROR HANDLER ─────────────────────────────────────────────────────
app.use(errorHandler);

module.exports = app;
