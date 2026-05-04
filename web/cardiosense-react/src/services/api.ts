import { useState, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

interface ModelMetrics {
  accuracy: number;
  roc_auc: number;
  precision: number;
  recall: number;
  f1: number;
  threshold: number;
}

interface ModelInfo {
  name: string;
  version: string;
  threshold: number;
  calibration: string;
  models: {
    name: string;
    accuracy: number;
    roc_auc: number;
    precision: number;
    recall: number;
    f1: number;
    threshold: number;
  }[];
}

interface PredictionResult {
  probability: number;
  risk_level: string;
  confidence: string;
  model_version: string;
  source: string;
}

export async function checkApiHealth(): Promise<{ status: string; model_version?: string }> {
  try {
    const res = await fetch(`${API_BASE}/health`);
    const data = await res.json();
    return { 
      status: data.status, 
      model_version: data.active_model_version 
    };
  } catch {
    return { status: "offline" };
  }
}

export async function runPrediction(payload: {
  id: number;
  age: number;
  gender: number;
  height: number;
  weight: number;
  ap_hi: number;
  ap_lo: number;
  cholesterol: number;
  gluc: number;
  smoke: number;
  alco: number;
  active: number;
}): Promise<PredictionResult> {
  const res = await fetch(`${API_BASE}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  
  if (!res.ok) throw new Error("Prediction failed");
  
  const data = await res.json();
  const prob = data.result.prob_disease * 100;
  
  return {
    probability: prob,
    risk_level: prob < 35 ? "Low" : prob < 65 ? "Medium" : "High",
    confidence: data.result.confidence_tier,
    model_version: data.model_version,
    source: "API"
  };
}

export async function getModelInfo(): Promise<ModelInfo> {
  try {
    const res = await fetch(`${API_BASE}/models/active`);
    if (!res.ok) throw new Error();
    const data = await res.json();
    
    return {
      name: data.model_name || "CardioSense Ensemble",
      version: data.model_version || "1.0.0",
      threshold: data.threshold_used || 0.42,
      calibration: "Sigmoid",
      models: []
    };
  } catch {
    return getDefaultModelInfo();
  }
}

export function getDefaultModelInfo(): ModelInfo {
  return {
    name: "CardioSense Ensemble",
    version: "1.0.0",
    threshold: 0.4185,
    calibration: "Sigmoid",
    models: [
      { name: "XGBoost Calibrated", accuracy: 0.7312, roc_auc: 0.802, precision: 0.7203, recall: 0.7468, f1: 0.7333, threshold: 0.428 },
      { name: "LightGBM Calibrated", accuracy: 0.7327, roc_auc: 0.804, precision: 0.7200, recall: 0.7522, f1: 0.7357, threshold: 0.424 },
      { name: "Random Forest Calibrated", accuracy: 0.7333, roc_auc: 0.803, precision: 0.7205, recall: 0.7530, f1: 0.7362, threshold: 0.417 },
      { name: "Soft Voting Ensemble", accuracy: 0.7339, roc_auc: 0.804, precision: 0.7203, recall: 0.7556, f1: 0.7375, threshold: 0.419 },
      { name: "Stacking Ensemble", accuracy: 0.7336, roc_auc: 0.804, precision: 0.7200, recall: 0.7553, f1: 0.7373, threshold: 0.420 },
    ]
  };
}

export function useApiHealth() {
  const [health, setHealth] = useState<{ status: string; model_version?: string }>({ status: "checking" });
  
  useEffect(() => {
    checkApiHealth().then(setHealth);
  }, []);
  
  return health;
}

export async function login(email: string, password: string) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  
  if (!res.ok) throw new Error("Login failed");
  return res.json();
}

export async function signup(data: { full_name: string; email: string; password: string; role: string }) {
  const res = await fetch(`${API_BASE}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  
  if (!res.ok) throw new Error("Signup failed");
  return res.json();
}

export async function getPredictionHistory(token: string) {
  const res = await fetch(`${API_BASE}/predictions/history`, {
    headers: { "Authorization": `Bearer ${token}` },
  });
  
  if (!res.ok) throw new Error("Failed to fetch history");
  return res.json();
}

export async function savePrediction(token: string, prediction: any) {
  const res = await fetch(`${API_BASE}/predictions`, {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify(prediction),
  });
  
  if (!res.ok) throw new Error("Failed to save prediction");
  return res.json();
}