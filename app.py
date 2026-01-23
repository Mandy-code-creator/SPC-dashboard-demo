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
# BACKGROUND STYLE
# =========================
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(
            270deg,
            #ffffff,
            #f0f9ff,
            #e0f2fe,
            #fef3c7,
            #ecfeff
        );
        background-size: 800% 800%;
        animation: gradientBG 20s ease infinite;
    }
    @keyframes gradientBG {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# REFRESH
# =========================
if st.button("🔄 Refresh data"):
    st.cache_data.clear()
    st.rerun()

# =========================
# GOOGLE SHEET LINKS
# =========================
LINE_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534/"
    "export?format=csv&gid=0"
)

LAB_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1jbP8puBraQ5Xgs9oIpJ7PlLpjIK3sltrgbrgKUcJ-Qo/"
    "export?format=csv&gid=0"
)

COLOR_COL = "塗料編號"

# =========================
# LOAD DATA
# =========================
@st.cache_data(ttl=300)
def load_data(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as res:
        return pd.read_csv(res)

df_line = load_data(LINE_URL)
df_lab  = load_data(LAB_URL)

# =========================
# CLEAN COLUMN NAMES
# =========================
def clean_columns(df):
    df.columns = (
        df.columns
        .astype(str)
        .str.replace("\r", "", regex=False)
        .str.replace("\n", "", regex=False)
        .str.replace("　", " ", regex=False)
        .str.strip()
    )
    return df

df_line = clean_columns(df_line)
df_lab  = clean_columns(df_lab)

# =========================
# AUTO DETECT BATCH COLUMN
# =========================
def detect_batch_col(df):
    for c in df.columns:
        if "batch" in c.lower() or "批" in c:
            return c
    return None

batch_line_col = detect_batch_col(df_line)
batch_lab_col  = detect_batch_col(df_lab)

if batch_line_col is None or batch_lab_col is None:
    st.error("❌ Cannot detect Batch column automatically")
    st.stop()

df_line["Batch"] = df_line[batch_line_col].astype(str)
df_lab["Batch"]  = df_lab[batch_lab_col].astype(str)

# =========================
# COLOR FILTER
# =========================
st.sidebar.header("🎨 Color Filter")

colors = sorted(
    set(df_line[COLOR_COL].dropna().unique()) |
    set(df_lab[COLOR_COL].dropna().unique())
)

selected_colors = st.sidebar.multiselect(
    "Select Color Code",
    colors,
    default=colors
)

df_line = df_line[df_line[COLOR_COL].isin(selected_colors)]
df_lab  = df_lab[df_lab[COLOR_COL].isin(selected_colors)]

# =========================
# CALC LINE LAB (mean per coil)
# =========================
def calc_line_lab(df):
    tmp = df[
        [
            "Batch", COLOR_COL,
            "正-北 ΔL", "正-南 ΔL",
            "正-北 Δa", "正-南 Δa",
            "正-北 Δb", "正-南 Δb"
        ]
    ].dropna()

    tmp["L"] = tmp[["正-北 ΔL", "正-南 ΔL"]].mean(axis=1)
    tmp["a"] = tmp[["正-北 Δa", "正-南 Δa"]].mean(axis=1)
    tmp["b"] = tmp[["正-北 Δb", "正-南 Δb"]].mean(axis=1)
    return tmp[["Batch", COLOR_COL, "L", "a", "b"]]

# =========================
# CALC LAB IQC
# =========================
def calc_lab_iqc(df):
    cols = [c for c in df.columns if "ΔL" in c or c.strip() == "L"]
    tmp = df[["Batch", COLOR_COL] + cols].dropna()
    tmp["L"] = tmp[cols].mean(axis=1)
    return tmp[["Batch", COLOR_COL, "L"]]

line_df = calc_line_lab(df_line)
lab_df  = calc_lab_iqc(df_lab)

# =========================
# BATCH MEAN
# =========================
line_batch = line_df.groupby(
    [COLOR_COL, "Batch"]
).agg(
    L_mean=("L", "mean"),
    a_mean=("a", "mean"),
    b_mean=("b", "mean")
).round(2).reset_index()

lab_batch = lab_df.groupby(
    [COLOR_COL, "Batch"]
).agg(
    L_mean=("L", "mean")
).round(2).reset_index()

# =========================
# LAB vs LINE CHART
# =========================
st.subheader("📈 LAB vs LINE (ΔL comparison)")

for color in selected_colors:
    fig, ax = plt.subplots()

    l1 = lab_batch[lab_batch[COLOR_COL] == color]
    l2 = line_batch[line_batch[COLOR_COL] == color]

    ax.plot(l1["Batch"], l1["L_mean"], "o-", label="LAB (IQC)")
    ax.plot(l2["Batch"], l2["L_mean"], "s-", label="LINE")

    ax.axhline(0, linestyle="--", color="gray")
    ax.set_title(f"ΔL Trend – Color {color}")
    ax.set_xlabel("Batch")
    ax.set_ylabel("ΔL")
    ax.legend()
    ax.grid(True)

    st.pyplot(fig)

# =========================
# SPC XBAR CHART
# =========================
st.subheader("📊 SPC X̄ Chart (LINE ΔL)")

for color in selected_colors:
    sub = line_batch[line_batch[COLOR_COL] == color]

    mean = sub["L_mean"].mean()
    std  = sub["L_mean"].std()

    ucl = mean + 3 * std
    lcl = mean - 3 * std

    fig, ax = plt.subplots()
    ax.plot(sub["Batch"], sub["L_mean"], marker="o")
    ax.axhline(mean, label="Mean")
    ax.axhline(ucl, linestyle="--", label="UCL")
    ax.axhline(lcl, linestyle="--", label="LCL")

    ax.set_title(f"SPC X̄ Chart – {color}")
    ax.set_ylabel("ΔL")
    ax.legend()
    ax.grid(True)

    st.pyplot(fig)

# =========================
# DISTRIBUTION
# =========================
st.subheader("📉 Distribution (Normal shape)")

for color in selected_colors:
    vals = line_batch[line_batch[COLOR_COL] == color]["L_mean"]

    if len(vals) < 3:
        continue

    mean = vals.mean()
    std  = vals.std()

    x = np.linspace(mean - 4*std, mean + 4*std, 300)
    y = (1/(std*np.sqrt(2*np.pi))) * np.exp(-0.5*((x-mean)/std)**2)

    fig, ax = plt.subplots()
    ax.hist(vals, bins=10, density=True, alpha=0.6)
    ax.plot(x, y)

    ax.set_title(f"ΔL Distribution – {color}")
    ax.set_xlabel("ΔL")
    ax.set_ylabel("Density")
    ax.grid(True)

    st.pyplot(fig)

# =========================
# DATA TABLES
# =========================
st.subheader("📋 LINE Batch Summary")
st.dataframe(line_batch, use_container_width=True)

st.subheader("📋 LAB (IQC) Batch Summary")
st.dataframe(lab_batch, use_container_width=True)
