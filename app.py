import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
import numpy as np
import math
st.write("✅ FILE LOADED AT:", __file__)
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

df_raw = load_data()
limit_df = load_limit()

# =========================
# FIX COLUMN NAMES
# =========================
df_raw.columns = (
    df_raw.columns
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

color_list = sorted(df_raw["塗料編號"].dropna().unique())
color = st.sidebar.selectbox("Color code", color_list)

df = df_raw[df_raw["塗料編號"] == color].copy()

# ---- YEAR FILTER (SAFE) ----
year_list = sorted(df["Time"].dt.year.dropna().unique())
if year_list:
    year = st.sidebar.selectbox("Year", year_list, index=len(year_list) - 1)
    df = df[df["Time"].dt.year == year]
else:
    year = "N/A"

# ---- MONTH FILTER (SAFE) ----
month_list = sorted(df["Time"].dt.month.dropna().unique())
month = st.sidebar.multiselect("Month (optional)", month_list)

if month:
    df = df[df["Time"].dt.month.isin(month)]

# =========================
# BUILD TIME RANGE + N (ABSOLUTELY SAFE)
# =========================
if df.empty or df["Time"].dropna().empty:
    t_min = "N/A"
    t_max = "N/A"
    n_batch = 0
else:
    t_min = df["Time"].min().strftime("%Y-%m-%d")
    t_max = df["Time"].max().strftime("%Y-%m-%d")
    n_batch = df["製造批號"].nunique()

month_text = "All" if not month else ", ".join(map(str, month))

# =========================
# TITLE + TIME RANGE (100% HIỆN)
# =========================
st.markdown(
    f"""
    <div style="margin-bottom:1.2rem">
        <h1 style="margin-bottom:0.3rem;">
            🎨 SPC Color Dashboard — {color}
        </h1>
        <div style="color:#6c757d;font-size:0.95rem;">
            ⏱ {t_min} → {t_max} | n = {n_batch} batches | Year: {year} | Month: {month_text}
        </div>
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
def prep_lab(df, col):
    return df.groupby("製造批號", as_index=False).agg(
        Time=("Time", "min"),
        value=(col, "mean")
    )

# =========================
# SPC CHART
# =========================
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
    ax.grid(True)
    ax.tick_params(axis="x", rotation=45)
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
    "ΔL": prep_lab(df, "入料檢測 ΔL 正面"),
    "Δa": prep_lab(df, "入料檢測 Δa 正面"),
    "Δb": prep_lab(df, "入料檢測 Δb 正面"),
}

# =========================
# MAIN DASHBOARD
# =========================
st.markdown("### 🧪 LAB SPC")

for k, spc_df in spc.items():
    fig = spc_single(
        spc_df,
        f"LAB {k}",
        get_limit(color, k, "LAB"),
        "#1f77b4"
    )
    st.pyplot(fig)
    download(fig, f"LAB_{color}_{k}.png")

