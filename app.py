import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import urllib.request

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="SPC Color Dashboard",
    page_icon="🎨",
    layout="wide"
)

# =========================
# UTILS
# =========================
def load_data(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as r:
        return pd.read_csv(r)

def normal_pdf(x, mean, std):
    return (1 / (std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mean) / std) ** 2)

# =========================
# DATA SOURCE
# =========================
DATA_URL = "https://docs.google.com/spreadsheets/d/1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534/export?format=csv&gid=0"

COLOR_COL = "塗料編號"
BATCH_COL = "製造批號"

# =========================
# LOAD
# =========================
df = load_data(DATA_URL)

df.columns = (
    df.columns.astype(str)
    .str.replace("\n", " ")
    .str.replace("　", " ")
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)

# =========================
# SIDEBAR
# =========================
st.sidebar.header("🎨 Filter")

colors = sorted(df[COLOR_COL].dropna().unique())
selected_colors = st.sidebar.multiselect(
    "Paint Code (塗料編號)",
    colors,
    default=colors
)

df = df[df[COLOR_COL].isin(selected_colors)]

# =========================
# LAB (Incoming IQC)
# =========================
lab_col = "入料檢測 ΔL 正面"

lab_df = df[[COLOR_COL, BATCH_COL, lab_col]].dropna()
lab_batch = (
    lab_df
    .groupby([COLOR_COL, BATCH_COL])
    .agg(LAB_mean=(lab_col, "mean"))
    .reset_index()
)

# =========================
# LINE (Production)
# =========================
line_df = df[[
    COLOR_COL, BATCH_COL,
    "正-北 ΔL", "正-南 ΔL"
]].dropna()

line_df["LINE_L"] = line_df[["正-北 ΔL", "正-南 ΔL"]].mean(axis=1)

line_batch = (
    line_df
    .groupby([COLOR_COL, BATCH_COL])
    .agg(LINE_mean=("LINE_L", "mean"))
    .reset_index()
)

# =========================
# MERGE LAB vs LINE
# =========================
compare_df = pd.merge(
    lab_batch,
    line_batch,
    on=[COLOR_COL, BATCH_COL],
    how="inner"
)

# =========================
# LAB vs LINE CHART
# =========================
st.subheader("📈 LAB vs LINE (ΔL)")

for color in compare_df[COLOR_COL].unique():
    sub = compare_df[compare_df[COLOR_COL] == color]

    fig, ax = plt.subplots(figsize=(10,4))
    ax.plot(sub[BATCH_COL], sub["LAB_mean"], marker="o", label="LAB (Incoming)")
    ax.plot(sub[BATCH_COL], sub["LINE_mean"], marker="s", label="LINE (Production)")

    ax.set_title(f"Paint Code {color}")
    ax.set_xlabel("Batch")
    ax.set_ylabel("ΔL")
    ax.legend()
    ax.grid(True)
    plt.xticks(rotation=45, ha="right")

    st.pyplot(fig)

# =========================
# SPC CHART (LINE)
# =========================
st.subheader("📊 SPC Chart – LINE ΔL")

values = line_batch["LINE_mean"]
mean = values.mean()
std = values.std()

ucl = mean + 3 * std
lcl = mean - 3 * std

fig, ax = plt.subplots(figsize=(10,4))
ax.plot(line_batch[BATCH_COL], values, marker="o")
ax
