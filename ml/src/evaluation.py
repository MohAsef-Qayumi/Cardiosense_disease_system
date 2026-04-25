"""Evaluation and plotting utilities for heart disease models."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import roc_auc_score, roc_curve

from config import (
    CONFIDENCE_HIGH_THRESHOLD,
    CONFIDENCE_MEDIUM_THRESHOLD,
    PLOT_EVALUATION,
)


def plot_evaluation(model, X_val, y_val, X_test, y_test, feature_names):
    """Generate evaluation and confidence plots."""
    fig = plt.figure(figsize=(18, 12))
    gs = gridspec.GridSpec(2, 3, figure=fig)
    fig.suptitle(
        "Confidence-Aware AI Inference Service — Evaluation",
        fontsize=15,
        fontweight="bold",
        y=0.98,
    )

    # Validation confusion matrix
    ax1 = fig.add_subplot(gs[0, 0])
    _, cm_val = model.evaluate(X_val, y_val, "Validation")
    sns.heatmap(
        cm_val,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=["No Disease", "Disease"],
        yticklabels=["No Disease", "Disease"],
        ax=ax1,
    )
    ax1.set_title("Confusion Matrix (Validation)", fontweight="bold")
    ax1.set_ylabel("Actual")
    ax1.set_xlabel("Predicted")

    # Test confusion matrix
    ax2 = fig.add_subplot(gs[0, 1])
    _, cm_test = model.evaluate(X_test, y_test, "Test")
    sns.heatmap(
        cm_test,
        annot=True,
        fmt="d",
        cmap="Oranges",
        xticklabels=["No Disease", "Disease"],
        yticklabels=["No Disease", "Disease"],
        ax=ax2,
    )
    ax2.set_title("Confusion Matrix (Test)", fontweight="bold")
    ax2.set_ylabel("Actual")
    ax2.set_xlabel("Predicted")

    # ROC curve
    ax3 = fig.add_subplot(gs[0, 2])
    probs = model.predict_proba(X_test)[:, 1]
    fpr, tpr, _ = roc_curve(y_test, probs)
    auc = roc_auc_score(y_test, probs)
    ax3.plot(fpr, tpr, color="#e74c3c", lw=2, label=f"AUC = {auc:.3f}")
    ax3.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5)
    ax3.fill_between(fpr, tpr, alpha=0.1, color="#e74c3c")
    ax3.set_xlabel("False Positive Rate")
    ax3.set_ylabel("True Positive Rate")
    ax3.set_title("ROC Curve (Test Set)", fontweight="bold")
    ax3.legend(loc="lower right", fontsize=11)

    # Confidence score distribution
    ax4 = fig.add_subplot(gs[1, 0])
    results = model.predict_with_confidence(X_test)
    ax4.hist(
        results[results["prediction"] == 0]["confidence_score"],
        bins=20,
        alpha=0.6,
        color="#2ecc71",
        label="No Disease",
    )
    ax4.hist(
        results[results["prediction"] == 1]["confidence_score"],
        bins=20,
        alpha=0.6,
        color="#e74c3c",
        label="Disease",
    )
    ax4.axvline(
        x=CONFIDENCE_HIGH_THRESHOLD,
        color="navy",
        linestyle="--",
        alpha=0.7,
        label="HIGH threshold",
    )
    ax4.axvline(
        x=CONFIDENCE_MEDIUM_THRESHOLD,
        color="orange",
        linestyle="--",
        alpha=0.7,
        label="MEDIUM threshold",
    )
    ax4.set_xlabel("Confidence Score")
    ax4.set_ylabel("Count")
    ax4.set_title("Confidence Score Distribution", fontweight="bold")
    ax4.legend(fontsize=8)

    # Confidence tiers
    ax5 = fig.add_subplot(gs[1, 1])
    tier_counts = results["confidence_tier"].value_counts()
    colors_tier = {"HIGH": "#27ae60", "MEDIUM": "#f39c12", "LOW": "#e74c3c"}
    bar_colors = [colors_tier.get(t, "gray") for t in tier_counts.index]
    bars = ax5.bar(tier_counts.index, tier_counts.values, color=bar_colors, width=0.5)
    for bar, val in zip(bars, tier_counts.values):
        ax5.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            str(val),
            ha="center",
            va="bottom",
            fontweight="bold",
        )
    ax5.set_title("Confidence Tier Distribution", fontweight="bold")
    ax5.set_ylabel("Count")

    # Feature importance
    ax6 = fig.add_subplot(gs[1, 2])
    if getattr(model, "calibrated_model", None) is not None:
        base_estimator = model.calibrated_model.calibrated_classifiers_[0].estimator
    else:
        base_estimator = getattr(model, "fitted_estimator", None)

    if base_estimator is None:
        ax6.text(0.5, 0.5, "No estimator available", ha="center", va="center", transform=ax6.transAxes)
        ax6.set_title("Feature Importance", fontweight="bold")
        plt.tight_layout()
        plt.savefig(str(PLOT_EVALUATION), bbox_inches="tight")
        plt.close()
        print(f"[Plot saved] -> {PLOT_EVALUATION}")
        return

    if hasattr(base_estimator, "feature_importances_"):
        importances = base_estimator.feature_importances_
        feat_imp = pd.Series(importances, index=feature_names).sort_values(ascending=True).tail(10)
        feat_imp.plot(kind="barh", ax=ax6, color="#3498db")
        ax6.set_title("Top 10 Feature Importances", fontweight="bold")
        ax6.set_xlabel("Importance Score")
    elif hasattr(base_estimator, "coef_"):
        coefs = np.abs(base_estimator.coef_[0])
        coef_imp = pd.Series(coefs, index=feature_names).sort_values(ascending=True).tail(10)
        coef_imp.plot(kind="barh", ax=ax6, color="#8e44ad")
        ax6.set_title("Top 10 |Coefficients|", fontweight="bold")
        ax6.set_xlabel("Absolute Coefficient")

    plt.tight_layout()
    plt.savefig(str(PLOT_EVALUATION), bbox_inches="tight")
    plt.close()
    print(f"[Plot saved] -> {PLOT_EVALUATION}")
