import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/context/auth-context";
import {
  loadModelMetrics,
  formatPercent,
  formatNumber,
  EnsembleMetrics,
} from "@/services/metrics";
import { useApiHealth, useCountUp } from "@/hooks/use-dashboard-data";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

interface AnalyticsStats {
  total: number;
  positive: number;
  avgRiskPct: number;
  highConfidencePct: number;
}

async function fetchAnalyticsStats(): Promise<AnalyticsStats> {
  const res = await fetch(`${API_BASE}/analytics/summary?bucket=day`, {
    signal: AbortSignal.timeout(4000),
  });
  if (!res.ok) throw new Error("analytics fetch failed");
  const data = await res.json();
  const groups: any[] = data.groups || [];
  if (groups.length === 0)
    return { total: 0, positive: 0, avgRiskPct: 0, highConfidencePct: 0 };

  const total = groups.reduce(
    (s: number, g: any) => s + g.total_predictions,
    0,
  );
  const positive = groups.reduce(
    (s: number, g: any) => s + g.positive_predictions,
    0,
  );
  const probSum = groups.reduce(
    (s: number, g: any) => s + g.average_probability * g.total_predictions,
    0,
  );
  const avgRiskPct = total > 0 ? (probSum / total) * 100 : 0;
  const highGroups = groups.filter((g: any) => g.confidence_tier === "HIGH");
  const highTotal = highGroups.reduce(
    (s: number, g: any) => s + g.total_predictions,
    0,
  );
  const highConfidencePct = total > 0 ? (highTotal / total) * 100 : 0;
  return { total, positive, avgRiskPct, highConfidencePct };
}

