import json
from pathlib import Path
from src.domain.models import DisputeCase
from backend.evaluation.baseline import run_baseline
from backend.evaluation.metrics import calculate_metrics, generate_report
from backend.evaluation.failure_analysis import analyze_failures

def run_evaluation(split: str = 'validation'):
    base_dir = Path(f"backend/evaluation/dataset/cases/{split}")
    gt_file = Path("backend/evaluation/dataset/cases/ground_truth.json")
    
    with open(gt_file, "r") as f:
        ground_truth = json.load(f)
        
    predictions = []
    cases = []
    
    if not base_dir.exists():
        print(f"Directory {base_dir} does not exist.")
        return
        
    for p in base_dir.glob("*.json"):
        with open(p, "r") as f:
            data = json.load(f)
            case = DisputeCase(**data)
            cases.append(case)
            
    print(f"Running baseline on {len(cases)} cases...")
    for case in cases:
        res = run_baseline(case)
        predictions.append(res)
        
    metrics = calculate_metrics(predictions, ground_truth)
    failures = analyze_failures(predictions, ground_truth)
    
    report = generate_report(metrics)
    print(report)
    
    with open(f"evaluation_report_{split}.txt", "w") as f:
        f.write(report)
        f.write("\nFailures:\n")
        f.write(json.dumps(failures, indent=2))
