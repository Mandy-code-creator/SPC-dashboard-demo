import streamlit as st
import pandas as pd
import numpy as np

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Batch LAB Summary",
    page_icon="📦",
    layout="wide"
)

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    # 👉 CHỈ CẦN THAY ID NÀY
    GOOGLE_SHEET_ID = "PASTE_YOUR_GOOGLE_SHEET_ID_HERE"

    url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv"
    df = pd.read_csv(url)

    return df

df = load_data()

st.title("📦 Batch LAB Summary")

# =========================
# CHECK DATA
# =========================
required_cols = [
    "製造批號",
    "正-北 ΔL", "正-南 ΔL",
    "正-北 Δa", "正-南 Δa",
    "正-北 Δb", "正-南 Δb"
]

missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"❌ Thiếu cột: {missing}")
    st.stop()

# =========================
# CLEAN & CALC PER COIL
# =========================
def calc_per_coil(df):
    tmp = df[required_cols].copy()

    # drop nếu thiếu đo
    tmp = tmp.dropna()

    # mỗi cuộn = trung bình Bắc / Nam
    tmp["L"] = tmp[["正-北 ΔL", "正-南 ΔL"]].mean(axis=1)
    tmp["a"] = tmp[["正-北 Δa", "正-南 Δa"]].mean(axis=1)
    tmp["b"] = tmp[["正-北 Δb", "正-南 Δb"]].mean(axis=1)

    return tmp[["製造批號", "L", "a", "b"]]

coil_df = calc_per_coil(df)

# =========================
# BATCH SUMMARY
# =========================
batch_df = (
    coil_df
    .groupby("製造批號")
    .agg(
        coil_count=("L", "count"),

        L_mean=("L", "mean"),
        a_mean=("a", "mean"),
        b_mean=("b", "mean"),

        L_std=("L", "std"),
        a_std=("a", "std"),
        b_std=("b", "std"),

        L_min=("L", "min"),
        a_min=("a", "min"),
        b_min=("b", "min"),

        L_max=("L", "max"),
        a_max=("a", "max"),
        b_max=("b", "max"),
    )
    .round(2)
    .reset_index()
)

# =========================
# DISPLAY
# =========================
st.subheader("🔹 Batch LAB Summary Table")
st.dataframe(batch_df, use_container_width=True)

# =========================
# DEBUG (OPTIONAL)
# =========================
with st.expander("🔍 Coil level data"):
    st.dataframe(coil_df, use_container_width=True)
