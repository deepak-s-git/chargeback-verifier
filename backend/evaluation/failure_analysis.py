from typing import Dict, List, Any

def analyze_failures(predictions: List[Dict[str, Any]], ground_truth: Dict[str, Any]) -> Dict[str, Any]:
    failures = {
        "false_positives": [],
        "false_negatives": [],
        "other": []
    }
    
    for p in predictions:
        cid = p['case_id']
        gt = ground_truth.get(cid)
        if not gt: continue
        
        pred_rec = p['recommendation']
        gt_rec = gt['expected_recommendation']
        
        if pred_rec != gt_rec:
            if pred_rec == 'CONTEST':
                failures["false_positives"].append({"case_id": cid, "predicted": pred_rec, "actual": gt_rec})
            elif gt_rec == 'CONTEST':
                failures["false_negatives"].append({"case_id": cid, "predicted": pred_rec, "actual": gt_rec})
            else:
                failures["other"].append({"case_id": cid, "predicted": pred_rec, "actual": gt_rec})
                
    return failures
