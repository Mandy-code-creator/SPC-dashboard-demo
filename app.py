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
    df["Time"] = pd.to_datetime(df["Time"])
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

# =========================
# LIMIT DISPLAY (2 DECIMALS)
# =========================
def show_limits(factor):
    row = limit_df[limit_df["Color_code"] == color]
    if row.empty:
        st.sidebar.warning(f"No {factor} limits")
        return

    table = row.filter(like=factor).copy()
    for c in table.columns:
        table[c] = table[c].map(lambda x: f"{x:.2f}" if pd.notnull(x) else "")

    st.sidebar.markdown(f"**{factor} Control Limits**")
    st.sidebar.dataframe(table, use_container_width=True, hide_index=True)

show_limits("LAB")
show_limits("LINE")

# =========================
# LIMIT FUNCTION
# =========================
def get_limit(color, prefix, factor):
    row = limit_df[limit_df["Color_code"] == color]
    if row.empty:
        return None, None
    return (
        row[f"{factor} {prefix} LCL"].values[0],
        row[f"{factor} {prefix} UCL"].values[0]
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
# SPC CHARTS (GIỮ NGUYÊN)
# =========================
def spc_combined(lab, line, title, lab_lim, line_lim):
    fig, ax = plt.subplots(figsize=(12, 4))

    mean = line["value"].mean()
    std = line["value"].std()

    ax.plot(lab["製造批號"], lab["value"], "o-", label="LAB", color="#1f77b4")
    ax.plot(line["製造批號"], line["value"], "o-", label="LINE", color="#2ca02c")

    ax.axhline(mean + 3 * std, color="orange", linestyle="--")
    ax.axhline(mean - 3 * std, color="orange", linestyle="--")

    if lab_lim[0] is not None:
        ax.axhline(lab_lim[0], color="#1f77b4", linestyle=":")
        ax.axhline(lab_lim[1], color="#1f77b4", linestyle=":")

    if line_lim[0] is not None:
        ax.axhline(line_lim[0], color="red")
        ax.axhline(line_lim[1], color="red")

    ax.set_title(title)
    ax.legend()
    ax.grid(True)
    ax.tick_params(axis="x", rotation=45)
    return fig

def spc_single(spc, title, limit, color):
    fig, ax = plt.subplots(figsize=(12, 4))

    mean = spc["value"].mean()
    std = spc["value"].std()

    ax.plot(spc["製造批號"], spc["value"], "o-", color=color)
    ax.axhline(mean + 3 * std, color="orange", linestyle="--")
    ax.axhline(mean - 3 * std, color="orange", linestyle="--")

    if limit[0] is not None:
        ax.axhline(limit[0], color="red")
        ax.axhline(limit[1], color="red")

    ax.set_title(title)
    ax.grid(True)
    ax.tick_params(axis="x", rotation=45)
    return fig

def download(fig, name):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    buf.seek(0)
    st.download_button("📥 Download PNG", buf, name, "image/png")

# =========================
# NORMAL PDF (NO SCIPY)
# =========================
def normal_pdf(x, mean, std):
    return (1 / (std * math.sqrt(2 * math.pi))) * np.exp(-0.5 * ((x - mean) / std) ** 2)

# =========================
# DISTRIBUTION CHART
# =========================
def spc_distribution(spc, title, limit, color):
    fig, ax = plt.subplots(figsize=(8, 4))

    values = spc["value"].dropna()
    mean = values.mean()
    std = values.std()

    lcl, ucl = limit
    center = (ucl + lcl) / 2 if lcl is not None else None

    bins = np.histogram_bin_edges(values, bins=12)
    counts, _, patches = ax.hist(values, bins=bins, edgecolor="white")

    for patch, left, right in zip(patches, bins[:-1], bins[1:]):
        c = (left + right) / 2
        patch.set_facecolor("red" if lcl is not None and (c < lcl or c > ucl) else color)
        patch.set_alpha(0.75)

    x = np.linspace(values.min(), values.max(), 200)
    pdf = normal_pdf(x, mean, std)
    scale = len(values) * (bins[1] - bins[0])
    ax.plot(x, pdf * scale, color="black", linewidth=2, label="Normal Curve")

    ax.axvline(mean, color="blue", linestyle="--", label="Mean")

    if lcl is not None:
        ax.axvline(lcl, color="red", label="LCL")
        ax.axvline(ucl, color="red", label="UCL")

        cp = (ucl - lcl) / (6 * std)
        cpk = min(ucl - mean, mean - lcl) / (3 * std)
        ca = abs(mean - center) / ((ucl - lcl) / 2)

        ax.text(
            0.98, 0.95,
            f"Cp  = {cp:.2f}\nCpk = {cpk:.2f}\nCa  = {ca:.2f}",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=10,
            bbox=dict(boxstyle="round", fc="#f6f8fa", ec="gray")
        )

    ax.set_title(title)
    ax.set_xlabel("Value")
    ax.set_ylabel("Frequency")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    return fig

# =========================
# PREP DATA
# =========================
spc = {
    "ΔL": prep_spc(df, "正-北 ΔL", "正-南 ΔL"),
    "Δa": prep_spc(df, "正-北 Δa", "正-南 Δa"),
    "Δb": prep_spc(df, "正-北 Δb", "正-南 Δb")
}

# =========================
# MAIN
# =========================
st.title(f"🎨 SPC Color Dashboard — {color}")

st.markdown("### 📈 SPC Distribution (Cp / Cpk / Ca)")
for k in spc:
    fig = spc_distribution(
        spc[k],
        f"Distribution {k}",
        get_limit(color, k, "LINE"),
        "#6f42c1"
    )
    st.pyplot(fig)
    download(fig, f"DIST_{color}_{k}.png")
