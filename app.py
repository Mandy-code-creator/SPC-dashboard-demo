import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
import numpy as np
import math

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="SPC Color Dashboard",
    page_icon="🎨",
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
st.sidebar.title("🎨 Filter")

color = st.sidebar.selectbox(
    "Color code",
    sorted(df["塗料編號"].dropna().unique())
)

df = df[df["塗料編號"] == color]

latest_year = int(df["Time"].dt.year.max())
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
# DASHBOARD TIME RANGE TEXT
# =========================
def build_dashboard_time_range(df, year, month):
    if "Time" not in df.columns:
        return "⏱ N/A | n = 0 batches"

    t = df["Time"].dropna()
    if t.empty:
        return "⏱ N/A | n = 0 batches"

    n = df["製造批號"].nunique()
    month_text = "All" if not month else ", ".join(map(str, month))

    return (
        f"⏱ {t.min().strftime('%Y-%m-%d')} → {t.max().strftime('%Y-%m-%d')} | "
        f"n = {n} batches | "
        f"Year: {year} | Month: {month_text}"
    )

# =========================
# TITLE
# =========================
st.title(f"🎨 SPC Color Dashboard — {color}")

st.markdown(
    f"""
    <div style="color:#6c757d;font-size:0.95rem;margin-top:-10px;">
    {build_dashboard_time_range(df, year, month)}
    </div>
    """,
    unsafe_allow_html=True
)

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
# SPC CHART FUNCTIONS
# =========================
def spc_combined(lab, line, title, lab_lim, line_lim):
    fig, ax = plt.subplots(figsize=(12, 4))
    mean = line["value"].mean()
    std = line["value"].std()

    ax.plot(lab["製造批號"], lab["value"], "o-", label="LAB")
    ax.plot(line["製造批號"], line["value"], "o-", label="LINE")

    ax.axhline(mean + 3 * std, linestyle="--", color="orange")
    ax.axhline(mean - 3 * std, linestyle="--", color="orange")

    if lab_lim[0] is not None:
        ax.axhline(lab_lim[0], linestyle=":", label="LAB LCL")
        ax.axhline(lab_lim[1], linestyle=":", label="LAB UCL")

    if line_lim[0] is not None:
        ax.axhline(line_lim[0], color="red", label="LINE LCL")
        ax.axhline(line_lim[1], color="red", label="LINE UCL")

    ax.set_title(title, loc="left")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.grid(True)
    ax.tick_params(axis="x", rotation=45)
    fig.subplots_adjust(right=0.78)
    return fig

def spc_single(spc, title, limit, color):
    fig, ax = plt.subplots(figsize=(12, 4))
    mean = spc["value"].mean()
    std = spc["value"].std()

    ax.plot(spc["製造批號"], spc["value"], "o-", color=color)
    ax.axhline(mean + 3 * std, linestyle="--", color="orange")
    ax.axhline(mean - 3 * std, linestyle="--", color="orange")

    if limit[0] is not None:
        ax.axhline(limit[0], color="red", label="LCL")
        ax.axhline(limit[1], color="red", label="UCL")

    ax.set_title(title, loc="left")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.grid(True)
    ax.tick_params(axis="x", rotation=45)
    fig.subplots_adjust(right=0.78)
    return fig

def download(fig, name):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    buf.seek(0)
    st.download_button("📥 Download PNG", buf, name, "image/png")

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
st.markdown("### 📊 COMBINED SPC")
for k in spc:
    fig = spc_combined(
        spc[k]["lab"],
        spc[k]["line"],
        f"COMBINED {k}",
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
        f"LAB {k}",
        get_limit(color, k, "LAB"),
        "#1f77b4"
    )
    st.pyplot(fig)
    download(fig, f"LAB_{color}_{k}.png")

st.markdown("---")
st.markdown("### 🏭 LINE SPC")
for k in spc:
    fig = spc_single(
        spc[k]["line"],
        f"LINE {k}",
        get_limit(color, k, "LINE"),
        "#2ca02c"
    )
    st.pyplot(fig)
    download(fig, f"LINE_{color}_{k}.png")
