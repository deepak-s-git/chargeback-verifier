"""Failure analysis for DisputeShield evaluation runs.

Aggregates the ways the system diverged from ground truth so a report reader can
see *where* it fails, not just how often:

* per-archetype accuracy (which generative template is hardest);
* recommendation confusion pairs (``GT->PRED`` counts among errors);
* score-calibration misses (right band, wrong numeric window, or vice versa);
* contradiction and injection detection misses (false positives / negatives),
  which matter disproportionately in a defense-only system.

Every bucket carries case ids so a failure can be reproduced and inspected.
"""

from collections import defaultdict
from typing import Any, Dict, List

from backend.evaluation.predict import Prediction


def analyze_failures(predictions: List[Prediction], ground_truth: Dict[str, Any]) -> Dict[str, Any]:
    paired = [(p, ground_truth[p.case_id]) for p in predictions if p.case_id in ground_truth]

    misclassified: List[Dict[str, Any]] = []
    confusion_pairs: Dict[str, int] = defaultdict(int)
    by_archetype: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"total": 0, "correct": 0, "errors": []})
    score_out_of_range: List[Dict[str, Any]] = []
    contradiction_misses: List[Dict[str, Any]] = []
    injection_misses: List[Dict[str, Any]] = []

    for p, gt in paired:
        archetype = gt.get("archetype", "unknown")
        bucket = by_archetype[archetype]
        bucket["total"] += 1

        gt_rec, pred_rec = gt["expected_recommendation"], p.recommendation
        if pred_rec == gt_rec:
            bucket["correct"] += 1
        else:
            pair = f"{gt_rec}->{pred_rec}"
            confusion_pairs[pair] += 1
            bucket["errors"].append({"case_id": p.case_id, "pair": pair, "network": gt.get("network", "")})
            misclassified.append({
                "case_id": p.case_id,
                "archetype": archetype,
                "network": gt.get("network", ""),
                "gt_recommendation": gt_rec,
                "pred_recommendation": pred_rec,
                "pred_score": p.score,
                "expected_score_range": list(gt["expected_score_range"]),
            })

        lo, hi = gt["expected_score_range"]
        if not (lo <= p.score <= hi):
            score_out_of_range.append({
                "case_id": p.case_id,
                "archetype": archetype,
                "pred_score": p.score,
                "expected_score_range": [lo, hi],
            })

        gt_con = gt.get("expected_contradictions", 0) > 0
        if gt_con != (p.contradictions > 0):
            contradiction_misses.append({
                "case_id": p.case_id,
                "archetype": archetype,
                "kind": "false_negative" if gt_con else "false_positive",
                "expected": gt.get("expected_contradictions", 0),
                "predicted": p.contradictions,
            })

        gt_inj = bool(gt.get("has_injection", False))
        if gt_inj != p.injection:
            injection_misses.append({
                "case_id": p.case_id,
                "archetype": archetype,
                "kind": "false_negative" if gt_inj else "false_positive",
            })

    for archetype, bucket in by_archetype.items():
        bucket["accuracy"] = bucket["correct"] / bucket["total"] if bucket["total"] else 0.0

    return {
        "misclassified_count": len(misclassified),
        "by_archetype": dict(sorted(by_archetype.items())),
        "confusion_pairs": dict(sorted(confusion_pairs.items(), key=lambda kv: -kv[1])),
        "score_out_of_range": score_out_of_range,
        "contradiction_misses": contradiction_misses,
        "injection_misses": injection_misses,
        "misclassified": misclassified,
    }


def render_failure_summary(failures: Dict[str, Any]) -> str:
    """Render a compact text summary of the failure breakdown for the report."""
    lines: List[str] = []
    lines.append("Per-archetype accuracy")
    lines.append("-" * 78)
    lines.append(f"{'archetype':<24}{'correct':>10}{'total':>8}{'accuracy':>11}")
    for archetype, b in failures["by_archetype"].items():
        lines.append(f"{archetype:<24}{b['correct']:>10}{b['total']:>8}{b['accuracy'] * 100:>10.1f}%")
    lines.append("")

    lines.append("Recommendation confusion pairs (errors only)")
    lines.append("-" * 78)
    if failures["confusion_pairs"]:
        for pair, n in failures["confusion_pairs"].items():
            lines.append(f"  {pair:<28} {n}")
    else:
        lines.append("  (none — every case landed in the correct band)")
    lines.append("")

    lines.append(f"Score-out-of-range cases ... {len(failures['score_out_of_range'])}")
    lines.append(f"Contradiction misses ....... {len(failures['contradiction_misses'])}")
    lines.append(f"Injection misses ........... {len(failures['injection_misses'])}")
    lines.append("")
    return "\n".join(lines)
