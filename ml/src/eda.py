"""
Module 2: Exploratory Data Analysis (EDA)
Analyzes the heart disease dataset and generates plots.
Updated to use centralized config paths.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend to avoid Tkinter warnings
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from pathlib import Path
from datetime import datetime
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    PLOTS_DIR, PLOT_TARGET_DIST, PLOT_CORR_HEATMAP,
    PLOT_FEATURE_DIST, PLOT_AGE_THALACH, TARGET_COLUMN
)

sns.set_style("whitegrid")
plt.rcParams["figure.dpi"] = 100


def _savefig_safely(path: Path):
    """
    Save plots with a fallback filename when an existing file is locked.
    """
    try:
        plt.savefig(str(path), bbox_inches="tight")
        return path
    except PermissionError:
        fallback = path.with_name(
            f"{path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{path.suffix}"
        )
        plt.savefig(str(fallback), bbox_inches="tight")
        print(f"  [WARN] Could not overwrite {path.name}; saved {fallback.name} instead.")
        return fallback


def run_eda(df: pd.DataFrame, save_plots: bool = True, target_col: str = TARGET_COLUMN):
    """Full EDA pipeline."""
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("EXPLORATORY DATA ANALYSIS — Heart Disease Dataset")
    print("=" * 60)

    # 1. Basic shape and types
    print(f"\n[1] Dataset Shape: {df.shape}")
    print(f"     Rows: {df.shape[0]} | Columns: {df.shape[1]}")
    print(f"\n[2] Column Data Types:\n{df.dtypes}")

    # 2. Missing values
    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(2)
    missing_df = pd.DataFrame({"Missing Count": missing, "Missing %": missing_pct})
    missing_df = missing_df[missing_df["Missing Count"] > 0]
    print(f"\n[3] Missing Values:\n{missing_df}")

    # 3. Descriptive statistics
    print(f"\n[4] Descriptive Statistics:\n{df.describe().round(2)}")

    # 4. Target distribution
    target_counts = df[target_col].value_counts()
    print(f"\n[5] Target Distribution:\n{target_counts}")
    if len(target_counts) == 2 and target_counts.min() > 0:
        print(f"     Class Imbalance Ratio: {target_counts.max()/target_counts.min():.2f}:1")

    # 5. Correlation matrix
    numeric_df = df.select_dtypes(include=[np.number])
    corr_matrix = numeric_df.corr()
    top_features = corr_matrix[target_col].abs().sort_values(ascending=False)
    print(f"\n[6] Top Features Correlated with Target:\n{top_features}")

    if save_plots:
        _plot_target_distribution(df, target_col)
        _plot_correlation_heatmap(corr_matrix)
        _plot_feature_distributions(df, target_col)
        _plot_age_vs_thalach(df, target_col)
        print(f"\n[EDA] All plots saved to '{PLOTS_DIR}/'")

    return corr_matrix, top_features


def _plot_target_distribution(df, target_col):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Heart Disease Target Distribution", fontsize=14, fontweight="bold")

    # Pie chart
    counts = df[target_col].value_counts().sort_index()
    labels = [f"Class {idx}" for idx in counts.index]
    colors = ["#2ecc71", "#e74c3c"]
    axes[0].pie(counts, labels=labels, colors=colors, autopct="%1.1f%%",
                startangle=90, explode=(0, 0.05))
    axes[0].set_title("Class Distribution")

    # Bar chart with counts
    bar_labels = [f"Class {idx}" for idx in counts.index]
    bars = axes[1].bar(bar_labels, counts.values, color=colors[: len(bar_labels)], width=0.5)
    axes[1].set_title("Sample Counts per Class")
    axes[1].set_ylabel("Count")
    for bar, count in zip(bars, counts):
        axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                     str(count), ha='center', va='bottom', fontweight='bold')

    plt.tight_layout()
    _savefig_safely(PLOT_TARGET_DIST)
    plt.close()


def _plot_correlation_heatmap(corr_matrix):
    fig, ax = plt.subplots(figsize=(12, 10))
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
    sns.heatmap(corr_matrix, mask=mask, annot=True, fmt=".2f", cmap="RdYlGn",
                center=0, square=True, linewidths=0.5, ax=ax,
                annot_kws={"size": 8})
    ax.set_title("Feature Correlation Heatmap", fontsize=14, fontweight="bold", pad=15)
    plt.tight_layout()
    _savefig_safely(PLOT_CORR_HEATMAP)
    plt.close()


def _plot_feature_distributions(df, target_col):
    numeric_cols = [
        c for c in df.select_dtypes(include=[np.number]).columns
        if c != target_col and c != "id"
    ]
    preferred = ["age", "ap_hi", "ap_lo", "weight", "height", "chol", "thalach", "oldpeak"]
    continuous_cols = [c for c in preferred if c in numeric_cols]
    if len(continuous_cols) < 5:
        for c in numeric_cols:
            if c not in continuous_cols:
                continuous_cols.append(c)
            if len(continuous_cols) == 5:
                break

    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    fig.suptitle("Feature Distributions by Target Class", fontsize=14, fontweight="bold")
    axes = axes.flatten()

    for i, col in enumerate(continuous_cols):
        for target_val, color, label in [(0, "#2ecc71", "No Disease"), (1, "#e74c3c", "Disease")]:
            subset = df[df[target_col] == target_val][col].dropna()
            axes[i].hist(subset, alpha=0.6, color=color, label=label, bins=20, edgecolor="white")
        axes[i].set_title(col.upper(), fontweight="bold")
        axes[i].set_xlabel("Value")
        axes[i].set_ylabel("Frequency")
        axes[i].legend(fontsize=8)

    # Missing values bar in last subplot
    missing = df.isnull().sum()
    missing = missing[missing > 0]
    if not missing.empty:
        axes[5].bar(missing.index, missing.values, color="#e67e22")
        axes[5].set_title("Missing Values per Column", fontweight="bold")
        axes[5].set_ylabel("Count")
    else:
        axes[5].text(0.5, 0.5, "No Missing Values", ha="center", va="center",
                     fontsize=12, transform=axes[5].transAxes)
        axes[5].set_title("Missing Values", fontweight="bold")

    plt.tight_layout()
    _savefig_safely(PLOT_FEATURE_DIST)
    plt.close()


def _plot_age_vs_thalach(df, target_col):
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = df[target_col].map({0: "#2ecc71", 1: "#e74c3c"})

    if "age" in df.columns and "thalach" in df.columns:
        x_col, y_col = "age", "thalach"
        title = "Age vs Max Heart Rate by Heart Disease Status"
    elif "age" in df.columns and "ap_hi" in df.columns:
        x_col, y_col = "age", "ap_hi"
        title = "Age vs Systolic BP by Heart Disease Status"
    elif "height" in df.columns and "weight" in df.columns:
        x_col, y_col = "height", "weight"
        title = "Height vs Weight by Heart Disease Status"
    else:
        ax.text(0.5, 0.5, "No suitable feature pair available", ha="center", va="center", transform=ax.transAxes)
        ax.set_title("Pairwise Feature Plot", fontsize=13, fontweight="bold")
        plt.tight_layout()
        _savefig_safely(PLOT_AGE_THALACH)
        plt.close()
        return

    ax.scatter(df[x_col], df[y_col], c=colors, alpha=0.6, edgecolors="white", linewidths=0.5, s=60)
    ax.set_xlabel(x_col, fontsize=12)
    ax.set_ylabel(y_col, fontsize=12)
    ax.set_title(title, fontsize=13, fontweight="bold")
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor="#2ecc71", label="No Disease"),
                       Patch(facecolor="#e74c3c", label="Heart Disease")]
    ax.legend(handles=legend_elements, fontsize=10)
    plt.tight_layout()
    _savefig_safely(PLOT_AGE_THALACH)
    plt.close()


if __name__ == "__main__":
    from src.data_loader import load_heart_disease_data
    df = load_heart_disease_data()
    run_eda(df)
