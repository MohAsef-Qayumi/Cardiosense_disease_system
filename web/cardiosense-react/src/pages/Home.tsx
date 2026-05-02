import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  loadModelMetrics,
  formatPercent,
  formatNumber,
  EnsembleMetrics,
} from "@/services/metrics";

export default function Home() {
  const [metrics, setMetrics] = useState<EnsembleMetrics | null>(null);

  useEffect(() => {
    loadModelMetrics().then(setMetrics);
  }, []);

  const bestModel = metrics?.models.reduce((best, m) =>
    m.metrics.accuracy > best.metrics.accuracy ? m : best,
  );

  return (
    <>
      <header className="hero">
        <span className="hero-orb hero-orb-a" />
        <span className="hero-orb hero-orb-b" />
        <div className="container">
          <div className="row g-4 align-items-center">
            <div className="col-lg-7" data-reveal>
              <span className="hero-badge">
                Heart Disease Prediction System
              </span>
              <h1 className="hero-title">
                Early Risk Detection with{" "}
                <span className="accent">5 ML Models</span>
              </h1>
              <p className="hero-copy">
                CardioSense AI uses an ensemble of XGBoost, LightGBM, Random
                Forest, Soft Voting, and Stacking models with sigmoid
                calibration to predict cardiovascular disease risk from clinical
                indicators.
              </p>
              <div className="hero-actions">
                <Link to="/signup" className="btn-primary-cs">
                  <i className="bi bi-person-plus" /> Create Free Account
                </Link>
                <Link to="/login" className="btn-outline-cs">
                  <i className="bi bi-box-arrow-in-right" /> Already have an
                  account
                </Link>
              </div>
              {metrics && bestModel && (
                <div className="metric-strip">
                  <div className="metric-tile">
                    <span className="metric-value">
                      {formatPercent(bestModel.metrics.accuracy)}
                    </span>
                    <span className="metric-label">Test Accuracy</span>
                  </div>
                  <div className="metric-tile">
                    <span className="metric-value">
                      {formatNumber(bestModel.metrics.roc_auc, 3)}
                    </span>
                    <span className="metric-label">Test ROC-AUC</span>
                  </div>
                  <div className="metric-tile">
                    <span className="metric-value">
                      {formatPercent(bestModel.metrics.recall)}
                    </span>
                    <span className="metric-label">Recall</span>
                  </div>
                  <div className="metric-tile">
                    <span className="metric-value">
                      {formatNumber(metrics.threshold, 2)}
                    </span>
                    <span className="metric-label">Threshold</span>
                  </div>
                </div>
              )}
            </div>
            <div className="col-lg-5" data-reveal>
              <aside className="glass-panel model-panel">
                <p className="panel-heading">5 Trained Models</p>
                <div className="prob-gauge" aria-hidden="true">
                  <div className="prob-ring" />
                  <div className="prob-core">
                    <strong>
                      {bestModel
                        ? formatNumber(bestModel.metrics.roc_auc, 3)
                        : "0.804"}
                    </strong>
                    <span>Best ROC-AUC</span>
                  </div>
                </div>
                <ul className="snapshot-list">
                  {metrics ? (
                    metrics.models.map((m) => (
                      <li key={m.name}>
                        <span>{m.name}</span>
                        <strong>
                          Acc: {formatPercent(m.metrics.accuracy)}
                        </strong>
                      </li>
                    ))
                  ) : (
                    <>
                      <li>
                        <span>XGBoost</span>
                        <strong>Acc: 73.12%</strong>
                      </li>
                      <li>
                        <span>LightGBM</span>
                        <strong>Acc: 73.27%</strong>
                      </li>
                      <li>
                        <span>Random Forest</span>
                        <strong>Acc: 73.33%</strong>
                      </li>
                      <li>
                        <span>Soft Voting</span>
                        <strong>Acc: 73.39%</strong>
                      </li>
                      <li>
                        <span>Stacking</span>
                        <strong>Acc: 73.36%</strong>
                      </li>
                    </>
                  )}
                </ul>
              </aside>
            </div>
          </div>
        </div>
      </header>

      <section className="section-block auth-strip-section">
        <div className="container">
          <div className="auth-strip" data-reveal>
            <div className="auth-strip-head">
              <span className="section-kicker">Get Started</span>
              <h2 className="section-title">Use CardioSense AI in 3 steps</h2>
            </div>
            <div className="auth-step-grid">
              <article className="auth-step-card">
                <span className="auth-step-index">1</span>
                <h3>Create your account</h3>
                <p>
                  Register to access the prediction dashboard and track your
                  health history.
                </p>
                <Link to="/signup">Open sign up form</Link>
              </article>
              <article className="auth-step-card">
                <span className="auth-step-index">2</span>
                <h3>Sign in to dashboard</h3>
                <p>
                  Access your personalized dashboard with prediction history and
                  analytics.
                </p>
                <Link to="/login">Go to login</Link>
              </article>
              <article className="auth-step-card">
                <span className="auth-step-index">3</span>
                <h3>Run risk predictions</h3>
                <p>
                  Enter your clinical data and get instant heart disease risk
                  assessment.
                </p>
                <Link to="/signup">Get started</Link>
              </article>
            </div>
          </div>
        </div>
      </section>

      <section className="section-block model-showcase-section">
        <div className="container">
          <div className="section-header" data-reveal>
            <span className="section-kicker">Model Details</span>
            <h2 className="section-title">
              5 Trained Models with Real Metrics
            </h2>
          </div>
          {metrics ? (
            <div className="model-showcase-grid" data-reveal>
              {metrics.models.map((model, idx) => (
                <article key={idx} className="model-card">
                  <div className="model-card-head">
                    <span className="model-icon">
                      <i className="bi bi-diagram-3"></i>
                    </span>
                    <h3>{model.fullName}</h3>
                  </div>
                  <div className="model-card-body">
                    <span className="metric-chip">
                      Accuracy: {formatPercent(model.metrics.accuracy)} | ROC:{" "}
                      {formatNumber(model.metrics.roc_auc, 3)}
                    </span>
                    <span className="metric-chip">
                      Precision: {formatPercent(model.metrics.precision)} |
                      Recall: {formatPercent(model.metrics.recall)}
                    </span>
                    <span className="metric-chip">
                      F1: {formatPercent(model.metrics.f1)} | Threshold:{" "}
                      {formatNumber(model.metrics.threshold, 3)}
                    </span>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="model-showcase-grid" data-reveal>
              <article className="model-card">
                <div className="model-card-head">
                  <h3>XGBoost Calibrated</h3>
                </div>
                <div className="model-card-body">
                  <span className="metric-chip">
                    Accuracy: 73.12% | ROC: 0.802
                  </span>
                </div>
              </article>
              <article className="model-card">
                <div className="model-card-head">
                  <h3>LightGBM Calibrated</h3>
                </div>
                <div className="model-card-body">
                  <span className="metric-chip">
                    Accuracy: 73.27% | ROC: 0.804
                  </span>
                </div>
              </article>
              <article className="model-card">
                <div className="model-card-head">
                  <h3>Random Forest Calibrated</h3>
                </div>
                <div className="model-card-body">
                  <span className="metric-chip">
                    Accuracy: 73.33% | ROC: 0.803
                  </span>
                </div>
              </article>
              <article className="model-card">
                <div className="model-card-head">
                  <h3>Soft Voting Ensemble</h3>
                </div>
                <div className="model-card-body">
                  <span className="metric-chip">
                    Accuracy: 73.39% | ROC: 0.804
                  </span>
                </div>
              </article>
              <article className="model-card">
                <div className="model-card-head">
                  <h3>Stacking Ensemble</h3>
                </div>
                <div className="model-card-body">
                  <span className="metric-chip">
                    Accuracy: 73.36% | ROC: 0.804
                  </span>
                </div>
              </article>
            </div>
          )}
          {metrics && bestModel && (
            <p className="text-center mt-4" data-reveal>
              <span className="stat-value">
                {formatPercent(bestModel.metrics.accuracy)}
              </span>{" "}
              best accuracy from <strong>{bestModel.name}</strong>
            </p>
          )}
        </div>
      </section>

      <section className="section-block bg-muted">
        <div className="container">
          <div className="section-header" data-reveal>
            <span className="section-kicker">How It Works</span>
            <h2 className="section-title">Ensemble Prediction Pipeline</h2>
          </div>
          <div className="pipeline-flow" data-reveal>
            <article className="pipeline-step">
              <div className="pipeline-icon">
                <i className="bi bi-1-circle"></i>
              </div>
              <h3>Input Features</h3>
              <p>
                11 clinical & lifestyle features: age, gender, height, weight,
                blood pressure, cholesterol, glucose, smoking, alcohol, physical
                activity.
              </p>
            </article>
            <div className="pipeline-arrow">
              <i className="bi bi-arrow-right"></i>
            </div>
            <article className="pipeline-step">
              <div className="pipeline-icon">
                <i className="bi bi-2-circle"></i>
              </div>
              <h3>5 Base Models</h3>
              <p>
                XGBoost, LightGBM, Random Forest with sigmoid calibration + Soft
                Voting & Stacking ensembles.
              </p>
            </article>
            <div className="pipeline-arrow">
              <i className="bi bi-arrow-right"></i>
            </div>
            <article className="pipeline-step">
              <div className="pipeline-icon">
                <i className="bi bi-3-circle"></i>
              </div>
              <h3>Risk Probability</h3>
              <p>
                Average probability from all models, threshold{" "}
                {metrics ? formatNumber(metrics.threshold, 2) : "0.42"} for
                balanced accuracy.
              </p>
            </article>
          </div>
        </div>
      </section>
    </>
  );
}
