const Prediction = require("../models/Prediction");

const ML_API_URL = process.env.ML_API_URL;

function getConfidenceTier(prob) {
  if (prob < 0.3 || prob > 0.75) return "HIGH";
  if (prob < 0.42 || prob > 0.62) return "MEDIUM";
  return "LOW";
}

// ── POST /predict ─────────────────────────────────────────────────────────────
async function predict(req, res, next) {
  if (!ML_API_URL) {
    return res.status(503).json({ detail: "ML API is not configured." });
  }

  const { id, age, gender, height, weight, ap_hi, ap_lo, cholesterol, gluc, smoke, alco, active } = req.body;

  const input = { age_days: age, gender, height, weight, ap_hi, ap_lo, cholesterol, gluc, smoke, alco, active };

  try {
    const mlRes = await fetch(`${ML_API_URL.replace(/\/$/, "")}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, age, gender, height, weight, ap_hi, ap_lo, cholesterol, gluc, smoke, alco, active }),
      signal: AbortSignal.timeout(10000),
    });

    if (!mlRes.ok) {
      const err = await mlRes.text();
      return res.status(502).json({ detail: `ML API error: ${err}` });
    }

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
  } catch (err) {
    return res.status(503).json({ detail: "ML API is unreachable. Please try again later." });
  }
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
