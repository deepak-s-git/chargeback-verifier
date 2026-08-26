"""Evaluation metrics and report rendering for DisputeShield.

The headline question is whether the system routes each case to the correct
*recommendation band*, so recommendation is scored as a 4-class classification
problem (CONTEST / REVIEW / INSUFFICIENT / ABSTAIN) with per-class and macro
precision / recall / F1 plus a full confusion matrix — a single accuracy number
would hide, for example, a model that over-predicts CONTEST (the costly error in
a defense-only system).

Three further axes are measured because they encode the product's safety
guarantees:

* **Score-in-range** — does the numeric score land in the archetype's expected
  window? Catches mis-calibration even when the band is correct.
* **Contradiction detection** — treated as a binary detection task (any
  contradiction vs none) with P/R/F1, plus exact-count accuracy.
* **Injection detection** — binary detection of prompt-injection content; recall
  here is a security property (a miss means unsanitised adversarial text was
  treated as trustworthy).

All metrics are pure functions of the predictions and ground truth; the report
is deterministic text suitable for committing and diffing.
"""

from typing import Any, Dict, List

from backend.evaluation.predict import Prediction

CLASSES = ["CONTEST", "REVIEW", "INSUFFICIENT", "ABSTAIN"]


def _prf(tp: int, fp: int, fn: int) -> Dict[str, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    # gt_positives lets the renderer distinguish "0% recall" (real misses) from
    # "n/a" (the split simply contains no positive cases to detect).
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn,
            "gt_positives": tp + fn, "pred_positives": tp + fp}


def compute_metrics(predictions: List[Prediction], ground_truth: Dict[str, Any]) -> Dict[str, Any]:
    """Compute the full metric suite for a set of predictions.

    Args:
        predictions: One :class:`Prediction` per case.
        ground_truth: Mapping of case_id -> ground-truth record.

    Returns:
        A nested dict of metrics (see module docstring for the axes).
    """
    paired = [(p, ground_truth[p.case_id]) for p in predictions if p.case_id in ground_truth]
    total = len(paired)

    # --- Recommendation: 4-class classification ---
    correct = sum(1 for p, gt in paired if p.recommendation == gt["expected_recommendation"])
    accuracy = correct / total if total else 0.0

    per_class: Dict[str, Dict[str, float]] = {}
    support: Dict[str, int] = {}
    for c in CLASSES:
        tp = sum(1 for p, gt in paired if p.recommendation == c and gt["expected_recommendation"] == c)
        fp = sum(1 for p, gt in paired if p.recommendation == c and gt["expected_recommendation"] != c)
        fn = sum(1 for p, gt in paired if p.recommendation != c and gt["expected_recommendation"] == c)
        per_class[c] = _prf(tp, fp, fn)
        support[c] = sum(1 for _, gt in paired if gt["expected_recommendation"] == c)

    present = [c for c in CLASSES if support[c] > 0]
    macro_precision = sum(per_class[c]["precision"] for c in present) / len(present) if present else 0.0
    macro_recall = sum(per_class[c]["recall"] for c in present) / len(present) if present else 0.0
    macro_f1 = sum(per_class[c]["f1"] for c in present) / len(present) if present else 0.0
    weighted_f1 = (sum(per_class[c]["f1"] * support[c] for c in present) / total) if total else 0.0

    # Confusion matrix: confusion[gt][pred].
    confusion = {g: {p: 0 for p in CLASSES} for g in CLASSES}
    for p, gt in paired:
        g = gt["expected_recommendation"]
        if g in confusion and p.recommendation in confusion[g]:
            confusion[g][p.recommendation] += 1

    # Majority-class baseline (always predict the most-supported class).
    majority_class = max(CLASSES, key=lambda c: support[c]) if total else None
    majority_baseline = (support[majority_class] / total) if (total and majority_class) else 0.0

    # --- Score calibration ---
    in_range = 0
    for p, gt in paired:
        lo, hi = gt["expected_score_range"]
        if lo <= p.score <= hi:
            in_range += 1

    # --- Contradiction detection (binary: any vs none) + exact count ---
    c_tp = c_fp = c_fn = exact = 0
    for p, gt in paired:
        gt_n = gt.get("expected_contradictions", 0)
        gt_pos, pred_pos = gt_n > 0, p.contradictions > 0
        c_tp += gt_pos and pred_pos
        c_fp += (not gt_pos) and pred_pos
        c_fn += gt_pos and (not pred_pos)
        exact += p.contradictions == gt_n
    contradiction = _prf(c_tp, c_fp, c_fn)
    contradiction["exact_count_accuracy"] = exact / total if total else 0.0

    # --- Injection detection (binary) ---
    i_tp = i_fp = i_fn = 0
    for p, gt in paired:
        gt_pos, pred_pos = bool(gt.get("has_injection", False)), p.injection
        i_tp += gt_pos and pred_pos
        i_fp += (not gt_pos) and pred_pos
        i_fn += gt_pos and (not pred_pos)
    injection = _prf(i_tp, i_fp, i_fn)

    return {
        "total": total,
        "accuracy": accuracy,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "per_class": per_class,
        "support": support,
        "confusion": confusion,
        "majority_class": majority_class,
        "majority_baseline": majority_baseline,
        "score_in_range": {"count": in_range, "total": total, "rate": (in_range / total if total else 0.0)},
        "contradiction": contradiction,
        "injection": injection,
    }


