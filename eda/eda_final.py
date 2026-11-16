"""탐색적 데이터 분석(EDA) - 하이링구얼 이탈 예측 데이터 (churn_features.csv)
실행: python eda.py churn_features.csv eda_out
출력(eda_out/): 그림 PNG 6개, 요약 CSV 여러 개, eda_summary.txt(핵심 수치 모음)

점검 항목
 1. 기본 정보      행·사용자 수, 기간, 결측, (사용자, 기준일) 중복
 2. 라벨·분할      이탈 비율(전체·월별·Train/Val/Test)
 3. 시간 추이      주별 행·사용자 수, 이탈 비율, 활동 대비 이벤트 수 (기록 방식 변경 8/17, 8/30 표시)
 4. 사용자별 행 수  한 사용자가 여러 행을 갖는 정도 (사용자 단위 평가·가중치의 근거)
 5. 피처 분포      28일 피처 분포, 이상치
 6. 0 비율·상관    피처별 0 비율(월별), 상관관계
 7. 윈도우 정의    관측 윈도우(7/14/21/28일)별 recency 윈도우 밖 비율·이탈 비율 (recency_윈도우밖 지시 변수의 근거)
 8. 라벨과의 관계  활동일·최근 접속일·유입(entry_days)별 이탈 비율
 9. 정합성 검사    누적 윈도우 단조성, 활동일 상한, active_days = app_usage_days 일치율
"""
import os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

CSV = sys.argv[1] if len(sys.argv) > 1 else "churn_features.csv"
OUT = sys.argv[2] if len(sys.argv) > 2 else "eda_out"
os.makedirs(OUT, exist_ok=True)

# 한글 폰트 (설치된 것 중 첫 번째 사용, 없으면 기본 폰트)
import glob
for p in glob.glob("/usr/share/fonts/**/Nanum*Gothic*.ttf", recursive=True):   # Colab: apt로 설치한 나눔고딕 직접 등록
    font_manager.fontManager.addfont(p)
for name in ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR", "Noto Sans CJK JP"]:
    if any(name == f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = name
        break
else:
    print("경고: 한글 폰트를 찾지 못했습니다. 그림의 한글이 깨집니다. (Colab: 0번 셀 실행 후 런타임 > 세션 다시 시작)")
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 110})

Y = "churn_label"
SPLIT = {"Train": ("2026-01-01", "2026-05-24"), "Val": ("2026-06-08", "2026-07-08"), "Test": ("2026-07-23", "2026-10-12")}
EVENTS = {"2026-08-10": "entry_days 기록 시작", "2026-08-17": "푸시·화면추적 이벤트 추가", "2026-08-30": "위젯 추가"}
BASES = ["event_count", "session_count", "diary_count", "vocabulary_count", "pronunciation_count",
         "social_count", "active_days", "entry_days", "learning_days", "app_usage_days"]
WIN = [7, 14, 21, 28]
lines = []


def say(s=""):
    print(s)
    lines.append(str(s))


def save(fig, name):
    fig.tight_layout()
    fig.savefig(f"{OUT}/{name}", dpi=130)
    plt.close(fig)


def shade_splits(ax):
    for (k, (a, b)), c in zip(SPLIT.items(), ["#dbeafe", "#fef3c7", "#dcfce7"]):
        ax.axvspan(pd.Timestamp(a), pd.Timestamp(b), color=c, alpha=0.6, lw=0)


def mark_events(ax, ytext=None):
    for d, lab in EVENTS.items():
        ax.axvline(pd.Timestamp(d), color="#b91c1c", ls="--", lw=1)
        ax.text(pd.Timestamp(d), ax.get_ylim()[1], lab, rotation=90, va="top", ha="right", fontsize=8, color="#b91c1c")


df = pd.read_csv(CSV, parse_dates=["reference_date"])
N_COLS = df.shape[1]
df["month"] = df.reference_date.dt.to_period("M").astype(str)
df["week"] = df.reference_date.dt.to_period("W").dt.start_time

