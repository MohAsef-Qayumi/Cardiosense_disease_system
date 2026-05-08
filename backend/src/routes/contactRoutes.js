const express = require("express");
const { body } = require("express-validator");
const { submitContact } = require("../controllers/contactController");

const router = express.Router();

// POST /contact
router.post(
  "/",
  [
    body("firstName").trim().notEmpty().withMessage("First name is required"),
    body("lastName").trim().notEmpty().withMessage("Last name is required"),
    body("email")
      .isEmail()
      .normalizeEmail()
      .withMessage("Valid email is required"),
    body("topic").trim().notEmpty().withMessage("Topic is required"),
    body("message").optional().trim(),
  ],
  submitContact,
);

module.exports = router;
