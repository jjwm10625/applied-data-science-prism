"""로지스틱 회귀 (baseline) - 7/14/21/28일 버전
실행: python train_logistic_regression.py churn_features.csv results_logistic_regression.csv
- 표준화(Train 기준 fit), C=1.0, 사용자 가중치 1/sqrt(n) 학습, 결정적이라 시드 1개
"""
import sys
from sklearn.linear_model import LogisticRegression
from common import run_model

csv, out = sys.argv[1], sys.argv[2]
run_model("LogisticRegression",
          lambda seed: LogisticRegression(C=1.0, max_iter=3000),
          csv, out, seeds=[0], scale=True)
