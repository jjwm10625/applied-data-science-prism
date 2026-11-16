"""사용자 단위 Bootstrap 신뢰구간 (train_*.py가 저장한 Test 예측 확률 사용)
실행: python bootstrap_ci.py . bootstrap_out        (모델 학습 결과 폴더, 출력 폴더)
선행: train_*.py 4개를 먼저 실행해 results_*_preds.npz 를 만들어 둔다.

한 사용자의 모든 행을 통째로 복원추출하고(같은 사용자의 행은 서로 비슷해 독립이 아니므로),
뽑힌 표본에서 AUC·PR-AUC를 계산하는 일을 B번 반복해 2.5%~97.5% 구간을 95% 신뢰구간으로 쓴다.
모델은 다시 학습하지 않는다. 같은 표본에서 모델·기간 간 차이도 계산(paired bootstrap)한다.

출력 CSV 4개
 1) bootstrap_ci.csv              모델 × 기간별 AUC·PR-AUC 95% 구간 (B=1000)
 2) bootstrap_reps.csv            반복 횟수 200·500·1000 비교 (LR, 시드 5개) - 구간 끝점이 시드마다 흔들리는 정도
 3) bootstrap_diff_versions.csv   기간 간 차이 (예: 28일 − 14일), 모델별
 4) bootstrap_diff_models.csv     모델 간 차이 (예: CatBoost − LR), 기간별
차이의 95% 구간이 0을 포함하지 않으면 '유의하다'고 본다.
"""
import itertools, os, sys
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score

IN_DIR = sys.argv[1] if len(sys.argv) > 1 else "."
OUT_DIR = sys.argv[2] if len(sys.argv) > 2 else "bootstrap_out"
B = 1000
VERSIONS = ["7", "14", "21", "28"]
MODELS = {"LogisticRegression": "logistic_regression", "RandomForest": "random_forest",
          "XGBoost": "xgboost", "CatBoost": "catboost"}
os.makedirs(OUT_DIR, exist_ok=True)


def fast_metrics(y, p):
    """AUC, PR-AUC를 정렬 한 번으로 계산 (확률이 같은 행은 한 묶음으로 처리, sklearn 값과 동일)"""
    o = np.argsort(-p, kind="stable")
    ps, ys = p[o], y[o]
    tp, fp = np.cumsum(ys), np.cumsum(1 - ys)
    cut = np.r_[np.where(np.diff(ps) != 0)[0], len(ps) - 1]      # 확률이 바뀌는 지점
    tps, fps = tp[cut], fp[cut]
    npos, nneg = ys.sum(), len(ys) - ys.sum()
    recall = tps / npos
    pr_auc = np.sum(np.diff(np.r_[0.0, recall]) * (tps / (tps + fps)))
    trapz = getattr(np, "trapezoid", None) or np.trapz      # numpy 1.x/2.x 모두 지원
    auc = trapz(np.r_[0.0, tps / npos], np.r_[0.0, fps / nneg])
    return auc, pr_auc


# ---- 예측 확률 읽기
P, y, user = {}, None, None
for name, f in MODELS.items():
    z = np.load(os.path.join(IN_DIR, f"results_{f}_preds.npz"), allow_pickle=True)
    y, user = z["y"].astype(int), z["user"]
    for v in VERSIONS:
        P[(name, v)] = z[v]

# 정확성 확인: 빠른 계산 vs sklearn
for key in [("LogisticRegression", "28"), ("CatBoost", "7")]:
    a, b = fast_metrics(y, P[key])
    assert abs(a - roc_auc_score(y, P[key])) < 1e-6 and abs(b - average_precision_score(y, P[key])) < 1e-6, key

groups = pd.Series(np.arange(len(user))).groupby(user).apply(lambda s: s.values)
users = groups.index.values


def draw(rng):
    return np.concatenate([groups[u] for u in rng.choice(users, len(users), replace=True)])


def pct(a):
    return np.percentile(a, [2.5, 97.5])


# ---- 1) 모델 × 기간별 신뢰구간, 3)·4) 차이 (같은 표본 사용)
rng = np.random.default_rng(0)
AUC = {k: [] for k in P}
PRA = {k: [] for k in P}
for i in range(B):
    idx = draw(rng)
    yi = y[idx]
    for k, p in P.items():
        a, r = fast_metrics(yi, p[idx])
        AUC[k].append(a)
        PRA[k].append(r)
    if (i + 1) % 100 == 0:
        print(f"bootstrap {i + 1}/{B}", flush=True)
