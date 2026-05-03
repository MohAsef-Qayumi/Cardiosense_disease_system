import { PredictorForm } from "@/components/predictor-form";

export default function DashboardPredict() {
  return (
    <>
      <div className="dashboard-header" data-reveal>
        <h1>Heart Disease Predictor</h1>
        <p>Enter clinical data to get risk assessment from the ensemble model.</p>
      </div>

      <div className="dashboard-panel" data-reveal>
        <PredictorForm />
      </div>

      <div className="dashboard-panel mt-4" data-reveal>
        <h3><i className="bi bi-info-circle"></i> Input Features Guide</h3>
        <div className="feature-guide-grid">
          <div className="feature-item">
            <strong>Age</strong>
            <span>Your age in years (18-100)</span>
          </div>
          <div className="feature-item">
            <strong>Gender</strong>
            <span>1 = Female, 2 = Male</span>
          </div>
          <div className="feature-item">
            <strong>Height & Weight</strong>
            <span>Used to calculate BMI</span>
          </div>
          <div className="feature-item">
            <strong>Blood Pressure</strong>
            <span>Systolic (ap_hi) and Diastolic (ap_lo)</span>
          </div>
          <div className="feature-item">
            <strong>Cholesterol</strong>
            <span>1 = Normal, 2 = Above normal, 3 = Well above normal</span>
          </div>
          <div className="feature-item">
            <strong>Glucose</strong>
            <span>1 = Normal, 2 = Above normal, 3 = Well above normal</span>
          </div>
          <div className="feature-item">
            <strong>Lifestyle</strong>
            <span>Smoking, Alcohol intake, Physical activity (0 or 1)</span>
          </div>
        </div>
      </div>
    </>
  );
}