# ---------------- 1. 기본 정보
say("=" * 60 + "\n1. 기본 정보")
say(f"행 {len(df):,} · 열 {N_COLS} · 사용자 {df.user_id.nunique():,}")
say(f"기준일 {df.reference_date.min().date()} ~ {df.reference_date.max().date()}")
miss = df.isna().sum()
say(f"결측치가 있는 열: {int((miss > 0).sum())}개" + ("" if (miss > 0).sum() == 0 else f"\n{miss[miss > 0].to_string()}"))
say(f"(사용자, 기준일) 중복 행: {int(df.duplicated(['user_id', 'reference_date']).sum())}")
df.describe().T.round(3).to_csv(f"{OUT}/describe.csv", encoding="utf-8-sig")

# ---------------- 2. 라벨·분할
say("\n" + "=" * 60 + "\n2. 라벨·분할")
say(f"전체 이탈 비율 {df[Y].mean():.4f}")
rows = []
for k, (a, b) in SPLIT.items():
    s = df[(df.reference_date >= a) & (df.reference_date <= b)]
    rows.append(dict(구간=k, 시작=a, 끝=b, 행=len(s), 사용자=s.user_id.nunique(), 이탈비율=round(s[Y].mean(), 4)))
sp = pd.DataFrame(rows)
sp.to_csv(f"{OUT}/split_summary.csv", index=False, encoding="utf-8-sig")
say(sp.to_string(index=False))
monthly = df.groupby("month").agg(행=(Y, "size"), 사용자=("user_id", "nunique"), 이탈비율=(Y, "mean")).round(4)
monthly.to_csv(f"{OUT}/monthly_summary.csv", encoding="utf-8-sig")
say("\n월별 행·사용자·이탈 비율\n" + monthly.to_string())
say("→ 이탈 비율이 약 80%로 불균형. 모두 이탈로 예측해도 정확도가 이탈 비율만큼 나오므로 F1·정확도만으로는 모델을 구분하기 어렵다.")

# ---------------- 3. 시간 추이 (그림 A)
wk = df.groupby("week").agg(행=(Y, "size"), 사용자=("user_id", "nunique"), 이탈비율=(Y, "mean"))
act = df[df.active_days_7d > 0].assign(per_day=lambda x: x.event_count_7d / x.active_days_7d)
wk_ev = act.groupby("week").per_day.agg(["median", "mean"])
fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
for ax, col, ttl in zip(axes[:2], ["사용자", "이탈비율"], ["주별 사용자 수", "주별 이탈 비율"]):
    ax.plot(wk.index, wk[col], color="#1d4ed8", lw=1.8)
    shade_splits(ax)
    ax.set_title(ttl, loc="left", fontsize=11)
axes[1].set_ylim(0.6, 1.0)
axes[2].plot(wk_ev.index, wk_ev["median"], color="#047857", lw=1.8, label="중앙값")
axes[2].plot(wk_ev.index, wk_ev["mean"], color="#9ca3af", lw=1.2, label="평균")
axes[2].set_title("활동한 날 하루당 이벤트 수 (event_count_7d / active_days_7d)", loc="left", fontsize=11)
axes[2].legend(frameon=False)
shade_splits(axes[2])
for ax in axes:
    mark_events(ax)
fig.suptitle("A. 시간 추이  (파랑=Train, 노랑=Val, 초록=Test, 빨강=기록 방식 변경)", y=1.0)
save(fig, "A_time.png")
wk.join(wk_ev).round(4).to_csv(f"{OUT}/weekly_summary.csv", encoding="utf-8-sig")

say("\n" + "=" * 60 + "\n3. 기록 방식 변경 전후 비교")
for d in ["2026-08-17", "2026-08-30"]:
    b, a = act[(act.reference_date < d) & (act.reference_date >= pd.Timestamp(d) - pd.Timedelta(days=28))], \
           act[(act.reference_date >= d) & (act.reference_date < pd.Timestamp(d) + pd.Timedelta(days=28))]
    say(f"{d} 전후 4주  활동일당 이벤트 중앙값 {b.per_day.median():.2f} → {a.per_day.median():.2f}, "
        f"active_days_7d 평균 {b.active_days_7d.mean():.2f} → {a.active_days_7d.mean():.2f}, "
        f"이탈 비율(최근 7일 활동 행 기준) {b[Y].mean():.3f} → {a[Y].mean():.3f}")
