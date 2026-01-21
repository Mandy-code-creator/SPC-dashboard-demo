import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="SPC Color Dashboard",
    page_icon="🎨",
    layout="wide"
)

# =========================
# GLOBAL STYLE
# =========================
st.markdown("""
<style>
.block-container {
    padding-top: 1.5rem;
}
h1 {
    color: #1f4e79;
}
h2, h3 {
    color: #1f4e79;
}
.sidebar-title {
    font-size: 20px;
    font-weight: bold;
}
.section-card {
    padding: 1rem;
    border-radius: 10px;
    background-color: #f8f9fa;
    margin-bottom: 1rem;
    border-left: 6px solid #1f77b4;
}
</style>
""", unsafe_allow_html=True)

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

# =========================
# NORMALIZE HEADERS
# =========================
df.columns = (
    df.columns
      .str.replace("\r\n", " ", regex=False)
      .str.replace("\n", " ", regex=False)
      .str.replace("　", " ", regex=False)
      .str.replace(r"\s+", " ", regex=True)
      .str.strip()
)

limit_df = load_limit()
limit_df.columns = (
    limit_df.columns
      .str.replace("\r\n", " ", regex=False)
      .str.replace("\n", " ", regex=False)
      .str.replace("　", " ", regex=False)
      .str.replace(r"\s+", " ", regex=True)
      .str.strip()
)

# =========================
# SIDEBAR – FILTER
# =========================
st.sidebar.markdown("### 🎛️ Filter Panel")

color = st.sidebar.selectbox(
    "🎨 Color code",
    sorted(df["塗料編號"].dropna().unique())
)

df = df[df["塗料編號"] == color]

latest_year = df["Time"].dt.year.max()
year = st.sidebar.selectbox(
    "📅 Year",
    sorted(df["Time"].dt.year.unique()),
    index=list(sorted(df["Time"].dt.year.unique())).index(latest_year)
)

month = st.sidebar.multiselect(
    "🗓️ Month (optional)",
    sorted(df["Time"].dt.month.unique())
)

df = df[df["Time"].dt.year == year]
if month:
    df = df[df["Time"].dt.month.isin(month)]

st.sidebar.divider()

# =========================
# LIMIT DISPLAY
# =========================
def show_limits(factor, icon):
    row = limit_df[limit_df["Color_code"] == color]
    if row.empty:
        st.sidebar.warning(f"No {factor} limits")
        return
    st.sidebar.markdown(f"### {icon} {factor} Limits")
    st.sidebar.dataframe(
        row.filter(like=factor),
        use_container_width=True,
        hide_index=True
    )

show_limits("LAB", "🧪")
show_limits("LINE", "🏭")

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
    out = tmp.groupby("製造批號", as_index=False).agg(
        Time=("Time", "min"),
        value=("value", "mean")
    )
    return out.sort_values("Time")

def prep_lab(df, col):
    out = df.groupby("製造批號", as_index=False).agg(
        Time=("Time", "min"),
        value=(col, "mean")
    )
    return out.sort_values("Time")

# =========================
# SPC CHARTS
# =========================
def spc_single(spc, title, limit, color):
    fig, ax = plt.subplots(figsize=(13, 4))

    mean = spc["value"].mean()
    std = spc["value"].std()

    ax.plot(
        spc["製造批號"], spc["value"],
        marker="o", linewidth=1.5, markersize=5,
        color=color
    )

    ax.axhline(mean, color="black", linestyle="--", linewidth=1)
    ax.axhline(mean + 3*std, color="orange", linestyle="--", alpha=0.6)
    ax.axhline(mean - 3*std, color="orange", linestyle="--", alpha=0.6)

    if limit[0] is not None:
        ax.axhline(limit[0], color="red", linewidth=2)
        ax.axhline(limit[1], color="red", linewidth=2)

    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel("Batch Code")
    ax.grid(True, linestyle="--", alpha=0.3)
    plt.xticks(rotation=45)
    fig.tight_layout()
    return fig

def download(fig, name):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    buf.seek(0)
    st.download_button("⬇️ Download PNG", buf, name, "image/png")

# =========================
# PREP DATA
# =========================
spc = {
    "ΔL": prep_lab(df, "入料檢測 ΔL 正面"),
    "Δa": prep_lab(df, "入料檢測 Δa 正面"),
    "Δb": prep_lab(df, "入料檢測 Δb 正面")
}

# =========================
# MAIN
# =========================
st.title(f"🎨 SPC Color Dashboard — {color}")
st.caption("📊 Statistical Process Control for Color Quality")

for k in spc:
    st.markdown(f"<div class='section-card'>🧪 <b>LAB SPC — {k}</b></div>", unsafe_allow_html=True)
    fig = spc_single(
        spc[k],
        f"LAB {k}",
        get_limit(color, k, "LAB"),
        "#1f77b4"
    )
    st.pyplot(fig)
    download(fig, f"LAB_{color}_{k}.png")
