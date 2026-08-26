"""Generate the DisputeShield synthetic evaluation dataset.

Deterministic (seed=42). By default every case is self-validated against the
real engine at generation time (see backend/evaluation/dataset/generator.py), so
a successful run guarantees the dataset is coherent with the current engine.

Usage:
    python scripts/generate_dataset.py                 # generate + self-validate
    python scripts/generate_dataset.py --no-validate   # skip validation (faster)
"""

import argparse
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, os.path.join(_REPO_ROOT, "backend"))

from backend.evaluation.dataset.generator import generate_dataset

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate the DisputeShield evaluation dataset.")
    parser.add_argument("--no-validate", action="store_true",
                        help="Skip per-case self-validation against the engine.")
    args = parser.parse_args()

    out_dir = os.path.join(_REPO_ROOT, "backend", "evaluation", "dataset", "cases")
    counts = generate_dataset(out_dir, validate=not args.no_validate)
    total = sum(counts.values())
    print(f"Generated {total} cases  ->  " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    if not args.no_validate:
        print("All cases self-validated against analyze_evidence.")
