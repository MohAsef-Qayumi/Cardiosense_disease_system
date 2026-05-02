import { Link } from "react-router-dom";

export default function Modules() {
  const modules = [
    "Data Loader and Split",
    "Feature Preprocessing",
    "Model Training and Evaluation",
    "Inference API",
    "Model Registry Service",
    "Drift Monitoring",
  ];

  const endpoints = [
    "GET /health",
    "POST /predict",
    "POST /predict/batch",
    "POST /feedback",
    "GET /models/active",
    "POST /models/rollback",
  ];

  return (
    <>
      <section className="page-hero">
        <div className="container">
          <h1 className="section-title">Platform modules and API surfaces</h1>
          <p className="page-subtitle">This page maps project capabilities from data flow to deployment operations, including core inference endpoints.</p>
        </div>
      </section>
      <section className="section-block">
        <div className="container">
          <div className="feature-grid">
            <article className="feature-card">
              <span className="module-icon"><i className="bi bi-table" /></span>
              <h2 className="feature-title">Core project components</h2>
              <ul className="helper-list">{modules.map((item) => <li key={item}>{item}</li>)}</ul>
            </article>
            <article className="feature-card">
              <span className="module-icon"><i className="bi bi-globe2" /></span>
              <h2 className="feature-title">Inference and operations endpoints</h2>
              <ul className="helper-list">{endpoints.map((item) => <li key={item}>{item}</li>)}</ul>
            </article>
          </div>
        </div>
      </section>
      <section className="section-block alt">
        <div className="container">
          <div className="glass-panel p-4 p-lg-5">
            <span className="section-kicker">Operations</span>
            <h2 className="section-title mt-2">Deployment checklist</h2>
            <ul className="helper-list mt-3">
              <li>Install dependencies and train using main.py.</li>
              <li>Run API with uvicorn and validate health endpoint.</li>
              <li>Set active model and verify threshold metadata in /models/active.</li>
              <li>Run repository tests before presentation.</li>
              <li>Capture drift snapshots after deployment traffic starts.</li>
            </ul>
          </div>
        </div>
      </section>
      <section className="section-block">
        <div className="container">
          <div className="cta-banner">
            <span className="section-kicker">Practical Start</span>
            <h2 className="section-title">Use the redesigned UI with your local API</h2>
            <p className="section-copy">Start the FastAPI service at port 8000, then open the Overview page and run live predictions through the integrated form.</p>
            <div className="cta-actions">
              <Link to="/#predict" className="btn-primary-cs"><i className="bi bi-play-circle" /> Open Predictor</Link>
              <a href="../../ml/heart-disease-inference/docs/runbook.md" className="btn-outline-cs"><i className="bi bi-journal-text" /> Read Runbook</a>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
