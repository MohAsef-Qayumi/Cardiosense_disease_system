export default function Research() {
  const notes = [
    "Threshold selection changed behavior more than model type.",
    "False negatives remain the largest error block.",
    "Drift snapshots are critical after deployment.",
    "Strict schemas reduce integration debugging time.",
    "Rollback support is essential in operations.",
    "Fallback UI behavior keeps demos resilient.",
  ];

  return (
    <>
      <section className="page-hero">
        <div className="container">
          <h1 className="section-title">Experiment and analysis notes</h1>
          <p className="page-subtitle">Key lessons from threshold tuning, error analysis, and deployment behavior while building this workflow.</p>
        </div>
      </section>
      <section className="section-block">
        <div className="container">
          <div className="glass-panel p-4 p-lg-5">
            <span className="pill teal">Featured note</span>
            <h2 className="section-title mt-2">Why threshold selection changed project behavior more than model type</h2>
            <p className="section-copy mt-3">Moving from default cutoff to optimized threshold for balanced accuracy had the biggest practical effect in inference behavior.</p>
          </div>
        </div>
      </section>
      <section className="section-block alt">
        <div className="container">
          <div className="section-head">
            <span className="section-kicker">Notebook Highlights</span>
            <h2 className="section-title">Recent project insights</h2>
          </div>
          <div className="article-grid">
            {notes.map((note) => (
              <article key={note} className="article-card">
                <p className="article-copy">{note}</p>
              </article>
            ))}
          </div>
        </div>
      </section>
      <section className="section-block">
        <div className="container">
          <div className="feature-grid">
            <article className="feature-card">
              <span className="feature-icon"><i className="bi bi-bar-chart-line" /></span>
              <h3 className="feature-title">Metric references used in this UI</h3>
              <ul className="helper-list">
                <li>Test accuracy: 0.7341</li>
                <li>Test ROC-AUC: 0.8042</li>
                <li>Test balanced accuracy: 0.7334</li>
                <li>Threshold used: 0.53</li>
              </ul>
            </article>
            <article className="feature-card">
              <span className="feature-icon"><i className="bi bi-folder2-open" /></span>
              <h3 className="feature-title">Source outputs</h3>
              <ul className="helper-list">
                <li>outputs/results/xgboost_metrics.json</li>
                <li>outputs/results/xgboost_metrics.csv</li>
                <li>outputs/results/error_analysis_summary.json</li>
                <li>outputs/results/error_analysis_misclassified.csv</li>
              </ul>
            </article>
          </div>
        </div>
      </section>
    </>
  );
}
