const mongoose = require("mongoose");

const predictionSchema = new mongoose.Schema(
  {
    // null for guest/unauthenticated predictions
    user: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      default: null,
    },
    input: {
      age_days: Number,
      gender: Number,
      height: Number,
      weight: Number,
      ap_hi: Number,
      ap_lo: Number,
      cholesterol: Number,
      gluc: Number,
      smoke: Number,
      alco: Number,
      active: Number,
    },
    result: {
      prob_disease: {
        type: Number,
        required: true,
        min: 0,
        max: 1,
      },
      confidence_tier: {
        type: String,
        enum: ["HIGH", "MEDIUM", "LOW"],
      },
      model_version: String,
    },
    source: {
      type: String,
      default: "express",
    },
  },
  { timestamps: true },
);

// Index for efficient analytics aggregation
predictionSchema.index({ createdAt: -1 });
predictionSchema.index({ user: 1, createdAt: -1 });

module.exports = mongoose.model("Prediction", predictionSchema);
