const express = require("express");
const { requireAuth } = require("../middleware/authMiddleware");
const {
  savePrediction,
  getHistory,
} = require("../controllers/predictController");

const router = express.Router();

// GET /predictions/history
router.get("/history", requireAuth, getHistory);

// POST /predictions
router.post("/", requireAuth, savePrediction);

module.exports = router;
