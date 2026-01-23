import streamlit as st
import pandas as pd
import numpy as np
import urllib.request

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Batch LAB Summary",
    page_icon="📦",
    layout="wide"
)

# =========================
# LOAD DATA (ROBUST)
# =========================
@st.cache_data
def load_data():
    GOOGLE_SHEET_ID = "PASTE_YOUR_GOOGLE_SHEET_ID_HERE"
    GID = "0"   # 👈 nếu không phải sheet đầu, đổi số này

    url = (
        f"https://docs.google.com/spreadsheets/d/"
        f"{GOOGLE_SHEET_ID}/export?format=csv&gid={GID}"
    )

    # 👉 Bypass Google HTTP block
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(req) as response:
        df = pd.read_csv(response)

    return df


# =========================
# MAIN
# =========================
try:
    df = load_data()
except Exception as e:
    st.error("❌ Không thể load Google Sheet")
    st.info("👉 Kiểm tra: Share sheet + đúng GID")
    st.exception(e)
    st.stop()

st.title("📦 Batch LAB Summary")

# =========================
# REQUIRED COLUMNS
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
    tmp = tmp.dropna()

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
st.subheader("🔹 Batch LAB Summary")
st.dataframe(batch_df, use_container_width=True)

with st.expander("🔍 Coil-level data"):
    st.dataframe(coil_df, use_container_width=True)
