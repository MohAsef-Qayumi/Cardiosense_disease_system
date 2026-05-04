import { useEffect, useState } from "react";
import { loadModelMetrics, formatPercent, formatNumber, EnsembleMetrics } from "@/services/metrics";

export default function DashboardModels() {
  const [metrics, setMetrics] = useState<EnsembleMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadModelMetrics().then(m => {
      setMetrics(m);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="d-flex align-items-center justify-content-center" style={{ height: "60vh" }}>
        <div className="text-center">
          <div className="spinner-border text-primary mb-3" role="status"></div>
          <p className="text-muted">Loading model metrics from ML pipeline...</p>
        </div>
      </div>
    );
  }

  const bestModel = metrics!.models.reduce((best, m) => 
    m.metrics.accuracy > best.metrics.accuracy ? m : best
  );

  const modelConfig: Record<string, { color: string; bg: string; icon: string; desc: string }> = {
    "XGBoost": { color: "#d62839", bg: "#ffebee", icon: "bi-tree", desc: "Gradient boosted trees with Optuna hyperparameter tuning" },
    "LightGBM": { color: "#108a7e", bg: "#e0f7f5", icon: "bi-lightning", desc: "Leaf-wise tree growth for faster training" },
    "Random Forest": { color: "#ef8a43", bg: "#fff3e0", icon: "bi-forest", desc: "Bagging ensemble with 446 estimators" },
    "Soft Voting": { color: "#7c4dff", bg: "#ede7f6", icon: "bi-collection", desc: "Probability averaging across calibrated base models" },
    "Stacking": { color: "#00bcd4", bg: "#e0f7fa", icon: "bi-stack", desc: "Meta-learner on top of base model predictions" },
  };

  return (
    <>
      <div className="dashboard-header" data-reveal>
        <h1>Model Information</h1>
        <p className="text-muted">Complete pipeline details: 5 calibrated models with threshold optimization.</p>
      </div>

      {/* Stats Row */}
      <div className="dashboard-stats-grid">
        {[
          { icon: "bi-trophy", label: "Best Model", value: bestModel.name, color: "#ffd700" },
          { icon: "bi-tag", label: "Total Models", value: String(metrics!.models.length), color: "var(--teal)" },
          { icon: "bi-sliders", label: "Optimal Threshold", value: formatNumber(metrics!.threshold, 4), color: "var(--amber)" },
          { icon: "bi-check-circle", label: "Calibration", value: metrics!.config.calibrationMethod, color: "var(--primary)" },
        ].map((stat, idx) => (
          <div key={idx} className="dashboard-stat-card" data-reveal style={{ borderLeft: `4px solid ${stat.color}` }}>
            <div className="d-flex justify-content-between align-items-start">
              <div>
                <div className="stat-label text-muted">{stat.label}</div>
                <div className="stat-value">{stat.value}</div>
              </div>
              <div className="stat-icon" style={{ opacity: 0.15, fontSize: "1.8rem", color: stat.color }}>
                <i className={`bi ${stat.icon}`}></i>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Model Cards */}
      <div className="row g-3 mb-4">
        {metrics!.models.map((model, idx) => {
          const config = modelConfig[model.name] || { color: "#666", bg: "#f5f5f5", icon: "bi-cpu", desc: "" };
          const isBest = model.name === bestModel.name;
          return (
            <div key={idx} className="col-md-6 col-lg-4" data-reveal>
              <div className="dashboard-panel h-100 position-relative" 
                style={{ 
                  borderTop: `3px solid ${config.color}`,
                  boxShadow: isBest ? `0 4px 20px ${config.color}30` : undefined
                }}
              >
                {isBest && (
                  <span className="badge position-absolute" style={{ top: "12px", right: "12px", background: config.color, color: "#fff", fontSize: "0.7rem" }}>
                    <i className="bi bi-trophy-fill me-1"></i>BEST
                  </span>
                )}
                <div className="d-flex align-items-center gap-3 mb-3">
                  <div className="d-flex align-items-center justify-content-center rounded-circle"
                    style={{ width: "48px", height: "48px", background: config.bg, color: config.color }}>
                    <i className={`bi ${config.icon}`} style={{ fontSize: "1.4rem" }}></i>
                  </div>
                  <div>
                    <h5 className="m-0" style={{ fontSize: "1rem" }}>{model.fullName}</h5>
                    <p className="text-muted m-0" style={{ fontSize: "0.78rem" }}>{config.desc}</p>
                  </div>
                </div>
                
                <div className="row g-2 text-center">
                  <div className="col-4">
                    <div style={{ fontSize: "1.1rem", fontWeight: 700, color: config.color }}>{formatPercent(model.metrics.accuracy)}</div>
                    <div style={{ fontSize: "0.7rem", color: "var(--ink-muted)" }}>Accuracy</div>
                  </div>
                  <div className="col-4">
                    <div style={{ fontSize: "1.1rem", fontWeight: 700, color: config.color }}>{formatNumber(model.metrics.roc_auc, 3)}</div>
                    <div style={{ fontSize: "0.7rem", color: "var(--ink-muted)" }}>ROC-AUC</div>
                  </div>
                  <div className="col-4">
                    <div style={{ fontSize: "1.1rem", fontWeight: 700, color: config.color }}>{formatPercent(model.metrics.recall)}</div>
                    <div style={{ fontSize: "0.7rem", color: "var(--ink-muted)" }}>Recall</div>
                  </div>
                </div>
                
                <div className="mt-3 pt-3 border-top">
                  <div className="d-flex justify-content-between text-muted" style={{ fontSize: "0.78rem" }}>
                    <span>Precision</span>
                    <strong>{formatPercent(model.metrics.precision)}</strong>
                  </div>
                  <div className="d-flex justify-content-between text-muted" style={{ fontSize: "0.78rem" }}>
                    <span>F1-Score</span>
                    <strong>{formatPercent(model.metrics.f1)}</strong>
                  </div>
                  <div className="d-flex justify-content-between text-muted" style={{ fontSize: "0.78rem" }}>
                    <span>Threshold</span>
                    <strong>{formatNumber(model.metrics.threshold, 4)}</strong>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Detailed Comparison Table */}
      <div className="dashboard-panel" data-reveal>
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h3 className="m-0"><i className="bi bi-table text-muted"></i> Detailed Model Comparison</h3>
          <span className="badge" style={{ background: "var(--bg-soft)", color: "var(--ink)" }}>
            Sorted by Accuracy
          </span>
        </div>
        <div className="table-responsive">
          <table className="table" style={{ fontSize: "0.88rem" }}>
            <thead>
              <tr>
                <th>Model</th>
                <th>Accuracy</th>
                <th>ROC-AUC</th>
                <th>Precision</th>
                <th>Recall</th>
                <th>F1</th>
                <th>Threshold</th>
                <th>Visual</th>
              </tr>
            </thead>
            <tbody>
              {[...metrics!.models]
                .sort((a, b) => b.metrics.accuracy - a.metrics.accuracy)
                .map((model, idx) => {
                  const isBest = model.name === bestModel.name;
                  return (
                    <tr key={idx} style={{ background: isBest ? "rgba(124, 77, 255, 0.04)" : "transparent" }}>
                      <td>
                        <div className="d-flex align-items-center gap-2">
                          {isBest && <i className="bi bi-trophy-fill text-warning"></i>}
                          <strong>{model.fullName}</strong>
                        </div>
                      </td>
                      <td><strong style={{ color: isBest ? "var(--primary)" : "inherit" }}>{formatPercent(model.metrics.accuracy)}</strong></td>
                      <td>{formatNumber(model.metrics.roc_auc, 3)}</td>
                      <td>{formatPercent(model.metrics.precision)}</td>
                      <td>{formatPercent(model.metrics.recall)}</td>
                      <td>{formatPercent(model.metrics.f1)}</td>
                      <td>{formatNumber(model.metrics.threshold, 4)}</td>
                      <td style={{ width: "100px" }}>
                        <div className="progress" style={{ height: "5px", background: "rgba(0,0,0,0.05)" }}>
                          <div className="progress-bar" style={{ 
                            width: `${model.metrics.accuracy * 100}%`, 
                            background: isBest ? "var(--primary)" : "#ccc",
                            borderRadius: "2px"
                          }} />
                        </div>
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Hyperparameters */}
      <div className="dashboard-panel mt-4" data-reveal>
        <h3 className="mb-4"><i className="bi bi-gear text-muted"></i> Optimal Hyperparameters</h3>
        <div className="row g-4">
          {[
            {
              name: "XGBoost",
              color: "#d62839",
              params: [
                { k: "n_estimators", v: "206" },
                { k: "learning_rate", v: "0.092" },
                { k: "max_depth", v: "6" },
                { k: "min_child_weight", v: "6" },
                { k: "subsample", v: "0.874" },
                { k: "colsample_bytree", v: "0.640" },
                { k: "reg_lambda", v: "2.119" },
              ]
            },
            {
              name: "LightGBM",
              color: "#108a7e",
              params: [
                { k: "n_estimators", v: "617" },
                { k: "learning_rate", v: "0.060" },
                { k: "num_leaves", v: "85" },
                { k: "max_depth", v: "2" },
                { k: "min_child_samples", v: "24" },
                { k: "subsample", v: "0.670" },
                { k: "reg_lambda", v: "0.305" },
              ]
            },
            {
              name: "Random Forest",
              color: "#ef8a43",
              params: [
                { k: "n_estimators", v: "446" },
                { k: "max_depth", v: "10" },
                { k: "min_samples_split", v: "4" },
                { k: "min_samples_leaf", v: "2" },
                { k: "max_features", v: "sqrt" },
              ]
            },
          ].map((model, idx) => (
            <div key={idx} className="col-md-4">
              <div className="p-3 rounded" style={{ background: "var(--bg-soft)", borderLeft: `3px solid ${model.color}` }}>
                <h5 style={{ color: model.color, marginBottom: "12px" }}>{model.name}</h5>
                <div className="d-flex flex-column gap-1">
                  {model.params.map((p, pidx) => (
                    <div key={pidx} className="d-flex justify-content-between" style={{ fontSize: "0.85rem" }}>
                      <span className="text-muted">{p.k}</span>
                      <code style={{ background: "#fff", padding: "1px 6px", borderRadius: "4px", fontSize: "0.8rem" }}>{p.v}</code>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Pipeline Info */}
      <div className="dashboard-panel mt-4" data-reveal>
        <h3 className="mb-4"><i className="bi bi-shield-check text-muted"></i> Pipeline Configuration</h3>
        <div className="row g-3">
          {[
            { icon: "bi-collection", title: "Ensemble Methods", desc: "Soft Voting (probability averaging) & Stacking (meta-learner on calibrated probabilities)", color: "#7c4dff" },
            { icon: "bi-check-circle", title: "Calibration", desc: `Sigmoid calibration applied to all base models. Random state: ${metrics!.config.randomState}`, color: "var(--teal)" },
            { icon: "bi-bullseye", title: "Objective", desc: `Balanced accuracy optimization targeting ${metrics!.config.targetRecall * 100}% recall and ${metrics!.config.targetAccuracy * 100}% accuracy`, color: "var(--primary)" },
            { icon: "bi-database", title: "Dataset", desc: "68,000+ BRFSS 2015 samples. 13,722 test samples (20% holdout). 11 clinical & lifestyle features.", color: "var(--amber)" },
            { icon: "bi-shield-shaded", title: "Validation", desc: "5-fold cross-validation with stratification. Precision floor: 72% enforced.", color: "#00bcd4" },
            { icon: "bi-graph-up-arrow", title: "Optimization", desc: "Threshold search over 41 values from 0.30 to 0.70 with 0.01 step size.", color: "#4caf50" },
          ].map((item, idx) => (
            <div key={idx} className="col-md-6 col-lg-4">
              <div className="d-flex gap-3 p-3 rounded" style={{ background: "var(--bg-soft)", height: "100%" }}>
                <div className="flex-shrink-0">
                  <div className="d-flex align-items-center justify-content-center rounded-circle"
                    style={{ width: "40px", height: "40px", background: `${item.color}15`, color: item.color }}>
                    <i className={`bi ${item.icon}`}></i>
                  </div>
                </div>
                <div>
                  <h5 style={{ fontSize: "0.9rem", marginBottom: "4px" }}>{item.title}</h5>
                  <p className="text-muted m-0" style={{ fontSize: "0.82rem", lineHeight: 1.5 }}>{item.desc}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
