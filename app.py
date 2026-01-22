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
# REFRESH BUTTON (TOP)
# =========================
if st.button("🔄 Refresh data"):
    st.cache_data.clear()

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
# LIMIT DISPLAY
# =========================
def show_limits(factor):
    row = limit_df[limit_df["Color_code"] == color]
    if row.empty:
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
# TIME BOX (⏱ FIX CLIP)
# =========================
def add_time_box(ax, spc_df):
    if spc_df.empty:
        return
    t_min = spc_df["Time"].min().strftime("%Y-%m-%d")
    t_max = spc_df["Time"].max().strftime("%Y-%m-%d")

    ax.text(
        1.02, 0.02,
        f"⏱ Time range\n{t_min} → {t_max}",
        transform=ax.transAxes,
        fontsize=9,
        va="bottom",
        clip_on=False,   # 🔥 QUAN TRỌNG
        bbox=dict(
            boxstyle="round,pad=0.35",
            fc="#f8f9fa",
            ec="#ced4da"
        )
    )

# =========================
# SPC CHARTS
# =========================
def spc_combined(lab, line, title, lab_lim, line_lim):
    fig, ax = plt.subplots(figsize=(12, 4))
    fig.subplots_adjust(right=0.78)

    mean = line["value"].mean()
    std = line["value"].std()

    ax.plot(lab["製造批號"], lab["value"], "o-", label="LAB")
    ax.plot(line["製造批號"], line["value"], "o-", label="LINE")

    ax.axhline(mean + 3 * std, linestyle="--", color="orange", label="+3σ")
    ax.axhline(mean - 3 * std, linestyle="--", color="orange", label="-3σ")

    if lab_lim[0] is not None:
        ax.axhline(lab_lim[0], linestyle=":", label="LAB LCL")
        ax.axhline(lab_lim[1], linestyle=":", label="LAB UCL")

    if line_lim[0] is not None:
        ax.axhline(line_lim[0], color="red", label="LINE LCL")
        ax.axhline(line_lim[1], color="red", label="LINE UCL")

    ax.set_title(title)
    ax.grid(True)
    ax.tick_params(axis="x", rotation=45)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))

    add_time_box(ax, line)
    return fig

def spc_single(spc, title, limit, color):
    fig, ax = plt.subplots(figsize=(12, 4))
    fig.subplots_adjust(right=0.78)

    mean = spc["value"].mean()
    std = spc["value"].std()

    ax.plot(spc["製造批號"], spc["value"], "o-", color=color, label="Value")
    ax.axhline(mean + 3 * std, linestyle="--", color="orange", label="+3σ")
    ax.axhline(mean - 3 * std, linestyle="--", color="orange", label="-3σ")

    if limit[0] is not None:
        ax.axhline(limit[0], color="red", label="LCL")
        ax.axhline(limit[1], color="red", label="UCL")

    ax.set_title(title)
    ax.grid(True)
    ax.tick_params(axis="x", rotation=45)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))

    add_time_box(ax, spc)
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
# MAIN
# =========================
st.title(f"🎨 SPC Color Dashboard — {color}")

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
st.markdown("## 📈 Process Distribution Dashboard")

def normal_pdf(x, mean, std):
    return (1 / (std * math.sqrt(2 * math.pi))) * np.exp(-0.5 * ((x - mean) / std) ** 2)

cols = st.columns(3)
for i, k in enumerate(spc):
    with cols[i]:
        values = spc[k]["line"]["value"].dropna()
        mean = values.mean()
        std = values.std()
        lcl, ucl = get_limit(color, k, "LINE")

        fig, ax = plt.subplots(figsize=(4, 3))
        bins = np.histogram_bin_edges(values, bins=10)

        ax.hist(values, bins=bins, color="#4dabf7", edgecolor="white", alpha=0.85)

        x = np.linspace(mean - 3 * std, mean + 3 * std, 400)
        pdf = normal_pdf(x, mean, std)
        ax.plot(x, pdf * len(values) * (bins[1] - bins[0]), color="black")

        ax.set_title(f"{k}")
        ax.grid(axis="y", alpha=0.3)
        st.pyplot(fig)
