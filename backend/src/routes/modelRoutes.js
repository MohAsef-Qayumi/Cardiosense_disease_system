const express = require("express");

const router = express.Router();

// GET /models/active
router.get("/active", (req, res) => {
  res.json({
    model_name: "CardioSense Ensemble",
    model_version: process.env.ML_API_URL ? "ml-proxy-v1" : "fallback-v1",
    threshold_used: 0.4185,
    calibration: "Sigmoid",
    source: process.env.ML_API_URL ? "ml-api" : "fallback",
  });
});

// GET /models/metrics
// Returns ensemble model metrics for the dashboard models page
router.get("/metrics", (req, res) => {
  res.json({
    selected_model: "Stacking",
    selected_threshold: 0.4185,
    config: {
      calibration_method: "sigmoid",
      random_state: 42,
      target_recall: 0.83,
      target_accuracy: 0.78,
    },
    models: [
      {
        name: "XGBoost",
        full_name: "XGBoost Calibrated",
        accuracy: 0.7312,
        roc_auc: 0.8025,
        precision: 0.7203,
        recall: 0.7468,
        f1: 0.7333,
        threshold: 0.4281,
        is_selected: false,
      },
      {
        name: "LightGBM",
        full_name: "LightGBM Calibrated",
        accuracy: 0.7338,
        roc_auc: 0.8042,
        precision: 0.7228,
        recall: 0.7512,
        f1: 0.7367,
        threshold: 0.4412,
        is_selected: false,
      },
      {
        name: "Random Forest",
        full_name: "Random Forest Calibrated",
        accuracy: 0.7198,
        roc_auc: 0.7921,
        precision: 0.7089,
        recall: 0.7341,
        f1: 0.7213,
        threshold: 0.4550,
        is_selected: false,
      },
      {
        name: "Soft Voting",
        full_name: "Soft Voting Ensemble",
        accuracy: 0.7361,
        roc_auc: 0.8071,
        precision: 0.7245,
        recall: 0.7538,
        f1: 0.7389,
        threshold: 0.4298,
        is_selected: false,
      },
      {
        name: "Stacking",
        full_name: "Stacking Ensemble",
        accuracy: 0.7340,
        roc_auc: 0.8040,
        precision: 0.7230,
        recall: 0.7510,
        f1: 0.7367,
        threshold: 0.4185,
        is_selected: true,
      },
    ],
  });
});

module.exports = router;
