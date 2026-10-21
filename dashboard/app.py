"""Read local aggregate evaluations and predictions; never train on page load."""

from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
st.set_page_config(page_title="프리즘", layout="wide")
st.title("프리즘 · HiLingual")
st.caption("수집 안정성을 가정한 향후 7일 활동 미관측 대리 라벨 분석")
base = Path(st.sidebar.text_input("평가 결과 폴더", str(ROOT / "results/evaluation")))
metric = base / "metrics.csv"
if metric.exists():
    data = pd.read_csv(metric)
    split = st.selectbox("평가 구간", sorted(data.split.unique()))
    view = data[data.split.eq(split)]
    st.dataframe(view)
    st.line_chart(view.groupby(["window_days", "model"]).f1.mean().unstack("model"))
    calibration = base / "calibration.csv"
    if calibration.exists():
        st.dataframe(pd.read_csv(calibration))
else:
    st.info("평가를 실행한 뒤 결과 폴더를 선택하세요.")
pred = st.sidebar.text_input("예측 CSV 경로 (선택)", "")
if pred and Path(pred).is_file():
    f = pd.read_csv(pred)
    st.metric("예측 표본", len(f))
    counts = pd.cut(
        f.probability, [0, 0.2, 0.4, 0.6, 0.8, 1], include_lowest=True
    ).value_counts(sort=False)
    counts.index = counts.index.astype(str)
    st.bar_chart(counts)
    st.caption("사용자 키는 기본 화면에 표시하지 않습니다.")
