import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import io

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="SPC Color Dashboard",
    layout="wide",
    page_icon="📊"
)

# =========================
# GOOGLE SHEET LINKS
# =========================
DATA_URL = "https://docs.google.com/spreadsheets/d/1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534/export?format=csv"
LIMIT_URL = "https://docs.google.com/spreadsheets/d/1jbP8puBraQ5Xgs9oIpJ7PlLpjIK3sltrgbrgKUcJ-Qo/export?format=csv"

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_URL)
    df.columns = (
        df.columns
        .str.replace("\n", " ", regex=False)
        .str.replace("  ", " ")
        .str.strip()
    )
    df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
    return df

@st.cache_data
def load_limit():
    lim = pd.read_csv(LIMIT_URL)
    lim.columns = lim.columns.str.strip()
    return lim

df = load_data()
limit_df = load_limit()

# =========================
# COLUMN MAP (AFTER NORMALIZE)
# =========================
COL = {
    "color": "塗料編號",
    "batch": "製造批號",

    "dL_N": "正-北 ΔL",
    "dL_S": "正-南 ΔL",
    "da_N": "正-北 Δa",
    "da_S": "正-南 Δa",
    "db_N": "正-北 Δb",
    "db_S": "正-南 Δb",

    "lab_dL": "入料檢測 ΔL 正面",
    "lab_da": "入料檢測 Δa 正面",
    "lab_db": "入料檢測 Δb 正面",
}

# =========================
# CALCULATE LINE (COIL LEVEL)
# =========================
df["dL_line"] = df[[COL["dL_N"], COL["dL_S"]]].astype(float).mean(axis=1)
df["da_line"] = df[[COL["da_N"], COL["da_S"]]].astype(float).mean(axis=1)
df["db_line"] = df[[COL["db_N"], COL["db_S"]]].astype(float).mean(axis=1)

df["dL_lab"] = df[COL["lab_dL"]]
df["da_lab"] = df[COL["lab_da"]]
df["db_lab"] = df[COL["lab_db"]]

# =========================
# SIDEBAR FILTER
# =========================
st.sidebar.header("🎛 Filter")

years = sorted(df["Time"].dt.year.dropna().unique())
default_year = max(years) if years else None
year = st.sidebar.selectbox(
    "Year", [None] + years,
    index=years.index(default_year) + 1 if default_year else 0
)

month = st.sidebar.selectbox("Month", [None] + list(range(1, 13)))

colors = sorted(df[COL["color"]].dropna().unique())
color = st.sidebar.selectbox("🎨 Color Code", colors)

if year:
    df = df[df["Time"].dt.year == year]
if month:
    df = df[df["Time"].dt.month == month]

df = df[df[COL["color"]] == color]

# =========================
# AGGREGATE BY BATCH (SPC CORE)
# =========================
batch_df = (
    df
    .groupby(COL["batch"], as_index=False)
    .agg(
        dL_line=("dL_line", "mean"),
        da_line=("da_line", "mean"),
        db_line=("db_line", "mean"),

        dL_lab=("dL_lab", "mean"),
        da_lab=("da_lab", "mean"),
        db_lab=("db_lab", "mean"),

        batch_time=("Time", "min")
    )
    .sort_values("batch_time")
    .reset_index(drop=True)
)

st.title(f"📊 X-bar Control Chart — {color}")
st.caption("Each point = average of coils within one batch")

# =========================
# GET LIMIT (LAB / LINE)
# =========================
def get_limit(color, factor):
    row = limit_df[limit_df["Color_code"] == color]
    if row.empty:
        return None, None
    try:
        return (
            float(row[f"{factor} LCL"].values[0]),
            float(row[f"{factor} UCL"].values[0]),
        )
    except:
        return None, None

# =========================
# SPC CHART (LAB + LINE)
# =========================
def spc_chart(df, line_col, lab_col, factor):
    fig, ax = plt.subplots(figsize=(14, 5))

    x = np.arange(1, len(df) + 1)
    y_line = df[line_col]
    y_lab = df[lab_col]

    lab_lcl, lab_ucl = get_limit(color, factor)
    line_lcl, line_ucl = get_limit(color, factor)

    # DATA
    ax.plot(x, y_lab, marker="^", color="green", label=f"{factor}* 入料")
    ax.plot(x, y_line, marker="o", color="orange", label=f"{factor}* 產出")

    # LAB LIMIT
    if lab_lcl is not None:
        ax.axhline(lab_lcl, color="purple", label="LCL 入料")
    if lab_ucl is not None:
        ax.axhline(lab_ucl, color="purple", label="UCL 入料")

    # LINE LIMIT
    if line_lcl is not None:
        ax.axhline(line_lcl, color="red", linestyle="--", label="LCL 產出")
    if line_ucl is not None:
        ax.axhline(line_ucl, color="red", linestyle="--", label="UCL 產出")

    # NG POINT (LINE ONLY)
    for i, v in enumerate(y_line):
        if line_lcl is not None and line_ucl is not None:
            if v < line_lcl or v > line_ucl:
                ax.scatter(x[i], v, color="red", s=90, zorder=5)

    ax.set_title(f"X-bar Control chart {factor}*")
    ax.set_xlabel("Batch order")
    ax.set_ylabel(factor)
    ax.legend()
    ax.grid(True)

    return fig

# =========================
# COMBINED SPC FIRST (ΔL)
# =========================
st.subheader("🔗 COMBINED SPC (Batch Average)")

fig = spc_chart(batch_df, "dL_line", "dL_lab", "ΔL")
st.pyplot(fig)

buf = io.BytesIO()
fig.savefig(buf, format="png")
buf.seek(0)
st.download_button("📥 Export ΔL SPC", buf, f"{color}_ΔL_SPC.png", "image/png")

# =========================
# INDIVIDUAL SPC
# =========================
for factor, line_c, lab_c in [
    ("ΔL", "dL_line", "dL_lab"),
    ("Δa", "da_line", "da_lab"),
    ("Δb", "db_line", "db_lab"),
]:
    st.subheader(f"{factor} SPC")
    fig = spc_chart(batch_df, line_c, lab_c, factor)
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
