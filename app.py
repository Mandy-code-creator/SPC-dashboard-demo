import streamlit as st
import pandas as pd
import numpy as np

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Batch LAB Summary",
    layout="wide"
)

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    url = "PASTE_YOUR_CSV_URL_HERE"
    return pd.read_csv(url)

df = load_data()

st.title("📦 Batch LAB Summary")

# =========================
# CLEAN & CALC PER COIL
# =========================
def calc_per_coil(df):
    tmp = df[[
        "製造批號",
        "正-北 ΔL", "正-南 ΔL",
        "正-北 Δa", "正-南 Δa",
        "正-北 Δb", "正-南 Δb"
    ]].copy()

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
        coil_count=("L", "count")
    )
    .round(2)
    .reset_index()
)

# =========================
# DISPLAY
# =========================
st.subheader("🔹 Batch LAB Table")
st.dataframe(batch_df, use_container_width=True)

# =========================
# DEBUG (OPTIONAL)
# =========================
with st.expander("🔍 Debug – coil level"):
    st.dataframe(coil_df, use_container_width=True)
