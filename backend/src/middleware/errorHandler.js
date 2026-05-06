/**
 * Central error handler – must be registered last in app.js.
 * Converts any thrown error into a consistent JSON response.
 */
function errorHandler(err, req, res, _next) {
  // Mongoose duplicate key (e.g. duplicate email on signup)
  if (err.code === 11000) {
    const field = Object.keys(err.keyValue || {})[0] || "field";
    return res.status(409).json({ detail: `${field} is already in use.` });
  }

  // Mongoose validation errors
  if (err.name === "ValidationError") {
    const msg = Object.values(err.errors)[0]?.message || "Validation error";
    return res.status(400).json({ detail: msg });
  }

  const status = err.status || err.statusCode || 500;
  const message = err.message || "Internal server error";

  if (process.env.NODE_ENV !== "production") {
    console.error("[Error]", err);
  }

  res.status(status).json({ detail: message });
}

module.exports = errorHandler;
