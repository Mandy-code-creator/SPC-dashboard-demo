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

# ✅ FIX DUY NHẤT – CHUẨN HÓA TÊN CỘT (KHÔNG ĐỔI TÍNH NĂNG)
df.columns = df.columns.str.replace("\n ", "\n", regex=False).str.strip()

limit_df = load_limit()

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
        st.sidebar.warning(f"No {factor} limits")
        return
    st.sidebar.markdown(f"**{factor} Control Limits**")
    st.sidebar.dataframe(
        row.filter(like=factor),
        use_container_width=True,
        hide_index=True
    )

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
# SPC CHARTS
# =========================
def spc_combined(lab, line, title, lab_lim, line_lim):
    fig, ax = plt.subplots(figsize=(12, 4))

    mean = line["value"].mean()
    std = line["value"].std()

    ax.plot(lab["Time"], lab["value"], "o-", label="LAB", color="#1f77b4")
    ax.plot(line["Time"], line["value"], "o-", label="LINE", color="#2ca02c")

    ax.axhline(mean + 3*std, color="orange", linestyle="--")
    ax.axhline(mean - 3*std, color="orange", linestyle="--")

    if lab_lim[0] is not None:
        ax.axhline(lab_lim[0], color="#1f77b4", linestyle=":")
        ax.axhline(lab_lim[1], color="#1f77b4", linestyle=":")

    if line_lim[0] is not None:
        ax.axhline(line_lim[0], color="red")
        ax.axhline(line_lim[1], color="red")

    ax.set_title(title)
    ax.legend()
    ax.grid(True)
    return fig

def spc_single(spc, title, limit, color):
    fig, ax = plt.subplots(figsize=(12, 4))

    mean = spc["value"].mean()
    std = spc["value"].std()

    ax.plot(spc["Time"], spc["value"], "o-", color=color)
    ax.axhline(mean + 3*std, color="orange", linestyle="--")
    ax.axhline(mean - 3*std, color="orange", linestyle="--")

    if limit[0] is not None:
        ax.axhline(limit[0], color="red")
        ax.axhline(limit[1], color="red")

    ax.set_title(title)
    ax.grid(True)
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
        "lab": prep_lab(df, "入料檢測\nΔL 正面"),
        "line": prep_spc(df, "正-北\nΔL", "正-南\nΔL")
    },
    "Δa": {
        "lab": prep_lab(df, "入料檢測\nΔa 正面"),
        "line": prep_spc(df, "正-北\nΔa", "正-南\nΔa")
    },
    "Δb": {
        "lab": prep_lab(df, "入料檢測\nΔb 正面"),
        "line": prep_spc(df, "正-北\nΔb", "正-南\nΔb")
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
