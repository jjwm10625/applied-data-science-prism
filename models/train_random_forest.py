"""RandomForest - 7/14/21/28일 버전 (튜닝 전 기본 설정)
실행: python train_random_forest.py churn_features.csv results_random_forest.csv
- 200그루, 최소 잎 50, max_features=sqrt, max_samples=0.5, 시드 5개
"""
import sys
from sklearn.ensemble import RandomForestClassifier
from common import run_model, SEEDS

csv, out = sys.argv[1], sys.argv[2]
run_model("RandomForest",
          lambda seed: RandomForestClassifier(n_estimators=200, min_samples_leaf=50, max_features="sqrt",
                                              max_samples=0.5, n_jobs=-1, random_state=seed),
          csv, out, seeds=SEEDS)
