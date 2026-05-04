export interface ModelMetrics {
  accuracy: number;
  roc_auc: number;
  precision: number;
  recall: number;
  f1: number;
  threshold: number;
}

export interface ModelInfo {
  name: string;
  fullName: string;
  metrics: ModelMetrics;
}

export interface EnsembleMetrics {
  models: ModelInfo[];
  bestModel: string;
  bestAccuracy: number;
  threshold: number;
  config: {
    calibrationMethod: string;
    randomState: number;
    targetRecall: number;
    targetAccuracy: number;
  };
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

function parseApiMetrics(data: any): EnsembleMetrics {
  const models: ModelInfo[] = (data.models || []).map((m: any) => ({
    name: m.name,
    fullName: m.full_name, 
    metrics: {
      accuracy: m.accuracy,
      roc_auc: m.roc_auc,
      precision: m.precision,
      recall: m.recall,
      f1: m.f1,
      threshold: m.threshold,
    },
  }));

  const selected = (data.models || []).find((m: any) => m.is_selected);
  const bestAccuracy =
    selected?.accuracy ??
    (models.length > 0
      ? Math.max(...models.map((m) => m.metrics.accuracy))
      : 0);

  return {
    models,
    bestModel: data.selected_model || (models.length > 0 ? models[0].name : ""),
    bestAccuracy,
    threshold: data.selected_threshold ?? 0.5,
    config: {
      calibrationMethod: data.config?.calibration_method ?? "sigmoid",
      randomState: data.config?.random_state ?? 42,
      targetRecall: data.config?.target_recall ?? 0.83,
      targetAccuracy: data.config?.target_accuracy ?? 0.78,
    },
  };
}

function parseStaticMetrics(data: any): EnsembleMetrics {
  if (data.models && Array.isArray(data.models)) {
    return {
      models: data.models.map((m: any) => ({
        name: m.name,
        fullName: m.fullName,
        metrics: {
          accuracy: m.accuracy,
          roc_auc: m.roc_auc,
          precision: m.precision,
          recall: m.recall,
          f1: m.f1,
          threshold: m.threshold,
        },
      })),
      bestModel: data.bestModel,
      bestAccuracy: data.bestAccuracy,
      threshold: data.threshold,
      config: {
        calibrationMethod: data.config?.calibration_method || "sigmoid",
        randomState: data.config?.random_state || 42,
        targetRecall: data.config?.target_recall || 0.83,
        targetAccuracy: data.config?.target_accuracy || 0.78,
      },
    };
  }

  // Legacy best_ensemble_metrics.json format (steps dict)
  if (data.steps && typeof data.steps === "object") {
    const nameMap: Record<string, [string, string]> = {
      step1_xgb_calibrated: ["XGBoost", "XGBoost Calibrated"],
      step1_lgbm_calibrated: ["LightGBM", "LightGBM Calibrated"],
      step1_rf_calibrated: ["Random Forest", "Random Forest Calibrated"],
      step2_soft_voting_calibrated: ["Soft Voting", "Soft Voting Ensemble"],
      step3_stacking_calibrated: ["Stacking", "Stacking Ensemble"],
      xgb_cal: ["XGBoost", "XGBoost Calibrated"],
      lgbm_cal: ["LightGBM", "LightGBM Calibrated"],
      rf_cal: ["Random Forest", "Random Forest Calibrated"],
      soft_voting: ["Soft Voting", "Soft Voting Ensemble"],
      stacking: ["Stacking", "Stacking Ensemble"],
    };

    const models: ModelInfo[] = Object.entries(data.steps).map(
      ([key, step]: [string, any]) => {
        const [name, fullName] = nameMap[key] ?? [key, key];
        const cr = step.classification_report ?? {};
        const diseaseCr = cr["1"] ?? cr["Disease"] ?? {};
        return {
          name,
          fullName,
          metrics: {
            accuracy: step.accuracy ?? 0,
            roc_auc: step.roc_auc ?? 0,
            precision: step.precision ?? 0,
            recall: step.recall ?? 0,
            f1: diseaseCr["f1-score"] ?? step.f1 ?? 0,
            threshold: step.threshold ?? 0.5,
          },
        };
      },
    );

    const best = models.reduce(
      (b, m) => (m.metrics.accuracy > b.metrics.accuracy ? m : b),
      models[0],
    );
    return {
      models,
      bestModel: best?.name ?? "",
      bestAccuracy: best?.metrics.accuracy ?? 0,
      threshold: best?.metrics.threshold ?? 0.5,
      config: {
        calibrationMethod: data.config?.calibration_method ?? "sigmoid",
        randomState: data.config?.random_state ?? 42,
        targetRecall: data.config?.target_recall ?? 0.83,
        targetAccuracy: data.config?.target_accuracy ?? 0.78,
      },
    };
  }

  return getDefaultMetrics();
}

export async function loadModelMetrics(): Promise<EnsembleMetrics> {
  // 1. Try live API endpoint first
  try {
    const res = await fetch(`${API_BASE}/models/metrics`, {
      signal: AbortSignal.timeout(4000),
    });
    if (res.ok) {
      const data = await res.json();
      return parseApiMetrics(data);
    }
  } catch {
    // fall through to static file
  }

  // 2. Fall back to static public file
  try {
    const res = await fetch("/model-metrics.json");
    const data = await res.json();
    return parseStaticMetrics(data);
  } catch {
    return getDefaultMetrics();
  }
}

export function getDefaultMetrics(): EnsembleMetrics {
  return {
    models: [
      {
        name: "XGBoost",
        fullName: "XGBoost Calibrated",
        metrics: {
          accuracy: 0.7312,
          roc_auc: 0.8025,
          precision: 0.7203,
          recall: 0.7468,
          f1: 0.7333,
          threshold: 0.428,
        },
      },
      {
        name: "LightGBM",
        fullName: "LightGBM Calibrated",
        metrics: {
          accuracy: 0.7327,
          roc_auc: 0.8037,
          precision: 0.72,
          recall: 0.7522,
          f1: 0.7358,
          threshold: 0.424,
        },
      },
      {
        name: "Random Forest",
        fullName: "Random Forest Calibrated",
        metrics: {
          accuracy: 0.7333,
          roc_auc: 0.803,
          precision: 0.7205,
          recall: 0.753,
          f1: 0.7364,
          threshold: 0.417,
        },
      },
      {
        name: "Soft Voting",
        fullName: "Soft Voting Ensemble",
        metrics: {
          accuracy: 0.7339,
          roc_auc: 0.8042,
          precision: 0.7203,
          recall: 0.7556,
          f1: 0.7375,
          threshold: 0.419,
        },
      },
      {
        name: "Stacking",
        fullName: "Stacking Ensemble",
        metrics: {
          accuracy: 0.7336,
          roc_auc: 0.8041,
          precision: 0.72,
          recall: 0.7553,
          f1: 0.7373,
          threshold: 0.42,
        },
      },
    ],
    bestModel: "Soft Voting",
    bestAccuracy: 0.7339,
    threshold: 0.4185,
    config: {
      calibrationMethod: "sigmoid",
      randomState: 42,
      targetRecall: 0.83,
      targetAccuracy: 0.78,
    },
  };
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

export function formatNumber(value: number, decimals: number = 4): string {
  return value.toFixed(decimals);
}
