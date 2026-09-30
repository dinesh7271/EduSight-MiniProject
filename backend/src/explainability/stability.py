"""
Explainability Stability and Agreement Module for EduSight.
Evaluates Jaccard overlap and Spearman rank correlation between SHAP, permutation importance,
and tree-based feature importance to audit explanation stability across cohort subsets.
"""
import sys
from pathlib import Path
from typing import Dict, List, Set

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def compute_jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Compute Jaccard similarity index between two sets of features."""
    if not set_a and not set_b:
        return 1.0
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    return round(float(intersection / union), 4) if union > 0 else 0.0


def compute_rank_correlation(ranks_a: List[str], ranks_b: List[str]) -> Dict[str, float]:
    """Compute Spearman rank correlation across overlapping top features."""
    common_features = [f for f in ranks_a if f in ranks_b]
    if len(common_features) < 3:
        return {"spearman_rho": 0.0, "p_value": 1.0, "n_common": len(common_features)}

    order_a = [ranks_a.index(f) for f in common_features]
    order_b = [ranks_b.index(f) for f in common_features]

    rho, pval = spearmanr(order_a, order_b)
    return {
        "spearman_rho": round(float(rho), 4) if not np.isnan(rho) else 0.0,
        "p_value": round(float(pval), 4) if not np.isnan(pval) else 1.0,
        "n_common": len(common_features),
    }


def audit_explanation_stability(
    shap_importance: Dict[str, float],
    tree_importance: Dict[str, float],
    top_k: int = 5,
) -> Dict[str, any]:
    """
    Compare top-k influential features between SHAP and native tree importance.
    High agreement (>0.60 Jaccard) indicates robust, stable feature attributions.
    """
    sorted_shap = sorted(shap_importance.keys(), key=lambda k: shap_importance[k], reverse=True)
    sorted_tree = sorted(tree_importance.keys(), key=lambda k: tree_importance[k], reverse=True)

    top_shap_set = set(sorted_shap[:top_k])
    top_tree_set = set(sorted_tree[:top_k])

    jaccard = compute_jaccard_similarity(top_shap_set, top_tree_set)
    corr = compute_rank_correlation(sorted_shap[:top_k], sorted_tree[:top_k])

    return {
        "top_k": top_k,
        "jaccard_similarity": jaccard,
        "agreement_level": "high" if jaccard >= 0.6 else "moderate" if jaccard >= 0.4 else "low",
        "rank_correlation": corr,
        "top_shap_features": sorted_shap[:top_k],
        "top_tree_features": sorted_tree[:top_k],
    }
