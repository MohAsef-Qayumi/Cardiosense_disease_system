const express = require("express");
const { getSummary } = require("../controllers/analyticsController");

const router = express.Router();

// GET /analytics/summary?bucket=day
router.get("/summary", getSummary);

module.exports = router;
