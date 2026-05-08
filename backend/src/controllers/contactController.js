const { validationResult } = require("express-validator");
const ContactMessage = require("../models/ContactMessage");

// ── POST /contact ─────────────────────────────────────────────────────────────
async function submitContact(req, res, next) {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({ detail: errors.array()[0].msg });
  }

  const { firstName, lastName, email, topic, message } = req.body;

  try {
    await ContactMessage.create({ firstName, lastName, email, topic, message });
    res.status(201).json({
      success: true,
      message: "Message received. Thank you for reaching out.",
    });
  } catch (err) {
    next(err);
  }
}

module.exports = { submitContact };
