"""공통 모듈: 데이터 로드·시간순 분할, 피처 생성, 평가 (모든 모델 스크립트가 사용)"""
import numpy as np
import pandas as pd
from sklearn.metrics import (roc_auc_score, average_precision_score, f1_score, accuracy_score,
                             balanced_accuracy_score, precision_score, recall_score, brier_score_loss)

Y = "churn_label"
WINDOWS = [7, 14, 21, 28]
SEEDS = [0, 1, 2, 3, 4]
DAYS = ["active_days", "learning_days"]
COUNTS = ["diary_count", "vocabulary_count", "pronunciation_count", "social_count", "session_count"]
# 제외: event_count(기록 방식에 민감), app_usage_days(active_days와 거의 동일), entry_days(학습 구간에 값 없음)
SPLIT = {                                   # 경계마다 7일 purge
    "train": ("2026-01-01", "2026-05-24"),
    "val":   ("2026-06-08", "2026-07-08"),
    "test":  ("2026-07-23", "2026-10-12"),
}


def load(csv_path):
    df = pd.read_csv(csv_path, parse_dates=["reference_date"])
    return {k: df[(df.reference_date >= a) & (df.reference_date <= b)].copy() for k, (a, b) in SPLIT.items()}


def block_value(d, col, w):
    """(w-7, w] 구간 값 = 누적(w) - 누적(w-7)"""
    cur = d[f"{col}_{w}d"]
    return cur if w == 7 else cur - d[f"{col}_{w - 7}d"]


def build_features(d, N, fill_rec):
    X = pd.DataFrame(index=d.index)
    for w in [x for x in WINDOWS if x <= N]:
        for c in DAYS + COUNTS:
            v = block_value(d, c, w)
            X[f"{c}_{w}b"] = np.log1p(v) if c in COUNTS else v
        act, lrn = block_value(d, "active_days", w), block_value(d, "learning_days", w)
        X[f"learning_ratio_{w}"] = np.where(act > 0, lrn / act.replace(0, np.nan), 0.0)
    r = d["recency_days"].where(d["recency_days"] <= N)          # N 초과 -> 결측
    X["recency_윈도우밖"] = r.isna().astype(int)
    X["recency_log"] = np.log1p(r).fillna(np.log1p(fill_rec))   # 채움값은 Train 평균
    return X


def prepare(part, N):
    """한 버전(N일)의 Train/Val/Test 피처와 학습 가중치"""
    tr, va, te = part["train"], part["val"], part["test"]
    fill = tr.loc[tr.recency_days <= N, "recency_days"].mean()
    Xtr, Xva, Xte = (build_features(d, N, fill) for d in (tr, va, te))
    return Xtr, Xva, Xte, user_weights(tr)


def user_weights(d, power=0.5):
    """사용자별 1/sqrt(n) 가중치 (n = 그 사용자의 행 수), 평균 1로 정규화"""
    n = d.groupby("user_id")["user_id"].transform("size")
    w = 1.0 / n ** power
    return (w * len(d) / w.sum()).values


def best_threshold(y, p):
    """Val에서 F1이 최대인 임계값"""
    grid = np.linspace(0.30, 0.95, 66)
    return grid[int(np.argmax([f1_score(y, p >= t) for t in grid]))]


def prec_at(y, p, frac):
    k = int(len(p) * frac)
    return y[np.argsort(-p)[:k]].mean()


def evaluate(y, p, th):
    yh = (p >= th).astype(int)
    return dict(AUC=roc_auc_score(y, p), PR_AUC=average_precision_score(y, p),
                F1=f1_score(y, yh), Precision=precision_score(y, yh, zero_division=0),
                Recall=recall_score(y, yh), Accuracy=accuracy_score(y, yh),
                BalancedAcc=balanced_accuracy_score(y, yh), Brier=brier_score_loss(y, p),
                Prec_top20=prec_at(y, p, 0.2), Prec_top10=prec_at(y, p, 0.1))


def run_model(model_name, make_model, csv_path, out_csv, seeds, scale=False, use_sample_weight=True):
    """모든 버전·시드에 대해 학습 -> Val 임계값 -> Test 평가. 결과 CSV와 예측 확률(npz) 저장"""
    import time
    from sklearn.preprocessing import StandardScaler
    part = load(csv_path)
    va, te = part["val"], part["test"]
    yv, y = va[Y].values, te[Y].values
    rows, preds = [], {}
    for N in WINDOWS:
        Xtr, Xva, Xte, sw = prepare(part, N)
        if scale:
            sc = StandardScaler().fit(Xtr)
            Xtr, Xva, Xte = sc.transform(Xtr), sc.transform(Xva), sc.transform(Xte)
        ps = []
        for s in seeds:
            t0 = time.time()
            m = make_model(s)
            m.fit(Xtr, part["train"][Y], sample_weight=sw if use_sample_weight else None)
            pv, pt = m.predict_proba(Xva)[:, 1], m.predict_proba(Xte)[:, 1]
            th = best_threshold(yv, pv)
            rows.append(dict(버전=f"{N}일", 모델=model_name, 시드=s, 임계값=round(th, 3), **evaluate(y, pt, th)))
            ps.append(pt)
            print(f"{N}일 {model_name} seed{s} AUC={rows[-1]['AUC']:.4f} PR-AUC={rows[-1]['PR_AUC']:.4f} "
                  f"F1={rows[-1]['F1']:.4f} ({time.time() - t0:.0f}s)", flush=True)
        preds[f"{N}"] = np.mean(ps, axis=0)
    res = pd.DataFrame(rows)
    res[res.select_dtypes("number").columns] = res.select_dtypes("number").round(4)
    res.to_csv(out_csv, index=False, encoding="utf-8-sig")
    np.savez(out_csv.replace(".csv", "_preds.npz"), y=y, user=te.user_id.values, **preds)
    print(res.groupby("버전")[["AUC", "PR_AUC", "F1", "BalancedAcc", "Brier", "Prec_top20"]].mean().round(4).to_string())
    print(f"저장: {out_csv}")
