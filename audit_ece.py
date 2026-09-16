import pandas as pd
import numpy as np

def calculate_brier_score(predictions, actuals):
    if not predictions or not actuals or len(predictions) != len(actuals):
        return None
    outcomes = ["home", "draw", "away"]
    total_sq_error = 0.0
    n = len(predictions)
    for p_dict, actual in zip(predictions, actuals):
        act = actual.lower().strip()
        for o in outcomes:
            p = p_dict.get(o, 0.0)
            y = 1.0 if act == o else 0.0
            total_sq_error += (p - y) ** 2
    return total_sq_error / n

def calculate_ece_binary(probs, labels, num_bins=8):
    probs = np.array(probs, dtype=float)
    labels = np.array(labels, dtype=float)
    n = len(probs)
    
    bin_boundaries = np.linspace(0, 1, num_bins + 1)
    ece = 0.0
    mce = 0.0
    bin_details = []
    
    for i in range(num_bins):
        lo = bin_boundaries[i]
        hi = bin_boundaries[i + 1]
        
        if i < num_bins - 1:
            in_bin = (probs >= lo) & (probs < hi)
        else:
            in_bin = (probs >= lo) & (probs <= hi)
            
        bin_size = int(np.sum(in_bin))
        
        if bin_size > 0:
            acc = float(np.mean(labels[in_bin]))
            conf = float(np.mean(probs[in_bin]))
            gap = abs(acc - conf)
            ece += (bin_size / n) * gap
            mce = max(mce, gap)
            bin_details.append({
                "bin": f"{lo:.2f}-{hi:.2f}",
                "count": bin_size,
                "mean_predicted_prob": round(conf, 4),
                "empirical_frequency": round(acc, 4),
                "abs_error": round(gap, 4)
            })
            
    return ece, mce, bin_details

def main():
    df = pd.read_csv("unified_betting_core/data/evidence_package/oos_predictions.csv")
    
    outcomes = ["home", "draw", "away"]
    per_class_ece = []
    
    print("=== Independent ECE & Brier Audit ===\n")
    
    # Calculate Brier
    preds = df[["home", "draw", "away"]].to_dict(orient="records")
    actuals = df["actual"].tolist()
    brier = calculate_brier_score(preds, actuals)
    print(f"Verified Brier Score: {brier:.5f}\n")
    
    for outcome in outcomes:
        probs = df[outcome].values
        labels = (df["actual"].str.lower().str.strip() == outcome).astype(int).values
        
        ece, mce, bin_details = calculate_ece_binary(probs, labels, num_bins=8)
        per_class_ece.append(ece)
        
        print(f"Reliability Table ({outcome.capitalize()}):")
        print("bin | count | mean_predicted_prob | empirical_frequency | abs_error")
        for bd in bin_details:
            print(f"{bd['bin']} | {bd['count']} | {bd['mean_predicted_prob']:.4f} | {bd['empirical_frequency']:.4f} | {bd['abs_error']:.4f}")
        print(f"Class ECE: {ece*100:.2f}%\n")
            
    macro_ece = np.mean(per_class_ece)
    print(f"Independent Macro ECE (8 bins): {macro_ece * 100:.2f}%")
    
if __name__ == "__main__":
    main()
