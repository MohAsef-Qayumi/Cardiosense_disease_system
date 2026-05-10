import { useEffect, useState } from "react";
import {
  loadModelMetrics,
  formatPercent,
  formatNumber,
  EnsembleMetrics,
} from "@/services/metrics";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

interface AnalyticsGroup {
  model_version: string;
  date_bucket: string;
  confidence_tier: string;
  total_predictions: number;
  positive_predictions: number;
  negative_predictions: number;
  average_confidence_score: number;
  average_probability: number;
}

interface AnalyticsSummary {
  groups: AnalyticsGroup[];
  total: number;
  positive: number;
  avgRiskPct: number;
  detectionRate: number;
  highConfidencePct: number;
  mediumConfidencePct: number;
  lowConfidencePct: number;
  byDay: { date: string; positive: number; negative: number; total: number }[];
}

async function fetchAnalyticsSummary(): Promise<AnalyticsSummary> {
  const res = await fetch(`${API_BASE}/analytics/summary?bucket=day`, {
    signal: AbortSignal.timeout(4000),
  });
  if (!res.ok) throw new Error("analytics fetch failed");
  const data = await res.json();
  const groups: AnalyticsGroup[] = data.groups || [];

  const total = groups.reduce((s, g) => s + g.total_predictions, 0);
  const positive = groups.reduce((s, g) => s + g.positive_predictions, 0);
  const probSum = groups.reduce(
    (s, g) => s + g.average_probability * g.total_predictions,
    0,
  );
  const avgRiskPct = total > 0 ? (probSum / total) * 100 : 0;
  const detectionRate = total > 0 ? (positive / total) * 100 : 0;

  const highTotal = groups
    .filter((g) => g.confidence_tier === "HIGH")
    .reduce((s, g) => s + g.total_predictions, 0);
  const medTotal = groups
    .filter((g) => g.confidence_tier === "MEDIUM")
    .reduce((s, g) => s + g.total_predictions, 0);
  const lowTotal = groups
    .filter((g) => g.confidence_tier === "LOW")
    .reduce((s, g) => s + g.total_predictions, 0);

  const highConfidencePct = total > 0 ? (highTotal / total) * 100 : 0;
  const mediumConfidencePct = total > 0 ? (medTotal / total) * 100 : 0;
  const lowConfidencePct = total > 0 ? (lowTotal / total) * 100 : 0;

  // Build per-day aggregates
  const dayMap: Record<string, { positive: number; negative: number }> = {};
  for (const g of groups) {
    if (!dayMap[g.date_bucket])
      dayMap[g.date_bucket] = { positive: 0, negative: 0 };
    dayMap[g.date_bucket].positive += g.positive_predictions;
    dayMap[g.date_bucket].negative += g.negative_predictions;
  }
  const byDay = Object.entries(dayMap)
    .sort(([a], [b]) => b.localeCompare(a))
    .slice(0, 7)
    .reverse()
    .map(([date, v]) => ({ date, ...v, total: v.positive + v.negative }));

  return {
    groups,
    total,
    positive,
    avgRiskPct,
    detectionRate,
    highConfidencePct,
    mediumConfidencePct,
    lowConfidencePct,
    byDay,
  };
}