say("→ 기록 방식이 바뀌어도 활동일당 이벤트 수(중앙값)·active_days·이탈 비율이 크게 변하지 않으면 영향이 작다고 본다. (평균은 소수 헤비유저에 민감해 중앙값으로 비교)")

# ---------------- 4. 사용자별 행 수 (그림 D)
say("\n" + "=" * 60 + "\n4. 사용자별 행 수")
n = df.groupby("user_id").size().sort_values(ascending=False)
say(f"사용자당 행 수  평균 {n.mean():.1f} · 중앙값 {n.median():.0f} · 최대 {n.max()}")
say(f"상위 1% 사용자({int(len(n) * 0.01)}명)가 전체 행의 {n.head(int(len(n) * 0.01)).sum() / len(df):.1%}, "
    f"상위 10%가 {n.head(int(len(n) * 0.1)).sum() / len(df):.1%}")
n.rename("행수").to_csv(f"{OUT}/rows_per_user.csv", encoding="utf-8-sig")
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
axes[0].hist(n, bins=60, color="#1d4ed8")
axes[0].set_yscale("log")
axes[0].set_title("사용자별 행 수 분포 (y 로그)", loc="left")
axes[0].set_xlabel("행 수")
cum = n.cumsum().values / n.sum()
axes[1].plot(np.arange(1, len(n) + 1) / len(n), cum, color="#b91c1c")
axes[1].plot([0, 1], [0, 1], color="#9ca3af", ls="--")
axes[1].set_title("누적 비중: 행이 많은 사용자부터", loc="left")
axes[1].set_xlabel("사용자 비율")
axes[1].set_ylabel("행 비율")
save(fig, "D_rows_per_user.png")
say("→ 소수 사용자가 많은 행을 차지하므로 학습 가중치(1/√n)와 사용자 단위 Bootstrap이 필요하다.")

# ---------------- 5. 피처 분포 (그림 B)
say("\n" + "=" * 60 + "\n5. 피처 분포 (28일)")
cols = [f"{b}_28d" for b in BASES] + ["recency_days"]
fig, axes = plt.subplots(3, 4, figsize=(14, 9))
for ax, c in zip(axes.ravel(), cols):
    v = df[c]
    ax.hist(np.log1p(v), bins=50, color="#1d4ed8")
    ax.set_yscale("log")
    ax.set_title(f"{c}  (0 비율 {np.mean(v == 0):.0%})", loc="left", fontsize=9)
    ax.set_xlabel("log1p(값)", fontsize=8)
for ax in axes.ravel()[len(cols):]:
    ax.axis("off")
fig.suptitle("B. 피처 분포 (log1p, y 로그)", y=1.0)
save(fig, "B_features.png")
q = df[cols].quantile([0.5, 0.9, 0.99, 1.0]).T
q.columns = ["중앙값", "90%", "99%", "최대"]
q.round(2).to_csv(f"{OUT}/feature_quantiles.csv", encoding="utf-8-sig")
say(q.round(1).to_string())
say("→ 횟수형 피처는 오른쪽으로 긴 꼬리를 가져 log1p 변환이 필요하다.")

# ---------------- 6. 0 비율 (월별) · 상관 (그림 C)
z = pd.DataFrame({c: (df[c] == 0).groupby(df.month).mean() for c in [f"{b}_28d" for b in BASES]}).T
z.round(3).to_csv(f"{OUT}/zero_ratio_by_month.csv", encoding="utf-8-sig")
sample = df.sample(min(150_000, len(df)), random_state=0)
corr = sample[[f"{b}_28d" for b in BASES if b != "entry_days"] + ["recency_days", Y]].corr(method="spearman")
corr.round(3).to_csv(f"{OUT}/spearman_corr.csv", encoding="utf-8-sig")
fig, axes = plt.subplots(1, 2, figsize=(15, 5.5), gridspec_kw={"width_ratios": [1.2, 1]})
im = axes[0].imshow(z.values, aspect="auto", cmap="Blues", vmin=0, vmax=1)
axes[0].set_xticks(range(len(z.columns)))
axes[0].set_xticklabels(z.columns, rotation=60, fontsize=8)
axes[0].set_yticks(range(len(z.index)))
axes[0].set_yticklabels(z.index, fontsize=8)
axes[0].set_title("월별 0 비율 (진할수록 0이 많음)", loc="left")
fig.colorbar(im, ax=axes[0], fraction=0.03)
im2 = axes[1].imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
axes[1].set_xticks(range(len(corr)))
axes[1].set_xticklabels(corr.columns, rotation=75, fontsize=8)
axes[1].set_yticks(range(len(corr)))
axes[1].set_yticklabels(corr.columns, fontsize=8)
axes[1].set_title("Spearman 상관 (entry_days 제외)", loc="left")
fig.colorbar(im2, ax=axes[1], fraction=0.04)
save(fig, "C_zero_corr.png")
say("\n" + "=" * 60 + "\n6. 0 비율·상관")
say(f"entry_days_28d가 0이 아닌 첫 기준일: {df.loc[df.entry_days_28d > 0, 'reference_date'].min().date()} "
    f"(그 이전 0 비율 {np.mean(df.loc[df.reference_date < '2026-08-10', 'entry_days_28d'] == 0):.0%})")
