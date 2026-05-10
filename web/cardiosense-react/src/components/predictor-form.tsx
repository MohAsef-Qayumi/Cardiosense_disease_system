import { FormEvent, useMemo, useState } from "react";

const defaultData: Record<string, number> = {
  sample_id: 1001,
  age_years: 52,
  gender: 2,
  height: 172,
  weight: 82,
  ap_hi: 140,
  ap_lo: 90,
  cholesterol: 2,
  gluc: 2,
  smoke: 0,
  alco: 0,
  active: 1,
};

const fieldMeta: Record<
  string,
  {
    label: string;
    type: string;
    min?: number;
    max?: number;
    step?: string;
    options?: { value: number; label: string }[];
  }
> = {
  sample_id: { label: "Sample ID", type: "number", min: 0 },
  age_years: { label: "Age (years)", type: "number", min: 18, max: 100 },
  gender: {
    label: "Gender code",
    type: "select",
    options: [
      { value: 1, label: "female" },
      { value: 2, label: "male" },
    ],
  },
  height: { label: "Height (cm)", type: "number", min: 120, max: 220 },
  weight: {
    label: "Weight (kg)",
    type: "number",
    min: 30,
    max: 220,
    step: "0.1",
  },
  ap_hi: { label: "Systolic BP", type: "number", min: 80, max: 240 },
  ap_lo: { label: "Diastolic BP", type: "number", min: 40, max: 160 },
  cholesterol: {
    label: "Cholesterol category",
    type: "select",
    options: [
      { value: 1, label: "normal" },
      { value: 2, label: "above normal" },
      { value: 3, label: "well above normal" },
    ],
  },
  gluc: {
    label: "Glucose category",
    type: "select",
    options: [
      { value: 1, label: "normal" },
      { value: 2, label: "above normal" },
      { value: 3, label: "well above normal" },
    ],
  },
  smoke: {
    label: "Smoking status",
    type: "select",
    options: [
      { value: 0, label: "No" },
      { value: 1, label: "Yes" },
    ],
  },
  alco: {
    label: "Alcohol intake",
    type: "select",
    options: [
      { value: 0, label: "No" },
      { value: 1, label: "Yes" },
    ],
  },
  active: {
    label: "Physically active",
    type: "select",
    options: [
      { value: 1, label: "Yes" },
      { value: 0, label: "No" },
    ],
  },
};

const DEFAULT_API =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export function PredictorForm() {
  const [result, setResult] = useState<number | null>(null);
  const [confidence, setConfidence] = useState("");
  const [meta, setMeta] = useState("");
  const [source, setSource] = useState("");

  const riskLabel = useMemo(() => {
    if (result === null) return "Awaiting input";
    if (result < 35) return "Low risk zone";
    if (result < 65) return "Medium risk zone";
    return "High risk zone";
  }, [result]);

  const riskTagClass = useMemo(() => {
    if (result === null) return "";
    if (result < 35) return "risk-low";
    if (result < 65) return "risk-medium";
    return "risk-high";
  }, [result]);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const payload = {
      id: Number(form.get("sample_id")),
      age: Number(form.get("age_years")) * 365,
      gender: Number(form.get("gender")),
      height: Number(form.get("height")),
      weight: Number(form.get("weight")),
      ap_hi: Number(form.get("ap_hi")),
      ap_lo: Number(form.get("ap_lo")),
      cholesterol: Number(form.get("cholesterol")),
      gluc: Number(form.get("gluc")),
      smoke: Number(form.get("smoke")),
      alco: Number(form.get("alco")),
      active: Number(form.get("active")),
    };

    try {
      const res = await fetch(`${DEFAULT_API.replace(/\/$/, "")}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      const prob = Number(data?.result?.prob_disease ?? 0) * 100;
      setResult(prob);
      setConfidence(
        "Confidence: " + (data?.result?.confidence_tier || "medium"),
      );
      setMeta("Model version: " + (data?.result?.model_version || "v1"));
      setSource("Prediction via API");
    } catch {
      setResult(null);
      setConfidence("");
      setMeta("");
      setSource("Error: ML service unavailable. Please try again.");
    }
  }

  return (
    <div className="row g-4 align-items-start">
      <div className="col-xl-8">
        <div className="glass-panel predictor-wrap" data-reveal>
          <form id="predictForm" className="field-grid" onSubmit={onSubmit}>
            {Object.entries(defaultData).map(([key, value]) => {
              const meta = fieldMeta[key];
              return (
                <div key={key} className="field">
                  <label htmlFor={key}>{meta?.label || key}</label>
                  {meta?.type === "select" ? (
                    <select id={key} name={key} defaultValue={value} required>
                      {meta.options?.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      id={key}
                      name={key}
                      type={meta?.type || "text"}
                      defaultValue={value}
                      min={meta?.min}
                      max={meta?.max}
                      step={meta?.step}
                      required
                    />
                  )}
                </div>
              );
            })}
            <div className="submit-row">
              <span className="submit-hint">
                Input map: age is converted from years to days before request
                submission.
              </span>
              <button className="btn-primary-cs" type="submit">
                <i className="bi bi-play-circle" /> Predict Risk
              </button>
            </div>
          </form>
        </div>
      </div>

      <div className="col-xl-4">
        <div
          id="predictionResult"
          className={`glass-panel result-panel ${result !== null ? "is-visible" : ""}`}
          data-reveal
        >
          <p className="panel-heading">Prediction output</p>
          <p className="result-empty">
            Submit the form to view disease probability, confidence tier, and
            model metadata.
          </p>

          <div className="result-data">
            <span id="riskOutput" className="result-score">
              {result === null ? "-" : `${result.toFixed(1)}%`}
            </span>
            <span id="riskTag" className={`risk-tag ${riskTagClass}`}>
              {riskLabel}
            </span>
            <div className="risk-meter">
              <div
                id="riskFill"
                className="risk-fill"
                style={{ width: result === null ? "0%" : `${result}%` }}
              />
            </div>
            <p id="confidenceOutput" className="result-meta">
              {confidence}
            </p>
            <p id="metaOutput" className="result-meta">
              {meta}
            </p>
            <p id="sourceOutput" className="result-meta">
              {source}
            </p>
          </div>
        </div>

        <div className="glass-panel helper-panel" data-reveal>
          <p className="panel-heading">Usage notes</p>
          <ul className="helper-list">
            <li>Prediction payload follows the strict request schema.</li>
            <li>If API fails, the UI falls back to a local estimator.</li>
            <li>
              This interface is for educational inference support, not
              diagnosis.
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
