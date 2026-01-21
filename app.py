import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import io

st.set_page_config(
    page_title="SPC Color Dashboard",
    layout="wide",
    page_icon="📊"
)

# ======================
# CONFIG
# ======================
DATA_SHEET = "https://docs.google.com/spreadsheets/d/1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534/export?format=csv"
LIMIT_SHEET = "https://docs.google.com/spreadsheets/d/1jbP8puBraQ5Xgs9oIpJ7PlLpjIK3sltrgbrgKUcJ-Qo/export?format=csv"

# ======================
# LOAD DATA
# ======================
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_SHEET)
    df.columns = df.columns.str.replace("\n", " ").str.strip()
    df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
    return df

@st.cache_data
def load_limits():
    lim = pd.read_csv(LIMIT_SHEET)
    lim.columns = lim.columns.str.strip()
    return lim

df = load_data()
limit_df = load_limits()

# ======================
# STANDARDIZE COLUMNS
# ======================
COL = {
    "color": "塗料編號",
    "batch": "製造批號",
    "dL_n": "正-北 ΔL",
    "dL_s": "正-南 ΔL",
    "da_n": "正-北 Δa",
    "da_s": "正-南 Δa",
    "db_n": "正-北 Δb",
    "db_s": "正-南 Δb",
    "lab_dL": "入料檢測 ΔL 正面",
    "lab_da": "入料檢測 Δa 正面",
    "lab_db": "入料檢測 Δb 正面",
}

df["dL_line"] = df[[COL["dL_n"], COL["dL_s"]]].mean(axis=1)
df["da_line"] = df[[COL["da_n"], COL["da_s"]]].mean(axis=1)
df["db_line"] = df[[COL["db_n"], COL["db_s"]]].mean(axis=1)

df["dL_lab"] = df[COL["lab_dL"]]
df["da_lab"] = df[COL["lab_da"]]
df["db_lab"] = df[COL["lab_db"]]

# ======================
# SIDEBAR – FILTER
# ======================
st.sidebar.header("🎛 Filters")

years = sorted(df["Time"].dt.year.dropna().unique())
default_year = max(years) if years else None
year = st.sidebar.selectbox("Year", [None] + years, index=years.index(default_year)+1 if default_year else 0)

months = list(range(1, 13))
month = st.sidebar.selectbox("Month", [None] + months)

colors = sorted(df[COL["color"]].dropna().unique())
color = st.sidebar.selectbox("🎨 Color Code", colors)

# Apply filters
if year:
    df = df[df["Time"].dt.year == year]
if month:
    df = df[df["Time"].dt.month == month]

df = df[df[COL["color"]] == color]
df = df.sort_values(["製造批號", "Time"])

st.title(f"📊 SPC Dashboard — {color}")

# ======================
# GET LIMITS
# ======================
def get_limit(color, factor):
    row = limit_df[limit_df["Color_code"] == color]
    if row.empty:
        return None, None
    try:
        return (
            float(row[f"{factor} LCL"].values[0]),
            float(row[f"{factor} UCL"].values[0])
        )
    except:
        return None, None

# ======================
# SPC PLOT
# ======================
def spc_chart(df, line_col, lab_col, title, factor):
    fig, ax = plt.subplots(figsize=(14, 5))

    x = range(len(df))
    y_line = df[line_col]
    y_lab = df[lab_col]

    mean = y_line.mean()
    std = y_line.std()
    ucl_3s = mean + 3 * std
    lcl_3s = mean - 3 * std

    lcl_int, ucl_int = get_limit(color, factor)

    ax.plot(x, y_line, marker="o", label="LINE", color="blue")
    ax.plot(x, y_lab, marker="s", linestyle="--", label="LAB", color="green")

    ax.axhline(mean, color="black", linestyle="--", label="Mean")
    ax.axhline(ucl_3s, color="orange", linestyle=":", label="+3σ")
    ax.axhline(lcl_3s, color="orange", linestyle=":")

    if lcl_int is not None:
        ax.axhline(lcl_int, color="red", linestyle="-", label="Internal LCL")
    if ucl_int is not None:
        ax.axhline(ucl_int, color="red", linestyle="-", label="Internal UCL")

    for i, v in enumerate(y_line):
        if (ucl_int is not None and v > ucl_int) or (lcl_int is not None and v < lcl_int):
            ax.scatter(i, v, color="red", s=80, zorder=5)
        elif v > ucl_3s or v < lcl_3s:
            ax.scatter(i, v, color="orange", s=80, zorder=5)

    ax.set_title(title)
    ax.legend()
    ax.grid(True)

    return fig

# ======================
# COMBINED FIRST
# ======================
st.subheader("🔗 COMBINED SPC (LINE + LAB)")

fig = spc_chart(df, "dL_line", "dL_lab", "COMBINED ΔL", "ΔL")
st.pyplot(fig)

buf = io.BytesIO()
fig.savefig(buf, format="png")
buf.seek(0)
st.download_button("📥 Export PNG", buf, f"{color}_COMBINED_dL.png", "image/png")

# ======================
# INDIVIDUAL SPC
# ======================
for factor, line_c, lab_c in [
    ("ΔL", "dL_line", "dL_lab"),
    ("Δa", "da_line", "da_lab"),
    ("Δb", "db_line", "db_lab"),
]:
    st.subheader(f"{factor} SPC")
    fig = spc_chart(df, line_c, lab_c, f"{factor} SPC", factor)
    st.pyplot(fig)

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    st.download_button(
        f"📥 Export {factor}",
        buf,
        f"{color}_{factor}_SPC.png",
        "image/png"
    )