c_y = corr[Y].drop(Y).sort_values(key=abs, ascending=False)
say("이탈 라벨과의 Spearman 상관 (절댓값 큰 순)\n" + c_y.round(3).to_string())
hi = corr.drop(index=Y, columns=Y).where(np.triu(np.ones((len(corr) - 1,) * 2), 1).astype(bool)).stack()
say("피처끼리 상관이 0.9 이상인 쌍\n" + (hi[hi.abs() >= 0.9].round(3).to_string() if (hi.abs() >= 0.9).any() else "없음"))

# ---------------- 7. 윈도우 정의 (그림 F)
# 윈도우 N일: 기준일 직전 N일. recency_days > N 이면 그 윈도우 안에 활동이 없다 -> recency를 결측 처리하고
# 지시 변수(recency_윈도우밖)를 둔다. 그 비율과 이탈 비율을 확인한다.
rows = []
for w in WIN:
    out = df.recency_days > w
    rows.append(dict(윈도우=f"{w}일", 윈도우밖_비율=out.mean(),
                     윈도우밖_이탈비율=df.loc[out, Y].mean() if out.any() else np.nan,
                     윈도우안_이탈비율=df.loc[~out, Y].mean(),
                     윈도우밖_active_days0_비율=np.mean(df.loc[out, f"active_days_{w}d"] == 0) if out.any() else np.nan,
                     윈도우안_active_days0_비율=np.mean(df.loc[~out, f"active_days_{w}d"] == 0)))
wdef = pd.DataFrame(rows)
wdef.round(4).to_csv(f"{OUT}/window_definition.csv", index=False, encoding="utf-8-sig")
say("\n" + "=" * 60 + "\n7. 윈도우 정의")
say(wdef.round(3).to_string(index=False))
tr_ = df[(df.reference_date >= SPLIT["Train"][0]) & (df.reference_date <= SPLIT["Train"][1])]
say("recency 채움값(Train에서 윈도우 안 행의 평균 recency_days): " +
    ", ".join(f"{w}일 {tr_.loc[tr_.recency_days <= w, 'recency_days'].mean():.2f}" for w in WIN))
say("→ 윈도우가 짧을수록 '윈도우 밖' 행이 많고 이탈 비율이 높다. recency를 윈도우 안에서만 정의하고 "
    "밖은 결측 + 지시 변수로 표현했다. 윈도우 밖 행의 active_days가 0이 아니면 정의 오류이므로 0인지 함께 확인한다.")
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
xs = np.arange(len(WIN))
axes[0].bar(xs, wdef.윈도우밖_비율, color="#1d4ed8")
axes[0].set_xticks(xs)
axes[0].set_xticklabels(wdef.윈도우)
axes[0].set_ylim(0, 1)
axes[0].set_title("윈도우 밖 행 비율 (recency_days > N)", loc="left")
axes[1].bar(xs - 0.2, wdef.윈도우안_이탈비율, 0.4, color="#047857", label="윈도우 안")
axes[1].bar(xs + 0.2, wdef.윈도우밖_이탈비율, 0.4, color="#b91c1c", label="윈도우 밖")
axes[1].set_xticks(xs)
axes[1].set_xticklabels(wdef.윈도우)
axes[1].set_ylim(0, 1.2)
axes[1].legend(frameon=False, ncol=2, loc="upper left")
axes[1].set_title("윈도우 안/밖 이탈 비율", loc="left")
save(fig, "F_window_definition.png")

