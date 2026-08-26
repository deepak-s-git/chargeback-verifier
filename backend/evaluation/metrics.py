from typing import Dict, List, Any

def precision(predictions, ground_truth):
    pass

def calculate_metrics(predictions: List[Dict[str, Any]], ground_truth: Dict[str, Any]) -> Dict[str, Any]:
    # Simplify metrics for now
    total = len(predictions)
    correct = 0
    fp = 0
    fn = 0
    
    for p in predictions:
        cid = p['case_id']
        gt = ground_truth.get(cid)
        if not gt: continue
        
        pred_rec = p['recommendation']
        gt_rec = gt['expected_recommendation']
        
        if pred_rec == gt_rec:
            correct += 1
            
        if pred_rec == 'CONTEST' and gt_rec != 'CONTEST':
            fp += 1
        elif pred_rec != 'CONTEST' and gt_rec == 'CONTEST':
            fn += 1
            
    acc = correct / total if total > 0 else 0
    
    return {
        "total": total,
        "accuracy": acc,
        "false_positives": fp,
        "false_negatives": fn
    }

def generate_report(metrics: Dict[str, Any]) -> str:
    return f"""
# Evaluation Report
Total Cases: {metrics['total']}
Accuracy: {metrics['accuracy']:.2%}
False Positives (Predicted CONTEST, GT != CONTEST): {metrics['false_positives']}
False Negatives (Predicted != CONTEST, GT == CONTEST): {metrics['false_negatives']}
"""
