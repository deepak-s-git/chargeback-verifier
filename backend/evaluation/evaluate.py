"""Evaluation orchestrator for DisputeShield.

Loads a dataset split, runs the decision system over every case (``full`` or the
``partial`` ablation), computes the metric suite and failure breakdown, prints
the report, and writes both a human-readable ``.txt`` and a machine-readable
``.json`` sidecar into ``backend/evaluation/reports/`` (co-located with the
dataset, and git-ignored — the reports are deterministic, regenerable artifacts;
``docs/evaluation.md`` is the committed record of the numbers).

Test-split isolation: the ``test`` split is held out for a single, final
measurement. Calibrate and iterate on ``train`` / ``validation`` only; a banner
is printed whenever the held-out split is touched so it is never run casually.
Paths are resolved relative to this file so the harness is cwd-independent.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from src.domain.models import DisputeCase

from backend.evaluation.failure_analysis import analyze_failures, render_failure_summary
from backend.evaluation.metrics import compute_metrics, generate_report
from backend.evaluation.predict import FULL, PARTIAL, Prediction, predict

_EVAL_DIR = Path(__file__).resolve().parent
_CASES_DIR = _EVAL_DIR / "dataset" / "cases"
_REPO_ROOT = _EVAL_DIR.parents[1]
_REPORTS_DIR = _EVAL_DIR / "reports"


def _load_cases(split: str) -> List[DisputeCase]:
    split_dir = _CASES_DIR / split
    if not split_dir.exists():
        raise FileNotFoundError(
            f"Split directory {split_dir} does not exist. Generate the dataset first "
            f"(scripts/generate_dataset.py)."
        )
    cases: List[DisputeCase] = []
    for path in sorted(split_dir.glob("*.json")):
        cases.append(DisputeCase(**json.loads(path.read_text())))
    return cases


def _load_ground_truth() -> Dict[str, Any]:
    gt_file = _CASES_DIR / "ground_truth.json"
    if not gt_file.exists():
        raise FileNotFoundError(f"Ground truth {gt_file} not found. Generate the dataset first.")
    return json.loads(gt_file.read_text())


def run_evaluation(split: str = "validation", mode: str = FULL) -> Dict[str, Any]:
    """Evaluate one split under one mode; write reports and return the metrics.

    Args:
        split: ``train`` | ``validation`` | ``test``.
        mode: ``full`` (real engine) | ``partial`` (ablation).

    Returns:
        The computed metrics dict.
    """
    if mode not in (FULL, PARTIAL):
        raise ValueError(f"unknown mode {mode!r}")

    if split == "test":
        print("!" * 78)
        print("!!  HELD-OUT TEST SPLIT  — run once, at the end. Do not calibrate on this.")
        print("!" * 78)

    ground_truth = _load_ground_truth()
    cases = _load_cases(split)
    print(f"Evaluating {len(cases)} cases  (split={split}, mode={mode}) ...")

    predictions: List[Prediction] = [predict(case, mode=mode) for case in cases]

    metrics = compute_metrics(predictions, ground_truth)
    failures = analyze_failures(predictions, ground_truth)

    report = generate_report(metrics, split=split, mode=mode)
    failure_summary = render_failure_summary(failures)
    full_text = report + failure_summary
    print(full_text)

    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    txt_path = _REPORTS_DIR / f"evaluation_report_{split}_{mode}.txt"
    json_path = _REPORTS_DIR / f"evaluation_report_{split}_{mode}.json"
    txt_path.write_text(full_text)
    json_path.write_text(json.dumps(
        {
            "split": split,
            "mode": mode,
            "metrics": metrics,
            "failures": failures,
            "predictions": [p.to_dict() for p in predictions],
        },
        indent=2,
    ))
    print(f"\nWrote {txt_path.name} and {json_path.name} to {_REPORTS_DIR.relative_to(_REPO_ROOT)}/.")
    return metrics