# ---------------- 8. 라벨과의 관계 (그림 E)
fig, axes = plt.subplots(1, 3, figsize=(14, 4))
t = df.groupby(df.active_days_28d.clip(upper=20))[Y].agg(["mean", "size"])
axes[0].bar(t.index, t["mean"], color="#1d4ed8")
axes[0].set_title("활동일(28일)별 이탈 비율", loc="left")
axes[0].set_xlabel("active_days_28d (20 이상 묶음)")
axes[0].set_xticks(range(0, 21, 5))
axes[0].set_ylim(0, 1)
t2 = df.groupby(df.recency_days.clip(upper=28).round())[Y].mean()
axes[1].plot(t2.index, t2.values, marker="o", color="#047857")
axes[1].set_title("최근 접속 후 경과일별 이탈 비율", loc="left")
axes[1].set_xlabel("recency_days (28 이상 묶음)")
axes[1].set_ylim(0, 1)
late = df[df.reference_date >= "2026-08-10"]
t3 = late.groupby(late.entry_days_28d.clip(upper=5))[Y].agg(["mean", "size"])
axes[2].bar(t3.index.astype(int).astype(str), t3["mean"], color="#b45309")
axes[2].set_title("유입일(28일)별 이탈 비율 (8/10 이후만)", loc="left")
axes[2].set_xlabel("entry_days_28d (5 이상 묶음)")
axes[2].set_ylim(0, 1)
save(fig, "E_label_relation.png")
say("\n" + "=" * 60 + "\n8. 라벨과의 관계")
say("활동일(28일)별 이탈 비율 (1·2·3일 이상; 최근 28일 활동이 있는 행만 데이터에 포함됨)\n" + df.groupby(df.active_days_28d.clip(upper=3))[Y].mean().round(3).to_string())
say(f"entry_days_28d>0 (8/10 이후) 행 {int((late.entry_days_28d > 0).sum()):,}개, 이탈 비율 "
    f"{late.loc[late.entry_days_28d > 0, Y].mean():.3f} vs 0인 행 {late.loc[late.entry_days_28d == 0, Y].mean():.3f}")
say("→ entry_days는 이탈과 강한 관계가 보이지만 8/10 이전에는 값이 없어 Train에서 학습할 수 없다.")

# ---------------- 9. 정합성 검사
say("\n" + "=" * 60 + "\n9. 정합성 검사")
chk = []
for b in BASES:
    for a, c in zip(WIN[:-1], WIN[1:]):
        chk.append(dict(검사=f"{b}: {a}일 ≤ {c}일 (누적)", 위반행=int((df[f"{b}_{a}d"] > df[f"{b}_{c}d"]).sum())))
for w in WIN:
    chk.append(dict(검사=f"active_days_{w}d ≤ {w}", 위반행=int((df[f"active_days_{w}d"] > w).sum())))
    chk.append(dict(검사=f"learning_days_{w}d ≤ active_days_{w}d", 위반행=int((df[f"learning_days_{w}d"] > df[f"active_days_{w}d"]).sum())))
    chk.append(dict(검사=f"recency_days > {w}이면 active_days_{w}d = 0", 위반행=int(((df.recency_days > w) & (df[f"active_days_{w}d"] > 0)).sum())))
chk = pd.DataFrame(chk)
chk.to_csv(f"{OUT}/consistency_checks.csv", index=False, encoding="utf-8-sig")
bad = chk[chk.위반행 > 0]
say(f"검사 {len(chk)}개 중 위반이 있는 검사: {len(bad)}개" + ("" if bad.empty else "\n" + bad.to_string(index=False)))
for w in WIN:
    say(f"active_days_{w}d == app_usage_days_{w}d 비율 {np.mean(df[f'active_days_{w}d'] == df[f'app_usage_days_{w}d']):.2%}")
say("→ app_usage_days는 active_days와 거의 같아 모델 입력에서 제외했다.")

with open(f"{OUT}/eda_summary.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
say(f"\n저장: {OUT}/ (PNG 6개 + CSV + eda_summary.txt)")
