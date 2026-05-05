require("dotenv").config();
const app = require("./src/app");
const connectDB = require("./src/config/db");

const PORT = process.env.PORT || 5000;

connectDB()
  .then(() => {
    app.listen(PORT, () => {
      console.log(`CardioSense backend running on port ${PORT}`);
      console.log(`Environment: ${process.env.NODE_ENV || "development"}`);
      if (process.env.ML_API_URL) {
        console.log(`ML API proxy: ${process.env.ML_API_URL}`);
      } else {
        console.log("ML API: not configured – fallback formula active");
      }
    });
  })
  .catch((err) => {
    console.error("Failed to start server:", err.message);
    process.exit(1);
  });
