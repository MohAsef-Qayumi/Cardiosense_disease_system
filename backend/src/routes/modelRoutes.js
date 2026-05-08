const express = require("express");

const router = express.Router();

// GET /models/active
// Returns static model info (update if you store model registry in MongoDB later)
router.get("/active", (req, res) => {
  res.json({
    model_name: "CardioSense Ensemble",
    model_version: process.env.ML_API_URL ? "ml-proxy-v1" : "fallback-v1",
    threshold_used: 0.4185,
    calibration: "Sigmoid",
    source: process.env.ML_API_URL ? "ml-api" : "fallback",
  });
});

module.exports = router;
