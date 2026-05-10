const jwt = require("jsonwebtoken");
const User = require("../models/User");

function extractToken(req) {
  const auth = req.headers.authorization;
  if (auth && auth.startsWith("Bearer ")) {
    return auth.slice(7);
  }
  return null;
}

/**
 * requireAuth – rejects with 401 if no valid token is present.
 * Use for routes that must be authenticated.
 */
async function requireAuth(req, res, next) {
  const token = extractToken(req);
  if (!token) {
    return res.status(401).json({ detail: "Authentication required." });
  }
  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = await User.findById(decoded.id).select("-password");
    if (!req.user) {
      return res.status(401).json({ detail: "User not found." });
    }
    next();
  } catch {
    return res.status(401).json({ detail: "Invalid or expired token." });
  }
}

async function optionalAuth(req, res, next) {
  const token = extractToken(req);
  if (token) {
    try {
      const decoded = jwt.verify(token, process.env.JWT_SECRET);
      req.user = await User.findById(decoded.id).select("-password");
    } catch {
      req.user = null;
    }
  }
  next();
}

module.exports = { requireAuth, optionalAuth };
