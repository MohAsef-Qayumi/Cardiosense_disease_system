import { Link } from "react-router-dom";

export default function About() {
  return (
    <>
      <section className="page-hero">
        <div className="container">
          <div className="breadcrumbs" data-reveal>
            <Link to="/">Overview</Link>
            <span>/</span>
            <span className="current">About</span>
          </div>
          <h1 className="section-title" data-reveal>Why this heart disease prediction project exists</h1>
          <p className="page-subtitle" data-reveal>
            CardioSense AI was built to translate machine learning outputs into a usable clinical-support workflow: train, validate, deploy, monitor, and improve.
          </p>
        </div>
      </section>

      <section className="section-block">
        <div className="container">
          <div className="row g-4 align-items-start">
            <div className="col-lg-7" data-reveal>
              <div className="glass-panel p-4 p-lg-5">
                <span className="section-kicker">Mission</span>
                <h2 className="section-title mt-2">Support early cardiovascular risk awareness</h2>
                <p className="section-copy mt-3">
                  Heart disease remains one of the leading causes of mortality worldwide. The objective of this project is to use structured clinical indicators and lifestyle factors to estimate risk earlier, so interventions can happen sooner.
                </p>
                <p className="section-copy mt-3">
                  Beyond model training, the project focuses on production concerns: strict schemas, versioned model management, rollback, persistence, and drift monitoring. The frontend redesign presents those capabilities clearly for demos and evaluation.
                </p>
              </div>
            </div>

            <div className="col-lg-5" data-reveal>
              <div className="feature-card h-100">
                <span className="feature-icon"><i className="bi bi-check2-circle"></i></span>
                <h3 className="feature-title">Project focus points</h3>
                <ul className="helper-list mt-3">
                  <li>Leak-safe preprocessing and reproducible splits</li>
                  <li>XGBoost with threshold optimization for imbalanced classes</li>
                  <li>FastAPI endpoints for single and batch inference</li>
                  <li>Registry-aware model activation and rollback</li>
                  <li>Operational audit logs and feedback labeling</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section-block alt">
        <div className="container">
          <div className="section-head" data-reveal>
            <span className="section-kicker">Scope</span>
            <h2 className="section-title">What is included in this build</h2>
          </div>

          <div className="feature-grid">
            <article className="feature-card" data-reveal>
              <span className="feature-icon"><i className="bi bi-funnel"></i></span>
              <h3 className="feature-title">Data Engineering</h3>
              <p className="feature-copy">Pipeline components for loading, preprocessing, and split verification to minimize leakage and preserve experimental integrity.</p>
            </article>

            <article className="feature-card" data-reveal>
              <span className="feature-icon"><i className="bi bi-cpu"></i></span>
              <h3 className="feature-title">Model Training</h3>
              <p className="feature-copy">XGBoost model training with exported validation and test metrics plus calibrated threshold selection.</p>
            </article>

            <article className="feature-card" data-reveal>
              <span className="feature-icon"><i className="bi bi-cloud-arrow-up"></i></span>
              <h3 className="feature-title">Inference API</h3>
              <p className="feature-copy">Strict request/response contracts, route-level tracing context, and robust error handling through custom domain exceptions.</p>
            </article>

            <article className="feature-card" data-reveal>
              <span className="feature-icon"><i className="bi bi-eye"></i></span>
              <h3 className="feature-title">Monitoring Layer</h3>
              <p className="feature-copy">Model registry controls, drift snapshots, and feedback loops to support post-deployment quality tracking.</p>
            </article>
          </div>
        </div>
      </section>

      <section className="section-block">
        <div className="container">
          <div className="row g-4">
            <div className="col-lg-6" data-reveal>
              <span className="section-kicker">Milestones</span>
              <h2 className="section-title mt-2">Build timeline</h2>

              <div className="timeline mt-3">
                <article className="timeline-item">
                  <p className="timeline-time">Phase 1</p>
                  <h3 className="timeline-title">Data and feature preparation</h3>
                  <p className="timeline-copy">Dataset structure validation, preprocessing design, and split generation for reproducibility.</p>
                </article>

                <article className="timeline-item">
                  <p className="timeline-time">Phase 2</p>
                  <h3 className="timeline-title">Training and metric evaluation</h3>
                  <p className="timeline-copy">XGBoost tuning, threshold objective selection, and test benchmarking with error analysis exports.</p>
                </article>

                <article className="timeline-item">
                  <p className="timeline-time">Phase 3</p>
                  <h3 className="timeline-title">Inference and operational APIs</h3>
                  <p className="timeline-copy">FastAPI deployment, persistence repositories, and request logging with idempotency support.</p>
                </article>

                <article className="timeline-item">
                  <p className="timeline-time">Phase 4</p>
                  <h3 className="timeline-title">Frontend and usability layer</h3>
                  <p className="timeline-copy">Project-specific UI for model interpretation, API checks, and prediction demonstrations.</p>
                </article>
              </div>
            </div>

            <div className="col-lg-6" data-reveal>
              <span className="section-kicker">Team</span>
              <h2 className="section-title mt-2">People behind the project</h2>

              <div className="team-grid mt-3">
                <article className="team-card">
                  <h3 className="team-name">Mohammad Asef</h3>
                  <span className="team-role">Frontend and architecture</span>
                  <p className="team-copy">Led implementation and integration of UI and system structure.</p>
                </article>

                <article className="team-card">
                  <h3 className="team-name">Affan Ahmad</h3>
                  <span className="team-role">UX and visual design</span>
                  <p className="team-copy">Defined interaction flow, layout direction, and presentation consistency.</p>
                </article>

                <article className="team-card">
                  <h3 className="team-name">Hussain Hamza</h3>
                  <span className="team-role">Content and styling</span>
                  <p className="team-copy">Prepared communication content and styling refinements for clarity.</p>
                </article>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section-block alt">
        <div className="container">
          <div className="glass-panel p-4 p-lg-5" data-reveal>
            <span className="section-kicker">Responsible AI</span>
            <h2 className="section-title mt-2">Usage boundaries</h2>
            <ul className="helper-list mt-3">
              <li>This prediction output is a risk-support signal, not a standalone diagnosis.</li>
              <li>Threshold choice trades sensitivity and specificity and should be reviewed per use case.</li>
              <li>Feedback and drift monitoring are required to keep deployed behavior reliable over time.</li>
              <li>Clinical oversight remains mandatory for any real medical decision path.</li>
            </ul>
          </div>
        </div>
      </section>
    </>
  );
}