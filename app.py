import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
import numpy as np
import math

# =========================
# SPC COLOR THEME (INDUSTRIAL)
# =========================
LAB_COLOR    = "#1f77b4"   # Steel Blue (LAB)
LINE_COLOR   = "#2ca02c"   # Process Green (LINE)
LIMIT_COLOR  = "#d62728"   # Control Red (LCL / UCL)
SIGMA_COLOR  = "#ff7f0e"   # Sigma Orange (±3σ)
GRID_COLOR   = "#e0e0e0"

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="SPC Coating Dashboard",
    page_icon="🏭",
    layout="wide"
)

# =========================
# REFRESH BUTTON
# =========================
if st.button("🔄 Refresh data"):
    st.cache_data.clear()
    st.rerun()

# =========================
# SIDEBAR STYLE
# =========================
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background-color: #f6f8fa;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# GOOGLE SHEET LINKS
# =========================
DATA_URL = "https://docs.google.com/spreadsheets/d/1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534/export?format=csv"
LIMIT_URL = "https://docs.google.com/spreadsheets/d/1jbP8puBraQ5Xgs9oIpJ7PlLpjIK3sltrgbrgKUcJ-Qo/export?format=csv"

# =========================
# LOAD DATA
# =========================
@st.cache_data(ttl=300)
def load_data():
    df = pd.read_csv(DATA_URL)
    df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
    return df

@st.cache_data(ttl=300)
def load_limit():
    return pd.read_csv(LIMIT_URL)

df = load_data()
limit_df = load_limit()

# =========================
# FIX COLUMN NAMES
# =========================
df.columns = (
    df.columns
    .str.replace("\r\n", " ", regex=False)
    .str.replace("\n", " ", regex=False)
    .str.replace("　", " ", regex=False)
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)

# =========================
# SIDEBAR – FILTER
# =========================
st.sidebar.title("🏭 Process Filter")

color = st.sidebar.selectbox(
    "Color code",
    sorted(df["塗料編號"].dropna().unique())
)

df = df[df["塗料編號"] == color]

latest_year = df["Time"].dt.year.max()
year = st.sidebar.selectbox(
    "Year",
    sorted(df["Time"].dt.year.dropna().unique()),
    index=list(sorted(df["Time"].dt.year.dropna().unique())).index(latest_year)
)

month = st.sidebar.multiselect(
    "Month (optional)",
    sorted(df["Time"].dt.month.dropna().unique())
)

df = df[df["Time"].dt.year == year]
if month:
    df = df[df["Time"].dt.month.isin(month)]

# =========================
# LIMIT FUNCTION
# =========================
def get_limit(color, prefix, factor):
    row = limit_df[limit_df["Color_code"] == color]
    if row.empty:
        return None, None
    return (
        row.get(f"{factor} {prefix} LCL", [None]).values[0],
        row.get(f"{factor} {prefix} UCL", [None]).values[0]
    )

# =========================
# PREP SPC DATA
# =========================
def prep_spc(df, north, south):
    tmp = df.copy()
    tmp["value"] = tmp[[north, south]].mean(axis=1)
    return tmp.groupby("製造批號", as_index=False).agg(
        Time=("Time", "min"),
        value=("value", "mean")
    )

def prep_lab(df, col):
    return df.groupby("製造批號", as_index=False).agg(
        Time=("Time", "min"),
        value=(col, "mean")
    )

# =========================
# TIME RANGE TEXT
# =========================
def build_time_range_text(spc_df):
    if "Time" not in spc_df.columns:
        return "⏱ N/A | n = 0 batches"

    t = spc_df["Time"].dropna()
    if t.empty:
        return "⏱ N/A | n = 0 batches"

    n = spc_df["製造批號"].nunique()
    return (
        f"⏱ {t.min().strftime('%Y-%m-%d')} → "
        f"{t.max().strftime('%Y-%m-%d')} | "
        f"n = {n} batches"
    )

