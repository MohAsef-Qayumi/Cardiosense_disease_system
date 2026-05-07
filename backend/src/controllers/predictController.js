const Prediction = require("../models/Prediction");

const ML_API_URL = process.env.ML_API_URL; // e.g. https://cardiosense-ml.onrender.com

// ── Fallback risk formula (logistic regression approximation) ──────────────────
// Used when the Python ML API is unavailable.
function computeFallback(input) {
  const age_years = input.age_days / 365;
  const bmi = input.weight / Math.pow(input.height / 100, 2);

  // Coefficients derived from cardio disease risk factors
  let score = -4.5;
  score += (age_years - 50) * 0.05;
  score += (bmi - 25) * 0.07;
  score += (input.ap_hi - 120) * 0.025;
  score += (input.ap_lo - 80) * 0.015;
  score += (input.cholesterol - 1) * 0.35;
  score += (input.gluc - 1) * 0.2;
  score += input.smoke * 0.3;
  score += input.alco * 0.15;
  score -= input.active * 0.25;

  return 1 / (1 + Math.exp(-score)); // sigmoid
}

function getConfidenceTier(prob) {
  // High confidence = clearly low or clearly high risk
  if (prob < 0.3 || prob > 0.75) return "HIGH";
  if (prob < 0.42 || prob > 0.62) return "MEDIUM";
  return "LOW";
}

// ── POST /predict ─────────────────────────────────────────────────────────────
async function predict(req, res, next) {
  const {
    id,
    age,
    gender,
    height,
    weight,
    ap_hi,
    ap_lo,
    cholesterol,
    gluc,
    smoke,
    alco,
    active,
  } = req.body;

  const input = {
    age_days: age,
    gender,
    height,
    weight,
    ap_hi,
    ap_lo,
    cholesterol,
    gluc,
    smoke,
    alco,
    active,
  };

  let prob_disease;
  let model_version = "fallback-v1";
  let source = "fallback";

  // Try the Python ML API first; fall back silently if it's unreachable
  if (ML_API_URL) {
    try {
      const mlRes = await fetch(`${ML_API_URL.replace(/\/$/, "")}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id,
          age,
          gender,
          height,
          weight,
          ap_hi,
          ap_lo,
          cholesterol,
          gluc,
          smoke,
          alco,
          active,
        }),
        signal: AbortSignal.timeout(5000),
      });

      if (mlRes.ok) {
        const mlData = await mlRes.json();
        prob_disease = mlData.result?.prob_disease;
        model_version = mlData.model_version || "ml-v1";
        source = "ml-api";
      }
    } catch {
      // ML API unreachable – fall through to local formula
    }
  }

  if (prob_disease === undefined) {
    prob_disease = computeFallback(input);
    source = "fallback";
  }

  const confidence_tier = getConfidenceTier(prob_disease);

  // Persist to MongoDB (non-blocking – failure doesn't affect the response)
  Prediction.create({
    user: req.user?._id || null,
    input,
    result: { prob_disease, confidence_tier, model_version },
    source,
  }).catch(() => {});

  res.json({
    result: { prob_disease, confidence_tier, model_version },
    model_version,
  });
}

// ── POST /predictions ─────────────────────────────────────────────────────────
async function savePrediction(req, res, next) {
  try {
    const prediction = await Prediction.create({
      user: req.user._id,
      ...req.body,
    });
    res.status(201).json(prediction);
  } catch (err) {
    next(err);
  }
}

// ── GET /predictions/history ──────────────────────────────────────────────────
async function getHistory(req, res, next) {
  try {
    const history = await Prediction.find({ user: req.user._id })
      .sort({ createdAt: -1 })
      .limit(100)
      .lean();
    res.json(history);
  } catch (err) {
    next(err);
  }
}

module.exports = { predict, savePrediction, getHistory };
