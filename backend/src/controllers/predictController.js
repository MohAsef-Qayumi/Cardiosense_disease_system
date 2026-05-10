const Prediction = require("../models/Prediction");

const ML_API_URL = process.env.ML_API_URL;

function getConfidenceTier(prob) {
  if (prob < 0.3 || prob > 0.75) return "HIGH";
  if (prob < 0.42 || prob > 0.62) return "MEDIUM";
  return "LOW";
}

/**
 * Logistic-regression-style fallback when the ML API is unavailable.
 * Mirrors the formula used in the React frontend so results are consistent.
 */
function fallbackEstimate(input) {
  const ageYears = input.age_days / 365;
  const bmi = input.weight / (input.height / 100) ** 2;
  const bpRisk =
    input.ap_hi > 140 || input.ap_lo > 90 ? 1.5
    : input.ap_hi > 120 ? 0.8
    : 0;
  const score =
    0.025 * (ageYears - 40) +
    0.04 * (bmi - 22) +
    0.18 * bpRisk +
    0.12 * (input.cholesterol - 1) +
    0.08 * (input.gluc - 1) +
    0.05 * input.smoke +
    0.03 * input.alco -
    0.04 * input.active;
  const pct = Math.min(95, Math.max(5, 30 + score * 18));
  return pct / 100; // return as 0-1 probability
}

// ── POST /predict ─────────────────────────────────────────────────────────────
async function predict(req, res, next) {
  const { id, age, gender, height, weight, ap_hi, ap_lo, cholesterol, gluc, smoke, alco, active } = req.body;
  const input = { age_days: age, gender, height, weight, ap_hi, ap_lo, cholesterol, gluc, smoke, alco, active };

  // ── Try ML API first ───────────────────────────────────────────────────────
  if (ML_API_URL) {
    try {
      const mlRes = await fetch(`${ML_API_URL.replace(/\/$/, "")}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, age, gender, height, weight, ap_hi, ap_lo, cholesterol, gluc, smoke, alco, active }),
        signal: AbortSignal.timeout(10000),
      });

      if (mlRes.ok) {
        const mlData = await mlRes.json();
        const prob_disease = mlData.result?.prob_disease;
        const model_version = mlData.model_version || "ml-v1";
        const confidence_tier = getConfidenceTier(prob_disease);

        Prediction.create({
          user: req.user?._id || null,
          input,
          result: { prob_disease, confidence_tier, model_version },
          source: "ml-api",
        }).catch(() => {});

        return res.json({
          result: { prob_disease, confidence_tier, model_version },
          model_version,
        });
      }

      console.error(`ML API responded ${mlRes.status}`);
    } catch (err) {
      console.error("ML API unreachable, using fallback:", err.message);
    }
  }

  // ── Fallback: estimate locally and still persist to DB ────────────────────
  const prob_disease = fallbackEstimate(input);
  const confidence_tier = getConfidenceTier(prob_disease);
  const model_version = "fallback-v1";

  Prediction.create({
    user: req.user?._id || null,
    input,
    result: { prob_disease, confidence_tier, model_version },
    source: "fallback",
  }).catch(() => {});

  return res.json({
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
