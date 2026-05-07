const Prediction = require("../models/Prediction");

// ── GET /analytics/summary?bucket=day ─────────────────────────────────────────
async function getSummary(req, res, next) {
  // Only 'day' bucket is used by the frontend; extend if needed
  try {
    const groups = await Prediction.aggregate([
      {
        $group: {
          _id: {
            date_bucket: {
              $dateToString: { format: "%Y-%m-%d", date: "$createdAt" },
            },
            confidence_tier: "$result.confidence_tier",
            model_version: "$result.model_version",
          },
          total_predictions: { $sum: 1 },
          positive_predictions: {
            $sum: {
              $cond: [{ $gte: ["$result.prob_disease", 0.5] }, 1, 0],
            },
          },
          negative_predictions: {
            $sum: {
              $cond: [{ $lt: ["$result.prob_disease", 0.5] }, 1, 0],
            },
          },
          average_probability: { $avg: "$result.prob_disease" },
          average_confidence_score: { $avg: "$result.prob_disease" },
        },
      },
      {
        $project: {
          _id: 0,
          date_bucket: "$_id.date_bucket",
          confidence_tier: "$_id.confidence_tier",
          model_version: "$_id.model_version",
          total_predictions: 1,
          positive_predictions: 1,
          negative_predictions: 1,
          average_probability: 1,
          average_confidence_score: 1,
        },
      },
      { $sort: { date_bucket: -1 } },
    ]);

    res.json({ groups });
  } catch (err) {
    next(err);
  }
}

module.exports = { getSummary };
