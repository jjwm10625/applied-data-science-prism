"""XGBoost - 7/14/21/28일 버전 (튜닝 전 기본 설정)
실행: python train_xgboost.py churn_features.csv results_xgboost.csv   (pip install xgboost)
- 300그루, 깊이 4, learning_rate 0.05, subsample·colsample 0.8, min_child_weight 20, 시드 5개
"""
import sys
from xgboost import XGBClassifier
from common import run_model, SEEDS

csv, out = sys.argv[1], sys.argv[2]
run_model("XGBoost",
          lambda seed: XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.8,
                                     colsample_bytree=0.8, min_child_weight=20, tree_method="hist",
                                     n_jobs=-1, random_state=seed, verbosity=0),
          csv, out, seeds=SEEDS)