export default function DashboardAnalytics() {
  const [metrics, setMetrics] = useState<EnsembleMetrics | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      loadModelMetrics(),
      fetchAnalyticsSummary().catch(() => null),
    ])
      .then(([m, a]) => {
        setMetrics(m);
        setAnalytics(a);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);
  
  useEffect(() => {
    if (loading) return;
    const id = setTimeout(() => {
      document
        .querySelectorAll("[data-reveal]:not(.is-visible)")
        .forEach((el) => el.classList.add("is-visible"));
    }, 50);
    return () => clearTimeout(id);
  }, [loading]);

  if (loading) {
    return <div className="p-4 text-muted">Loading analytics data...</div>;
  }

  if (!metrics || metrics.models.length === 0) {
    return <div className="p-4 text-muted">Unable to load model metrics.</div>;
  }

  const bestModel = metrics.models.reduce((best, m) =>
    m.metrics.accuracy > best.metrics.accuracy ? m : best,
  );

  const total = analytics?.total ?? 0;
  const avgRiskPct = analytics?.avgRiskPct ?? 0;
  const detectionRate = analytics?.detectionRate ?? 0;
  const highConfidencePct = analytics?.highConfidencePct ?? 0;
  const mediumConfidencePct = analytics?.mediumConfidencePct ?? 0;
  const lowConfidencePct = analytics?.lowConfidencePct ?? 0;
  const byDay = analytics?.byDay ?? [];
  const maxDayCount =
    byDay.length > 0 ? Math.max(...byDay.map((d) => d.total)) : 1;

  return (
    <>
      <div className="dashboard-header" data-reveal>
        <h1>Analytics Dashboard</h1>
        <p className="text-muted">
          Real-time insights from your heart disease prediction system.
        </p>
      </div>

      {/* Key Metrics Strip */}
      <div className="dashboard-stats-grid">
        {[
          {
            icon: "bi-calculator",
            label: "Total Predictions",
            value: total.toLocaleString(),
            color: "var(--primary)",
          },
          {
            icon: "bi-activity",
            label: "Avg Risk Score",
            value: `${avgRiskPct.toFixed(1)}%`,
            color: "var(--teal)",
          },
          {
            icon: "bi-graph-up",
            label: "Detection Rate",
            value: `${detectionRate.toFixed(1)}%`,
            color: "var(--amber)",
          },
          {
            icon: "bi-check-circle",
            label: "High Confidence",
            value: `${highConfidencePct.toFixed(1)}%`,
            color: "#7c4dff",
          },
        ].map((stat, idx) => (
          <div
            key={idx}
            className="dashboard-stat-card"
            data-reveal
            style={{ borderLeft: `4px solid ${stat.color}` }}
          >
            <div className="d-flex justify-content-between align-items-start">
              <div>
                <div className="stat-label text-muted">{stat.label}</div>
                <div className="stat-value" style={{ fontSize: "1.8rem" }}>
                  {stat.value}
                </div>
                <span className="text-muted" style={{ fontSize: "0.75rem" }}>
                  {total > 0 ? "Live from backend" : "No data yet"}
                </span>
              </div>
              <div
                className="stat-icon"
                style={{ opacity: 0.12, fontSize: "1.8rem", color: stat.color }}
              >
                <i className={`bi ${stat.icon}`}></i>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="dashboard-content-grid">
        {/* Prediction Trends Bar Chart */}
        <div className="dashboard-panel" data-reveal>
          <div className="d-flex justify-content-between align-items-center mb-4">
            <h3 className="m-0">
              <i className="bi bi-bar-chart-line text-muted"></i> Prediction
              Trends (Last 7 Days)
            </h3>
          </div>

          {byDay.length === 0 ? (
            <div className="text-center text-muted py-4">
              <i
                className="bi bi-bar-chart"
                style={{ fontSize: "2.5rem", opacity: 0.3 }}
              ></i>
              <p className="mt-2" style={{ fontSize: "0.9rem" }}>
                No prediction activity yet.
              </p>
            </div>
          ) : (
            <>
              <div
                style={{
                  height: "220px",
                  display: "flex",
                  alignItems: "flex-end",
                  gap: "12px",
                  padding: "10px 0",
                }}
              >
                {byDay.map((day, idx) => (
                  <div
                    key={idx}
                    style={{
                      flex: 1,
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    <div
                      style={{
                        width: "100%",
                        display: "flex",
                        gap: "2px",
                        alignItems: "flex-end",
                        height: "160px",
                      }}
                    >
                      <div
                        style={{
                          flex: 1,
                          background:
                            "linear-gradient(180deg, var(--primary), #ff6b7a)",
                          borderRadius: "4px 4px 0 0",
                          height: `${(day.positive / maxDayCount) * 160}px`,
                          minHeight: day.positive > 0 ? "4px" : "0",
                        }}
                      />
                      <div
                        style={{
                          flex: 1,
                          background:
                            "linear-gradient(180deg, var(--teal), #3dd9c9)",
                          borderRadius: "4px 4px 0 0",
                          height: `${(day.negative / maxDayCount) * 160}px`,
                          minHeight: day.negative > 0 ? "4px" : "0",
                        }}
                      />
                    </div>
                    <span
                      style={{
                        fontSize: "0.7rem",
                        color: "var(--ink-muted)",
                        fontWeight: 500,
                      }}
                    >
                      {day.date.slice(5)}
                    </span>
                  </div>
                ))}
              </div>
              <div className="d-flex justify-content-center gap-4 mt-3">
                <div className="d-flex align-items-center gap-2">
                  <div
                    style={{
                      width: "12px",
                      height: "12px",
                      background:
                        "linear-gradient(135deg, var(--primary), #ff6b7a)",
                      borderRadius: "2px",
                    }}
                  ></div>
                  <span style={{ fontSize: "0.85rem" }}>Positive</span>
                </div>
                <div className="d-flex align-items-center gap-2">
                  <div
                    style={{
                      width: "12px",
                      height: "12px",
                      background:
                        "linear-gradient(135deg, var(--teal), #3dd9c9)",
                      borderRadius: "2px",
                    }}
                  ></div>
                  <span style={{ fontSize: "0.85rem" }}>Negative</span>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Confidence Distribution */}
        <div className="dashboard-panel" data-reveal>
          <h3 className="mb-4">
            <i className="bi bi-pie-chart text-muted"></i> Confidence
            Distribution
          </h3>
          {total === 0 ? (
            <div className="text-center text-muted py-4">
              <i
                className="bi bi-pie-chart"
                style={{ fontSize: "2.5rem", opacity: 0.3 }}
              ></i>
              <p className="mt-2" style={{ fontSize: "0.9rem" }}>
                No data yet.
              </p>
            </div>
          ) : (
            <>
              <div className="d-flex align-items-center justify-content-center gap-4">
                <div
                  className="position-relative"
                  style={{ width: "150px", height: "150px" }}
                >
                  <svg
                    viewBox="0 0 100 100"
                    style={{ transform: "rotate(-90deg)" }}
                  >
                    <circle
                      cx="50"
                      cy="50"
                      r="40"
                      fill="none"
                      stroke="#e8eaf6"
                      strokeWidth="12"
                    />
                    <circle
                      cx="50"
                      cy="50"
                      r="40"
                      fill="none"
                      stroke="#7c4dff"
                      strokeWidth="12"
                      strokeDasharray={`${(highConfidencePct / 100) * 251.2} ${251.2}`}
                      strokeLinecap="round"
                    />
                    <circle
                      cx="50"
                      cy="50"
                      r="40"
                      fill="none"
                      stroke="#ff9800"
                      strokeWidth="12"
                      strokeDasharray={`${(mediumConfidencePct / 100) * 251.2} ${251.2}`}
                      strokeDashoffset={`-${(highConfidencePct / 100) * 251.2}`}
                      strokeLinecap="round"
                    />
                  </svg>
                  <div className="position-absolute top-50 start-50 translate-middle text-center">
                    <div
                      style={{
                        fontSize: "1.4rem",
                        fontWeight: 700,
                        color: "var(--ink)",
                      }}
                    >
                      {total}
                    </div>
                    <div
                      style={{ fontSize: "0.7rem", color: "var(--ink-muted)" }}
                    >
                      Total
                    </div>
                  </div>
                </div>
              </div>
              <div className="d-flex flex-column gap-2 mt-3">
                {[
                  {
                    label: "High Confidence",
                    value: highConfidencePct,
                    color: "#7c4dff",
                  },
                  {
                    label: "Medium Confidence",
                    value: mediumConfidencePct,
                    color: "#ff9800",
                  },
                  {
                    label: "Low Confidence",
                    value: lowConfidencePct,
                    color: "#00bcd4",
                  },
                ].map((item, idx) => (
                  <div key={idx} className="d-flex align-items-center gap-2">
                    <span
                      style={{
                        width: "10px",
                        height: "10px",
                        background: item.color,
                        borderRadius: "2px",
                        display: "inline-block",
                      }}
                    ></span>
                    <span style={{ fontSize: "0.85rem" }}>{item.label}</span>
                    <strong style={{ fontSize: "0.85rem", marginLeft: "auto" }}>
                      {item.value.toFixed(1)}%
                    </strong>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Model Comparison Table */}
      <div className="dashboard-panel mt-4" data-reveal>
        <div className="d-flex justify-content-between align-items-center mb-4">
          <h3 className="m-0">
            <i className="bi bi-diagram-3 text-muted"></i> Model Performance
            Comparison
          </h3>
          <span
            className="badge"
            style={{ background: "var(--bg-soft)", color: "var(--ink)" }}
          >
            {metrics!.models.length} Models Trained
          </span>
        </div>
        <div className="table-responsive">
          <table className="table" style={{ fontSize: "0.9rem" }}>
            <thead>
              <tr>
                <th>Model</th>
                <th>Accuracy</th>
                <th>ROC-AUC</th>
                <th>Precision</th>
                <th>Recall</th>
                <th>F1-Score</th>
                <th>Visual</th>
              </tr>
            </thead>
            <tbody>
              {metrics!.models.map((model, idx) => {
                const isBest = model.name === bestModel.name;
                return (
                  <tr
                    key={idx}
                    style={{
                      background: isBest
                        ? "rgba(124, 77, 255, 0.04)"
                        : "transparent",
                    }}
                  >
                    <td>
                      <div className="d-flex align-items-center gap-2">
                        {isBest && (
                          <i
                            className="bi bi-trophy-fill text-warning"
                            style={{ fontSize: "0.8rem" }}
                          ></i>
                        )}
                        <strong>{model.fullName}</strong>
                      </div>
                    </td>
                    <td>
                      <strong
                        style={{ color: isBest ? "var(--primary)" : "inherit" }}
                      >
                        {formatPercent(model.metrics.accuracy)}
                      </strong>
                    </td>
                    <td>{formatNumber(model.metrics.roc_auc, 3)}</td>
                    <td>{formatPercent(model.metrics.precision)}</td>
                    <td>{formatPercent(model.metrics.recall)}</td>
                    <td>{formatPercent(model.metrics.f1)}</td>
                    <td style={{ width: "120px" }}>
                      <div
                        className="progress"
                        style={{
                          height: "6px",
                          background: "rgba(0,0,0,0.05)",
                        }}
                      >
                        <div
                          className="progress-bar"
                          style={{
                            width: `${model.metrics.accuracy * 100}%`,
                            background: isBest
                              ? "linear-gradient(90deg, var(--primary), #ff6b7a)"
                              : "var(--bg-soft)",
                            borderRadius: "3px",
                          }}
                        />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Key Insights */}
      <div className="dashboard-panel mt-4" data-reveal>
        <h3 className="mb-4">
          <i className="bi bi-lightbulb text-warning"></i> Key Insights
        </h3>
        <div className="row g-3">
          {[
            {
              icon: "bi-trophy",
              title: "Best Model",
              desc: `${bestModel.fullName} achieves ${formatPercent(bestModel.metrics.accuracy)} accuracy with recall of ${formatPercent(bestModel.metrics.recall)}.`,
              color: "#ffd700",
            },
            {
              icon: "bi-sliders",
              title: "Threshold Optimization",
              desc: `Decision threshold at ${formatNumber(metrics!.threshold, 4)} targeting ${(metrics!.config.targetRecall * 100).toFixed(0)}% recall.`,
              color: "var(--primary)",
            },
            {
              icon: "bi-check-circle",
              title: "Calibration",
              desc: `All models use ${metrics!.config.calibrationMethod} calibration (random_state=${metrics!.config.randomState}).`,
              color: "var(--teal)",
            },
            {
              icon: "bi-database",
              title: "Dataset",
              desc: `Trained on 68,000+ BRFSS 2015 samples; 13,722-sample test holdout with 11 clinical features.`,
              color: "var(--amber)",
            },
          ].map((insight, idx) => (
            <div key={idx} className="col-md-6">
              <div
                className="d-flex gap-3 p-3 rounded"
                style={{ background: "var(--bg-soft)", height: "100%" }}
              >
                <div className="flex-shrink-0">
                  <div
                    className="d-flex align-items-center justify-content-center rounded-circle"
                    style={{
                      width: "44px",
                      height: "44px",
                      background: `${insight.color}20`,
                      color: insight.color,
                    }}
                  >
                    <i
                      className={`bi ${insight.icon}`}
                      style={{ fontSize: "1.2rem" }}
                    ></i>
                  </div>
                </div>
                <div>
                  <h5 style={{ fontSize: "0.95rem", marginBottom: "4px" }}>
                    {insight.title}
                  </h5>
                  <p
                    className="text-muted m-0"
                    style={{ fontSize: "0.85rem", lineHeight: 1.5 }}
                  >
                    {insight.desc}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