AUC = {k: np.array(v) for k, v in AUC.items()}
PRA = {k: np.array(v) for k, v in PRA.items()}
point = {k: (roc_auc_score(y, p), average_precision_score(y, p)) for k, p in P.items()}

rows = []
for (m, v) in P:
    a0, a1 = pct(AUC[(m, v)])
    r0, r1 = pct(PRA[(m, v)])
    rows.append(dict(버전=f"{v}일", 모델=m, AUC=point[(m, v)][0], AUC_하한=a0, AUC_상한=a1,
                     PR_AUC=point[(m, v)][1], PR_AUC_하한=r0, PR_AUC_상한=r1))
pd.DataFrame(rows).round(4).to_csv(f"{OUT_DIR}/bootstrap_ci.csv", index=False, encoding="utf-8-sig")


def diff_row(label_cols, ka, kb):
    out = dict(label_cols)
    for nm, D, j in (("AUC", AUC, 0), ("PR_AUC", PRA, 1)):
        d = D[ka] - D[kb]
        lo, hi = pct(d)
        out.update({f"{nm}_차이": point[ka][j] - point[kb][j], f"{nm}_하한": lo, f"{nm}_상한": hi,
                    f"{nm}_0포함": "예" if lo <= 0 <= hi else "아니오"})
    return out


rows = []
for m in MODELS:
    for a, b in itertools.combinations(VERSIONS, 2):                       # 긴 기간 − 짧은 기간
        rows.append(diff_row(dict(모델=m, 비교=f"{b}일 − {a}일"), (m, b), (m, a)))
pd.DataFrame(rows).round(4).to_csv(f"{OUT_DIR}/bootstrap_diff_versions.csv", index=False, encoding="utf-8-sig")

rows = []
pairs = [("CatBoost", "LogisticRegression"), ("XGBoost", "LogisticRegression"),
         ("RandomForest", "LogisticRegression"), ("CatBoost", "XGBoost")]
for v in VERSIONS:
    for a, b in pairs:
        rows.append(diff_row(dict(버전=f"{v}일", 비교=f"{a} − {b}"), (a, v), (b, v)))
pd.DataFrame(rows).round(4).to_csv(f"{OUT_DIR}/bootstrap_diff_models.csv", index=False, encoding="utf-8-sig")

# ---- 2) 반복 횟수 비교 (로지스틱 회귀, 시드 5개): 시드마다 1000회를 뽑고 앞 200 / 500 / 1000회로 구간 계산
rows = []
for v in VERSIONS:
    p = P[("LogisticRegression", v)]
    for seed in range(5):
        rng = np.random.default_rng(100 + seed)
        a_list, r_list = [], []
        for _ in range(B):
            idx = draw(rng)
            a, r = fast_metrics(y[idx], p[idx])
            a_list.append(a)
            r_list.append(r)
        a_list, r_list = np.array(a_list), np.array(r_list)
        for nb in (200, 500, 1000):
            a0, a1 = pct(a_list[:nb])
            r0, r1 = pct(r_list[:nb])
            rows.append(dict(버전=f"{v}일", B=nb, 시드=seed, AUC_하한=a0, AUC_상한=a1, AUC_폭=a1 - a0,
                             PR_AUC_하한=r0, PR_AUC_상한=r1, PR_AUC_폭=r1 - r0))
    print(f"반복 횟수 비교 {v}일 완료", flush=True)
pd.DataFrame(rows).round(5).to_csv(f"{OUT_DIR}/bootstrap_reps.csv", index=False, encoding="utf-8-sig")
s = pd.DataFrame(rows).groupby(["버전", "B"]).agg(AUC_하한_시드SD=("AUC_하한", "std"), AUC_상한_시드SD=("AUC_상한", "std"),
                                                AUC_폭=("AUC_폭", "mean"), PR_AUC_폭=("PR_AUC_폭", "mean")).round(5)
print(s.to_string())
print(f"저장: {OUT_DIR}/ (CSV 4개)")