def _pct(x: float) -> str:
    return f"{x * 100:5.1f}%"


def generate_report(metrics: Dict[str, Any], *, split: str, mode: str) -> str:
    """Render a deterministic, human-readable text report from ``metrics``."""
    m = metrics
    lines: List[str] = []
    lines.append("=" * 78)
    lines.append(f"DisputeShield — Evaluation Report   (split={split}, mode={mode})")
    lines.append("=" * 78)
    lines.append("")
    lines.append(f"Cases evaluated ............ {m['total']}")
    lines.append(f"Recommendation accuracy .... {_pct(m['accuracy'])}")
    lines.append(f"Macro F1 ................... {_pct(m['macro_f1'])}  "
                 f"(P {_pct(m['macro_precision'])} / R {_pct(m['macro_recall'])})")
    lines.append(f"Weighted F1 ................ {_pct(m['weighted_f1'])}")
    lines.append(f"Majority-class baseline .... {_pct(m['majority_baseline'])}  "
                 f"(always predict {m['majority_class']})")
    lines.append(f"Score within expected range  {_pct(m['score_in_range']['rate'])}  "
                 f"({m['score_in_range']['count']}/{m['score_in_range']['total']})")
    lines.append("")

    # Per-class table.
    lines.append("Per-class recommendation metrics")
    lines.append("-" * 78)
    lines.append(f"{'class':<14}{'precision':>11}{'recall':>11}{'f1':>11}{'support':>10}")
    for c in CLASSES:
        pc = m["per_class"][c]
        lines.append(f"{c:<14}{_pct(pc['precision']):>11}{_pct(pc['recall']):>11}"
                     f"{_pct(pc['f1']):>11}{m['support'][c]:>10}")
    lines.append("")

    # Confusion matrix (rows = ground truth, cols = predicted).
    lines.append("Confusion matrix  (rows = ground truth, cols = predicted)")
    lines.append("-" * 78)
    header = f"{'gt \\ pred':<14}" + "".join(f"{c[:10]:>12}" for c in CLASSES)
    lines.append(header)
    for g in CLASSES:
        row = f"{g:<14}" + "".join(f"{m['confusion'][g][p]:>12}" for p in CLASSES)
        lines.append(row)
    lines.append("")

    # Detection metrics.
    con, inj = m["contradiction"], m["injection"]
    lines.append("Contradiction detection (any vs none)")
    lines.append("-" * 78)
    lines.append(_detection_line(con, extra=f"   exact-count acc {_pct(con['exact_count_accuracy'])}"))
    lines.append(f"  tp {con['tp']}  fp {con['fp']}  fn {con['fn']}  (positives in split: {con['gt_positives']})")
    lines.append("")
    lines.append("Prompt-injection detection")
    lines.append("-" * 78)
    lines.append(_detection_line(inj))
    lines.append(f"  tp {inj['tp']}  fp {inj['fp']}  fn {inj['fn']}  (positives in split: {inj['gt_positives']})")
    lines.append("")
    return "\n".join(lines)


def _detection_line(d: Dict[str, float], extra: str = "") -> str:
    """Format a detection metric line, showing 'n/a' when the split has no positives."""
    if d["gt_positives"] == 0 and d["pred_positives"] == 0:
        return "  n/a — no positive cases in this split (nothing to detect, none predicted)"
    return (f"  precision {_pct(d['precision'])}   recall {_pct(d['recall'])}   "
            f"f1 {_pct(d['f1'])}{extra}")