# =========================
# SPC CHARTS
# =========================
def spc_combined(lab, line, title, lab_lim, line_lim):
    fig, ax = plt.subplots(figsize=(12, 4))

    mean = line["value"].mean()
    std = line["value"].std()

    ax.plot(lab["製造批號"], lab["value"], "o-", color=LAB_COLOR, label="LAB")
    ax.plot(line["製造批號"], line["value"], "o-", color=LINE_COLOR, label="LINE")

    ax.axhline(mean + 3 * std, linestyle="--", color=SIGMA_COLOR, label="+3σ")
    ax.axhline(mean - 3 * std, linestyle="--", color=SIGMA_COLOR, label="-3σ")

    if lab_lim[0] is not None:
        ax.axhline(lab_lim[0], linestyle=":", color=LAB_COLOR, label="LAB LCL")
        ax.axhline(lab_lim[1], linestyle=":", color=LAB_COLOR, label="LAB UCL")

    if line_lim[0] is not None:
        ax.axhline(line_lim[0], color=LIMIT_COLOR, label="LINE LCL")
        ax.axhline(line_lim[1], color=LIMIT_COLOR, label="LINE UCL")

    ax.set_title(title, loc="left", fontsize=11)
    ax.grid(True, color=GRID_COLOR)
    ax.tick_params(axis="x", rotation=45)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.subplots_adjust(right=0.78)
    return fig

def spc_single(spc, title, limit, series_color):
    fig, ax = plt.subplots(figsize=(12, 4))

    mean = spc["value"].mean()
    std = spc["value"].std()

    ax.plot(spc["製造批號"], spc["value"], "o-", color=series_color)

    ax.axhline(mean + 3 * std, linestyle="--", color=SIGMA_COLOR, label="+3σ")
    ax.axhline(mean - 3 * std, linestyle="--", color=SIGMA_COLOR, label="-3σ")

    if limit[0] is not None:
        ax.axhline(limit[0], color=LIMIT_COLOR, label="LCL")
        ax.axhline(limit[1], color=LIMIT_COLOR, label="UCL")

    ax.set_title(title, loc="left", fontsize=11)
    ax.grid(True, color=GRID_COLOR)
    ax.tick_params(axis="x", rotation=45)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.subplots_adjust(right=0.78)
    return fig

def download(fig, name):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    buf.seek(0)
    st.download_button("⬇️ Export PNG", buf, name, "image/png")

# =========================
# PREP DATA
# =========================
spc = {
    "ΔL": {
        "lab": prep_lab(df, "入料檢測 ΔL 正面"),
        "line": prep_spc(df, "正-北 ΔL", "正-南 ΔL")
    },
    "Δa": {
        "lab": prep_lab(df, "入料檢測 Δa 正面"),
        "line": prep_spc(df, "正-北 Δa", "正-南 Δa")
    },
    "Δb": {
        "lab": prep_lab(df, "入料檢測 Δb 正面"),
        "line": prep_spc(df, "正-北 Δb", "正-南 Δb")
    }
}

# =========================
# MAIN DASHBOARD
# =========================
st.title(f"🏭 SPC Coating Dashboard — {color}")

st.markdown("### 📊 COMBINED SPC")
for k in spc:
    time_text = build_time_range_text(
        pd.concat([spc[k]["lab"], spc[k]["line"]])
    )
    fig = spc_combined(
        spc[k]["lab"],
        spc[k]["line"],
        f"COMBINED {k}\n{time_text}",
        get_limit(color, k, "LAB"),
        get_limit(color, k, "LINE")
    )
    st.pyplot(fig)
    download(fig, f"COMBINED_{color}_{k}.png")

st.markdown("---")
st.markdown("### 🧪 LAB SPC")
for k in spc:
    time_text = build_time_range_text(spc[k]["lab"])
    fig = spc_single(
        spc[k]["lab"],
        f"LAB {k}\n{time_text}",
        get_limit(color, k, "LAB"),
        LAB_COLOR
    )
    st.pyplot(fig)
    download(fig, f"LAB_{color}_{k}.png")

st.markdown("---")
st.markdown("### 🏭 LINE SPC")
for k in spc:
    time_text = build_time_range_text(spc[k]["line"])
    fig = spc_single(
        spc[k]["line"],
        f"LINE {k}\n{time_text}",
        get_limit(color, k, "LINE"),
        LINE_COLOR
    )
    st.pyplot(fig)
    download(fig, f"LINE_{color}_{k}.png")
