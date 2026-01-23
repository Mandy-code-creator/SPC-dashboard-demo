import streamlit as st
import pandas as pd
import numpy as np
import urllib.request
from io import BytesIO

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Batch LAB Summary",
    page_icon="📦",
    layout="wide"
)

st.title("📦 Batch LAB Summary")

# =========================
# DATA SOURCE SELECT
# =========================
st.sidebar.header("📥 Data source")

source = st.sidebar.radio(
    "Choose data source",
    ["Google Sheet", "Upload CSV"]
)

# =========================
# LOAD FROM GOOGLE SHEET
# =========================
@st.cache_data
def load_from_google(sheet_id, gid):
    url = (
        f"https://docs.google.com/spreadsheets/d/"
        f"{sheet_id}/export?format=csv&gid={gid}"
    )

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(req) as response:
        df = pd.read_csv(response)

    return df


df = None

if source == "Google Sheet":
    sheet_id = st.sidebar.text_input(
        "Google Sheet ID",
        placeholder="ví dụ: 1lqsLKSoDTbtvAsH..."
    )
    gid = st.sidebar.text_input(
        "Sheet GID",
        value="0"
    )

    if sheet_id:
        try:
            df = load_from_google(sheet_id, gid)
            st.success("✅ Load Google Sheet thành công")
        except Exception as e:
            st.error("❌ Không load được Google Sheet")
            st.info("👉 Kiểm tra lại ID / GID hoặc dùng Upload CSV")
            st.exception(e)

# =========================
# LOAD FROM CSV UPLOAD
# =========================
if source == "Upload CSV":
    uploaded = st.sidebar.file_uploader(
        "Upload CSV file",
        type=["csv"]
    )
    if uploaded:
        df = pd.read_csv(uploaded)
        st.success("✅ CSV loaded successfully")

# =========================
# STOP IF NO DATA
# =========================
if df is None:
    st.warning("⬅️ Chọn nguồn dữ liệu để bắt đầu")
    st.stop()

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
# CALC PER COIL
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
