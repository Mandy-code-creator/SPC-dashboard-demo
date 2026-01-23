import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import io
import urllib.request
from scipy.stats import norm

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="SPC Color Dashboard",
    page_icon="🎨",
    layout="wide"
)

# =========================
# STYLE
# =========================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(270deg,#ffffff,#f0f9ff,#e0f2fe,#fef3c7,#ecfeff);
    background-size: 800% 800%;
    animation: gradientBG 20s ease infinite;
}
@keyframes gradientBG {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
</style>
""", unsafe_allow_html=True)

# =========================
# CONSTANTS
# =========================
DATA_URL = "https://docs.google.com/spreadsheets/d/1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534/export?format=csv&gid=0"
COLOR_COL = "塗料編號"
BATCH_COL = "製造批號"

# =========================
# LOAD DATA
# =========================
@st.cache_data(ttl=300)
def load_data(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as r:
        df = pd.read_csv(r)
    return df

df = load_data(DATA_URL)

# =========================
# CLEAN COLUMN NAMES
# =========================
df.columns = (
    df.columns
    .str.replace("\r\n", " ", regex=False)
    .str.replace("\n", " ", regex=False)
    .str.replace("　", " ", regex=False)
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)

st.success("✅ Data loaded successfully")

# =========================
# SIDEBAR FILTER
# =========================
st.sidebar.header("🎨 Color Filter")

color_list = sorted(df[COLOR_COL].dropna().unique())
selected_colors = st.sidebar.multiselect(
    "Select Color Code",
    color_list,
    default=color_list
)

df = df[df[COLOR_COL].isin(selected_colors)]

# =========================
# LINE DATA (PROCESS)
# =========================
def calc_line(df):
    tmp = df[
        [
            COLOR_COL,
            BATCH_COL,
            "正-北 ΔL", "正-南 ΔL",
            "正-北 Δa", "正-南 Δa",
            "正-北 Δb", "正-南 Δb",
        ]
    ].dropna()

    tmp["L"] = tmp[["正-北 ΔL", "正-南 ΔL"]].mean(axis=1)
    tmp["a"] = tmp[["正-北 Δa", "正-南 Δa"]].mean(axis=1)
    tmp["b"] = tmp[["正-北 Δb", "正-南 Δb"]].mean(axis=1)

    return tmp[[COLOR_COL, BATCH_COL, "L", "a", "b"]]

line_df = calc_line(df)

line_batch = (
    line_df
    .groupby([COLOR_COL, BATCH_COL])
    .agg(
        count=("L", "count"),
        L=("L", "mean"),
        a=("a", "mean"),
        b=("b", "mean"),
    )
    .round(2)
    .reset_index()
)

# =========================
# LAB (IQC) DATA
# =========================
lab_df = df[[COLOR_COL, BATCH_COL, "入料檢測 ΔL 正面"]].dropna()
lab_batch = (
    lab_df
    .groupby([COLOR_COL, BATCH_COL])
    .agg(L=("入料檢測 ΔL 正面", "mean"))
    .round(2)
    .reset_index()
)

# =========================
# LAB vs LINE MERGE
# =========================
compare = pd.merge(
    lab_batch,
    line_batch,
    on=[COLOR_COL, BATCH_COL],
    how="inner",
    suffixes=("_LAB", "_LINE")
)

# ================
