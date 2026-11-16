"""CatBoost - 7/14/21/28일 버전 (튜닝 전 기본 설정)
실행: python train_catboost.py churn_features.csv results_catboost.csv   (pip install catboost)
- 400회, 깊이 6, learning_rate 0.05, 시드 5개
"""
import sys
from catboost import CatBoostClassifier
from common import run_model, SEEDS

csv, out = sys.argv[1], sys.argv[2]
run_model("CatBoost",
          lambda seed: CatBoostClassifier(iterations=400, depth=6, learning_rate=0.05,
                                          random_seed=seed, thread_count=-1, verbose=0),
          csv, out, seeds=SEEDS)
