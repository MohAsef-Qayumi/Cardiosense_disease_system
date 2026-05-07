const express = require("express");
const { optionalAuth } = require("../middleware/authMiddleware");
const { predict } = require("../controllers/predictController");

const router = express.Router();

// POST /predict
router.post("/", optionalAuth, predict);

module.exports = router;
