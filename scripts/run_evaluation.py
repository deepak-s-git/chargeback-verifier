"""Run the DisputeShield evaluation over a dataset split.

Examples:
    python scripts/run_evaluation.py --split validation            # full engine
    python scripts/run_evaluation.py --split validation --mode partial   # ablation
    python scripts/run_evaluation.py --split test                   # final, held-out

Calibrate on train/validation; run the test split only once, at the end.
"""

import argparse
import os
import sys

# Make both the repo root (for `backend.*`) and `backend/` (for `src.*`) importable,
# regardless of the caller's PYTHONPATH.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, os.path.join(_REPO_ROOT, "backend"))

from backend.evaluation.evaluate import run_evaluation

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the DisputeShield evaluation.")
    parser.add_argument("--split", default="validation", choices=["train", "validation", "test"])
    parser.add_argument("--mode", default="full", choices=["full", "partial"],
                        help="'full' = real engine; 'partial' = ablation (no CE3.0/contradiction/injection).")
    args = parser.parse_args()

    run_evaluation(args.split, mode=args.mode)
