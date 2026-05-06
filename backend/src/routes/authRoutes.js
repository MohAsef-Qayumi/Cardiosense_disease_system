const express = require("express");
const { body } = require("express-validator");
const { signup, login } = require("../controllers/authController");

const router = express.Router();

// POST /auth/signup
router.post(
  "/signup",
  [
    body("full_name").trim().notEmpty().withMessage("Full name is required"),
    body("email")
      .isEmail()
      .normalizeEmail()
      .withMessage("Valid email is required"),
    body("password")
      .isLength({ min: 8 })
      .withMessage("Password must be at least 8 characters"),
    body("role")
      .optional()
      .isIn(["student", "patient", "clinical"])
      .withMessage("Invalid role"),
  ],
  signup,
);

// POST /auth/login
router.post(
  "/login",
  [
    body("email")
      .isEmail()
      .normalizeEmail()
      .withMessage("Valid email is required"),
    body("password").notEmpty().withMessage("Password is required"),
  ],
  login,
);

module.exports = router;
