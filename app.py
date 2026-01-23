import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
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
# STYLE
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
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# =========================
# GOOGLE SHEETS
# =========================
DATA_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534/"
    "export?format=csv&gid=0"
)

COLOR_COL = "塗料編號"
BATCH_COL = "製造批號"

# =========================
# LOAD DATA
# =========================
@st.cache_data(ttl=300)
def load_data(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as r:
        return pd.read_csv(r)

df = load_data(DATA_URL)

# =========================
# CLEAN COLUMN NAMES
# =========================
df.columns = (
    df.columns
    .astype(str)
    .str.replace("\n", " ", regex=False)
    .str.replace("\r", " ", regex=False)
    .str.replace("　", " ", regex=False)
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)

# =========================
# FIX DATA TYPES (CRITICAL)
# =========================
df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
df = df.dropna(subset=["Time"])

df[COLOR_COL] = df[COLOR_COL].astype(str).str.strip()
df[BATCH_COL] = df[BATCH_COL].astype(str).str.strip()

st.success("✅ Data loaded successfully")

# =========================
# SIDEBAR – FILTER
# =========================
st.sidebar.title("🎨 Filter")

color = st.sidebar.selectbox(
    "Color code",
    sorted(df[COLOR_COL].dropna().unique())
)

df = df[df[COLOR_COL] == color]

latest_year = df["Time"].dt.year.max()

year = st.sidebar.selectbox(
    "Year",
    sorted(df["Time"].dt.year.unique()),
    index=list(sorted(df["Time"].dt.year.unique())).index(latest_year)
)

month = st.sidebar.multiselect(
    "Month (optional)",
    sorted(df["Time"].dt.month.unique())
)

df = df[df["Time"].dt.year == year]
if month:
    df = df[df["Time"].dt.month.isin(month)]

st.sidebar.divider()

# =====================================================
# LINE DATA
# =====================================================
st.header("🏭 LINE Measurement (Production)")

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
        L_LINE=("L", "mean"),
        a_LINE=("a", "mean"),
        b_LINE=("b", "mean"),
        sample_count=("L", "count")
    )
    .round(2)
    .reset_index()
)

st.subheader("📊 LINE – Batch Mean")
st.dataframe(line_batch, use_container_width=True)

# =====================================================
# LAB (IQC)
# =====================================================
st.header("🧪 LAB (IQC) – Incoming Inspection (Front Side)")

lab_df = df[
    [
        COLOR_COL,
        BATCH_COL,
        "入料檢測 ΔL 正面",
        "入料檢測 Δa 正面",
        "入料檢測 Δb 正面",
    ]
].dropna(subset=["入料檢測 ΔL 正面"]).copy()

lab_df = lab_df.rename(columns={
    "入料檢測 ΔL 正面": "L",
    "入料檢測 Δa 正面": "a",
    "入料檢測 Δb 正面": "b",
})

lab_batch = (
    lab_df
    .groupby([COLOR_COL, BATCH_COL])
    .agg(
        L_LAB=("L", "mean"),
        a_LAB=("a", "mean"),
        b_LAB=("b", "mean"),
        lab_sample=("L", "count")
    )
    .round(2)
    .reset_index()
)

st.subheader("📊 LAB – Batch Mean")
st.dataframe(lab_batch, use_container_width=True)

# =====================================================
# LAB vs LINE COMPARISON
# =====================================================
st.header("🔍 LAB vs LINE – Color Deviation Traceability")

compare = pd.merge(
    lab_batch,
    line_batch,
    on=[COLOR_COL, BATCH_COL],
    how="inner"
)

compare["Delta_E_LAB_LINE"] = np.sqrt(
    (compare["L_LINE"] - compare["L_LAB"])**2 +
    (compare["a_LINE"] - compare["a_LAB"])**2 +
    (compare["b_LINE"] - compare["b_LAB"])**2
).round(2)

st.subheader("📋 LAB vs LINE Comparison Table")
st.dataframe(compare, use_container_width=True)

# =====================================================
# COMPARISON CHART
# =====================================================
st.subheader("📈 LAB vs LINE Trend Chart")

metric = st.selectbox("Select Metric", ["L", "a", "b"])

for c in compare[COLOR_COL].unique():
    sub = compare[compare[COLOR_COL] == c].copy()

    fig, ax = plt.subplots(figsize=(8, 4))

    ax.plot(
        sub[BATCH_COL],
        sub[f"{metric}_LAB"],
        marker="o",
        linestyle="--",
        label="LAB (IQC)"
    )

    ax.plot(
        sub[BATCH_COL],
        sub[f"{metric}_LINE"],
        marker="s",
        linestyle="-",
        label="LINE (Production)"
    )

    ax.set_title(f"{metric} – LAB vs LINE | Color Code {c}")
    ax.set_xlabel("Batch")
    ax.set_ylabel(metric)
    ax.legend()
    ax.grid(True)

    st.pyplot(fig)

# =====================================================
# EXPORT
# =====================================================
st.header("📤 Export Report")

csv = compare.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    "⬇️ Download LAB_vs_LINE_Report.csv",
    csv,
    "LAB_vs_LINE_Report.csv",
    "text/csv"
)