export default function Dashboard() {
  const { user } = useAuth();
  const [metrics, setMetrics] = useState<EnsembleMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const { status: apiStatus, version: apiVersion } = useApiHealth();
  const [stats, setStats] = useState<AnalyticsStats>({
    total: 0,
    positive: 0,
    avgRiskPct: 0,
    highConfidencePct: 0,
  });

  useEffect(() => {
    loadModelMetrics().then((m) => {
      setMetrics(m);
      setLoading(false);
    });
    fetchAnalyticsStats()
      .then(setStats)
      .catch(() => {});
  }, []);

  const totalPredictions = stats.total;
  const positiveCases = stats.positive;
  const avgRisk = stats.avgRiskPct;

  const animatedPredictions = useCountUp(totalPredictions, 1200);
  const animatedPositive = useCountUp(positiveCases, 1400);
  const animatedAvgRisk = useCountUp(Math.round(avgRisk), 1000);

  const bestModel = metrics?.models.reduce((best, m) =>
    m.metrics.accuracy > best.metrics.accuracy ? m : best,
  );

  const statusConfig = {
    Low: { bg: "#e8f5e9", color: "#2e7d32", label: "Low Risk" },
    Medium: { bg: "#fff3e0", color: "#ef6c00", label: "Medium Risk" },
    High: { bg: "#ffebee", color: "#c62828", label: "High Risk" },
  };

  return (
    <>
      {/* Welcome Header */}
      <div className="dashboard-header" data-reveal>
        <div className="d-flex justify-content-between align-items-start flex-wrap gap-3">
          <div>
            <h1>Welcome back, {user?.fullName || "User"}! 👋</h1>
            <p className="text-muted mt-1">
              Here's what's happening with your heart disease prediction system.
            </p>
          </div>
          <div className="d-flex gap-2">
            <span
              className={`badge ${apiStatus === "online" ? "bg-success" : apiStatus === "checking" ? "bg-warning" : "bg-danger"} d-flex align-items-center gap-1`}
            >
              <span
                className="rounded-circle"
                style={{
                  width: 8,
                  height: 8,
                  background: "#fff",
                  display: "inline-block",
                }}
              ></span>
              API {apiStatus}
            </span>
            <span className="badge bg-secondary">{apiVersion}</span>
          </div>
        </div>
      </div>

      {/* Animated Stats Cards */}
      <div className="dashboard-stats-grid">
        <div
          className="dashboard-stat-card"
          data-reveal
          style={{ borderLeft: "4px solid var(--primary)" }}
        >
          <div className="d-flex justify-content-between align-items-start">
            <div>
              <div className="stat-label text-muted">Total Predictions</div>
              <div className="stat-value" style={{ fontSize: "2.2rem" }}>
                {animatedPredictions}
              </div>
              <div
                className="text-muted"
                style={{ fontSize: "0.8rem", marginTop: "4px" }}
              >
                {totalPredictions > 0 ? (
                  <span style={{ color: "var(--teal)" }}>
                    Live from backend
                  </span>
                ) : (
                  <span>No predictions yet</span>
                )}
              </div>
            </div>
            <div
              className="stat-icon primary"
              style={{ opacity: 0.15, fontSize: "2rem" }}
            >
              <i className="bi bi-calculator"></i>
            </div>
          </div>
        </div>

        <div
          className="dashboard-stat-card"
          data-reveal
          style={{ borderLeft: "4px solid var(--amber)" }}
        >
          <div className="d-flex justify-content-between align-items-start">
            <div>
              <div className="stat-label text-muted">Positive Cases</div>
              <div className="stat-value" style={{ fontSize: "2.2rem" }}>
                {animatedPositive}
              </div>
              <div
                className="text-muted"
                style={{ fontSize: "0.8rem", marginTop: "4px" }}
              >
                <span style={{ color: "var(--amber)" }}>
                  {totalPredictions > 0
                    ? `${((positiveCases / totalPredictions) * 100).toFixed(1)}%`
                    : "0%"}
                </span>{" "}
                detection rate
              </div>
            </div>
            <div
              className="stat-icon amber"
              style={{ opacity: 0.15, fontSize: "2rem" }}
            >
              <i className="bi bi-heart-pulse"></i>
            </div>
          </div>
        </div>

        <div
          className="dashboard-stat-card"
          data-reveal
          style={{ borderLeft: "4px solid var(--teal)" }}
        >
          <div className="d-flex justify-content-between align-items-start">
            <div>
              <div className="stat-label text-muted">Average Risk Score</div>
              <div className="stat-value" style={{ fontSize: "2.2rem" }}>
                {animatedAvgRisk}%
              </div>
              <div
                className="text-muted"
                style={{ fontSize: "0.8rem", marginTop: "4px" }}
              >
                <span style={{ color: "var(--teal)" }}>
                  Across all predictions
                </span>
              </div>
            </div>
            <div
              className="stat-icon teal"
              style={{ opacity: 0.15, fontSize: "2rem" }}
            >
              <i className="bi bi-activity"></i>
            </div>
          </div>
        </div>

        <div
          className="dashboard-stat-card"
          data-reveal
          style={{ borderLeft: "4px solid #7c4dff" }}
        >
          <div className="d-flex justify-content-between align-items-start">
            <div>
              <div className="stat-label text-muted">Model Accuracy</div>
              <div className="stat-value" style={{ fontSize: "2.2rem" }}>
                {loading
                  ? "—"
                  : bestModel
                    ? (bestModel.metrics.accuracy * 100).toFixed(1) + "%"
                    : "73.4%"}
              </div>
              <div
                className="text-muted"
                style={{ fontSize: "0.8rem", marginTop: "4px" }}
              >
                <span style={{ color: "#7c4dff" }}>
                  {bestModel?.name || "Soft Voting"}
                </span>{" "}
                best model
              </div>
            </div>
            <div
              className="stat-icon"
              style={{ opacity: 0.15, fontSize: "2rem", color: "#7c4dff" }}
            >
              <i className="bi bi-cpu"></i>
            </div>
          </div>
        </div>
      </div>

      <div className="dashboard-content-grid">
        {/* Prediction Activity (from analytics API) */}
        <div className="dashboard-panel" data-reveal>
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h3 className="m-0">
              <i className="bi bi-clock-history text-muted"></i> Prediction
              Activity
            </h3>
            <Link
              to="/dashboard/analytics"
              className="btn btn-sm btn-outline-primary"
            >
              Full Analytics
            </Link>
          </div>

          {totalPredictions === 0 ? (
            <div className="text-center text-muted py-4">
              <i
                className="bi bi-inbox"
                style={{ fontSize: "2.5rem", opacity: 0.3 }}
              ></i>
              <p className="mt-2" style={{ fontSize: "0.9rem" }}>
                No predictions recorded yet. Run a prediction to see activity
                here.
              </p>
              <Link
                to="/dashboard/predict"
                className="btn btn-sm btn-primary-cs mt-1"
              >
                Make First Prediction
              </Link>
            </div>
          ) : (
            <div className="d-flex flex-column gap-2">
              <div
                className="d-flex justify-content-between p-3 rounded"
                style={{ background: "var(--bg-soft)" }}
              >
                <div>
                  <div
                    style={{ fontSize: "0.8rem", color: "var(--ink-muted)" }}
                  >
                    Total Predictions
                  </div>
                  <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>
                    {totalPredictions.toLocaleString()}
                  </div>
                </div>
                <div className="text-end">
                  <div
                    style={{ fontSize: "0.8rem", color: "var(--ink-muted)" }}
                  >
                    Positive / Negative
                  </div>
                  <div style={{ fontSize: "1rem", fontWeight: 600 }}>
                    <span style={{ color: "var(--primary)" }}>
                      {positiveCases}
                    </span>
                    <span className="text-muted mx-1">/</span>
                    <span style={{ color: "var(--teal)" }}>
                      {totalPredictions - positiveCases}
                    </span>
                  </div>
                </div>
              </div>
              <div
                className="d-flex justify-content-between p-3 rounded"
                style={{ background: "var(--bg-soft)" }}
              >
                <div>
                  <div
                    style={{ fontSize: "0.8rem", color: "var(--ink-muted)" }}
                  >
                    Avg Risk Score
                  </div>
                  <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>
                    {avgRisk.toFixed(1)}%
                  </div>
                </div>
                <div className="text-end">
                  <div
                    style={{ fontSize: "0.8rem", color: "var(--ink-muted)" }}
                  >
                    High Confidence
                  </div>
                  <div
                    style={{
                      fontSize: "1rem",
                      fontWeight: 600,
                      color: "#7c4dff",
                    }}
                  >
                    {stats.highConfidencePct.toFixed(1)}%
                  </div>
                </div>
              </div>
              <Link
                to="/dashboard/history"
                className="btn btn-sm btn-outline-secondary mt-1"
              >
                View Full History
              </Link>
            </div>
          )}
        </div>

        {/* Quick Actions + Model Performance */}
        <div className="d-flex flex-column gap-4">
          <div className="dashboard-panel" data-reveal>
            <h3 className="mb-3">
              <i className="bi bi-lightning-charge text-muted"></i> Quick
              Actions
            </h3>
            <div className="d-grid gap-2">
              <Link
                to="/dashboard/predict"
                className="btn btn-primary-cs d-flex align-items-center justify-content-center gap-2"
              >
                <i className="bi bi-activity"></i> New Prediction
              </Link>
              <Link
                to="/dashboard/models"
                className="btn btn-outline-cs d-flex align-items-center justify-content-center gap-2"
              >
                <i className="bi bi-cpu"></i> Model Information
              </Link>
              <Link
                to="/dashboard/analytics"
                className="btn btn-outline-cs d-flex align-items-center justify-content-center gap-2"
              >
                <i className="bi bi-graph-up"></i> View Analytics
              </Link>
            </div>
          </div>

          <div className="dashboard-panel" data-reveal>
            <div className="d-flex justify-content-between align-items-center mb-3">
              <h3 className="m-0">
                <i className="bi bi-trophy text-warning"></i> Best Model
              </h3>
              {bestModel && (
                <span
                  className="badge"
                  style={{
                    background: "var(--bg-soft)",
                    color: "var(--ink)",
                    fontSize: "0.8rem",
                  }}
                >
                  {bestModel.fullName}
                </span>
              )}
            </div>

            {metrics && bestModel ? (
              <div className="d-flex flex-column gap-3">
                {[
                  {
                    label: "Accuracy",
                    value: bestModel.metrics.accuracy,
                    color: "var(--primary)",
                    icon: "bi-bullseye",
                  },
                  {
                    label: "ROC-AUC",
                    value: bestModel.metrics.roc_auc,
                    color: "var(--teal)",
                    icon: "bi-graph-up-arrow",
                  },
                  {
                    label: "Recall",
                    value: bestModel.metrics.recall,
                    color: "var(--amber)",
                    icon: "bi-heart-pulse",
                  },
                  {
                    label: "F1-Score",
                    value: bestModel.metrics.f1,
                    color: "#7c4dff",
                    icon: "bi-funnel",
                  },
                ].map((metric, idx) => (
                  <div key={idx}>
                    <div className="d-flex justify-content-between align-items-center mb-1">
                      <span className="d-flex align-items-center gap-2">
                        <i
                          className={`bi ${metric.icon}`}
                          style={{ color: metric.color, fontSize: "0.85rem" }}
                        ></i>
                        {metric.label}
                      </span>
                      <strong style={{ fontSize: "0.95rem" }}>
                        {formatPercent(metric.value)}
                      </strong>
                    </div>
                    <div
                      className="progress"
                      style={{
                        height: "6px",
                        background: "rgba(0,0,0,0.05)",
                        borderRadius: "3px",
                      }}
                    >
                      <div
                        className="progress-bar"
                        style={{
                          width: `${Math.min(metric.value * 100, 100)}%`,
                          background: metric.color,
                          borderRadius: "3px",
                          transition: "width 1s ease-out",
                        }}
                      />
                    </div>
                  </div>
                ))}

                <div className="mt-2 pt-2 border-top">
                  <div
                    className="d-flex justify-content-between text-muted"
                    style={{ fontSize: "0.82rem" }}
                  >
                    <span>Threshold</span>
                    <span>{formatNumber(metrics.threshold, 4)}</span>
                  </div>
                  <div
                    className="d-flex justify-content-between text-muted"
                    style={{ fontSize: "0.82rem" }}
                  >
                    <span>Calibration</span>
                    <span>{metrics.config.calibrationMethod}</span>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-muted">Loading model metrics...</p>
            )}
          </div>
        </div>
      </div>

      {/* Model Comparison Mini-Chart */}
      {metrics && (
        <div className="dashboard-panel mt-4" data-reveal>
          <h3 className="mb-3">
            <i className="bi bi-bar-chart-line text-muted"></i> Model Accuracy
            Comparison
          </h3>
          <div
            className="d-flex align-items-end gap-3"
            style={{ height: "140px", padding: "10px 0" }}
          >
            {metrics.models.map((model, idx) => {
              const height = model.metrics.accuracy * 100;
              const isBest = model.name === bestModel?.name;
              return (
                <div
                  key={idx}
                  className="d-flex flex-column align-items-center gap-2"
                  style={{ flex: 1 }}
                >
                  <div
                    className="position-relative"
                    style={{
                      width: "100%",
                      display: "flex",
                      alignItems: "flex-end",
                      justifyContent: "center",
                    }}
                  >
                    <div
                      style={{
                        width: "50%",
                        height: `${height * 1.2}px`,
                        background: isBest
                          ? "linear-gradient(180deg, var(--primary), #ff6b7a)"
                          : "var(--bg-soft)",
                        borderRadius: "6px 6px 0 0",
                        transition: "height 1s ease-out",
                        minHeight: "20px",
                      }}
                    />
                    <span
                      className="position-absolute text-muted"
                      style={{
                        fontSize: "0.7rem",
                        bottom: "100%",
                        marginBottom: "4px",
                        fontWeight: 600,
                      }}
                    >
                      {(model.metrics.accuracy * 100).toFixed(1)}%
                    </span>
                  </div>
                  <span
                    className="text-center text-muted"
                    style={{ fontSize: "0.72rem", lineHeight: 1.2 }}
                  >
                    {model.name}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </>
  );
}
