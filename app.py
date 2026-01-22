import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
import numpy as np

# =========================
# FORCE MATPLOTLIB STYLE (VERY IMPORTANT)
# =========================
plt.rcParams.update({
    "axes.facecolor": "white",
    "figure.facecolor": "white",
    "axes.edgecolor": "#cccccc",
    "axes.labelcolor": "#333333",
    "xtick.color": "#333333",
    "ytick.color": "#333333",
    "grid.color": "#e0e0e0",
    "grid.linestyle": "-",
    "grid.linewidth": 0.8,
    "axes.grid": True,
    "legend.frameon": False,
    "lines.linewidth": 2.5,
    "lines.markersize": 6
})

# =========================
# SPC COLOR THEME (INDUSTRIAL)
# =========================
LAB_COLOR    = "#1f77b4"   # Steel Blue
LINE_COLOR   = "#2ca02c"   # Process Green
LIMIT_COLOR  = "#d62728"   # Control Red
SIGMA_COLOR  = "#ff7f0e"   # Sigma Orange
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
# HARD REFRESH BUTTON
# =========================
if st.button("🔄 HARD Refresh (Clear Cache)"):
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
# DATA SOURCES
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

# =========================
# SIDEBAR FILTER
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
    t = spc_df["Time"].dropna()
    if t.empty:
        return "⏱ N/A | n = 0 batches"
    return (
        f"⏱ {t.min().strftime('%Y-%m-%d')} → "
        f"{t.max().strftime('%Y-%m-%d')} | "
        f"n = {spc_df['製造批號'].nunique()}"
    )

# =========================
# SPC CHARTS
# =========================
def spc_combined(lab, line, title, lab_lim, line_lim):
    fig, ax = plt.subplots(figsize=(12, 4))

    mean = line["value"].mean()
    std = line["value"].std()

    ax.plot(lab["製造批號"], lab["value"],
            color=LAB_COLOR, marker="o", label="LAB")
    ax.plot(line["製造批號"], line["value"],
            color=LINE_COLOR, marker="o", label="LINE")

    ax.axhline(mean + 3*std, color=SIGMA_COLOR, linestyle="--", linewidth=2)
    ax.axhline(mean - 3*std, color=SIGMA_COLOR, linestyle="--", linewidth=2)

    if lab_lim[0] is not None:
        ax.axhline(lab_lim[0], color=LAB_COLOR, linestyle=":", linewidth=2)
        ax.axhline(lab_lim[1], color=LAB_COLOR, linestyle=":", linewidth=2)

    if line_lim[0] is not None:
        ax.axhline(line_lim[0], color=LIMIT_COLOR, linestyle=":", linewidth=2.5)
        ax.axhline(line_lim[1], color=LIMIT_COLOR, linestyle=":", linewidth=2.5)

    ax.set_title(title, loc="left", fontsize=11)
    ax.tick_params(axis="x", rotation=45)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.subplots_adjust(right=0.78)
    return fig

def spc_single(spc, title, limit, color):
    fig, ax = plt.subplots(figsize=(12, 4))

    mean = spc["value"].mean()
    std = spc["value"].std()

    ax.plot(spc["製造批號"], spc["value"],
            color=color, marker="o")

    ax.axhline(mean + 3*std, color=SIGMA_COLOR, linestyle="--", linewidth=2)
    ax.axhline(mean - 3*std, color=SIGMA_COLOR, linestyle="--", linewidth=2)

    if limit[0] is not None:
        ax.axhline(limit[0], color=LIMIT_COLOR, linestyle=":", linewidth=2.5)
        ax.axhline(limit[1], color=LIMIT_COLOR, linestyle=":", linewidth=2.5)

    ax.set_title(title, loc="left", fontsize=11)
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
    fig = spc_single(
        spc[k]["lab"],
        f"LAB {k}\n{build_time_range_text(spc[k]['lab'])}",
        get_limit(color, k, "LAB"),
        LAB_COLOR
    )
    st.pyplot(fig)
    download(fig, f"LAB_{color}_{k}.png")

st.markdown("---")
st.markdown("### 🏭 LINE SPC")
for k in spc:
    fig = spc_single(
        spc[k]["line"],
        f"LINE {k}\n{build_time_range_text(spc[k]['line'])}",
        get_limit(color, k, "LINE"),
        LINE_COLOR
    )
    st.pyplot(fig)
    download(fig, f"LINE_{color}_{k}.png")
