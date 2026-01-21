import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(
    page_title="SPC Dashboard",
    layout="wide",
    page_icon="📊"
)

# ================== GOOGLE SHEET ==================
DATA_URL = "https://docs.google.com/spreadsheets/d/1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534/export?format=csv"
LIMIT_URL = "https://docs.google.com/spreadsheets/d/1jbP8puBraQ5Xgs9oIpJ7PlLpjIK3sltrgbrgKUcJ-Qo/export?format=csv"

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_URL)
    limit = pd.read_csv(LIMIT_URL)

    # normalize header
    df.columns = df.columns.str.replace("\n", " ").str.strip()
    limit.columns = limit.columns.str.replace("\n", " ").str.strip()

    return df, limit

df, limit_df = load_data()

# ================== SAFE COLUMN MAP ==================
COL = {
    "batch":  [c for c in df.columns if "製造批號" in c][0],
    "color":  [c for c in df.columns if "塗料編號" in c][0],
    "time":   [c for c in df.columns if c == "Time"][0],

    "dL_n":   [c for c in df.columns if "正-北" in c and "ΔL" in c][0],
    "dL_s":   [c for c in df.columns if "正-南" in c and "ΔL" in c][0],
    "da_n":   [c for c in df.columns if "正-北" in c and "Δa" in c][0],
    "da_s":   [c for c in df.columns if "正-南" in c and "Δa" in c][0],
    "db_n":   [c for c in df.columns if "正-北" in c and "Δb" in c][0],
    "db_s":   [c for c in df.columns if "正-南" in c and "Δb" in c][0],

    "lab_dL": [c for c in df.columns if "入料檢測" in c and "ΔL" in c][0],
    "lab_da": [c for c in df.columns if "入料檢測" in c and "Δa" in c][0],
    "lab_db": [c for c in df.columns if "入料檢測" in c and "Δb" in c][0],
}

# ================== CLEAN ==================
df[COL["batch"]] = df[COL["batch"]].astype(str).str.strip()
df[COL["color"]] = df[COL["color"]].astype(str).str.strip()
df[COL["time"]]  = pd.to_datetime(df[COL["time"]], errors="coerce")

df["Year"] = df[COL["time"]].dt.year
df["Month"] = df[COL["time"]].dt.month

# ================== SIDEBAR ==================
with st.sidebar:
    st.header("⏱ Time Filter")

    latest_year = int(df["Year"].max())
    year = st.selectbox("Year", ["All"] + sorted(df["Year"].dropna().unique()),
                        index=sorted(df["Year"].dropna().unique()).index(latest_year)+1)
    month = st.selectbox("Month", ["All"] + list(range(1, 13)))

    if year != "All":
        df = df[df["Year"] == int(year)]
    if month != "All":
        df = df[df["Month"] == int(month)]

    st.divider()
    color = st.selectbox("🎨 Color code", sorted(df[COL["color"]].unique()))

df = df[df[COL["color"]] == color]

# ================== LIMIT ==================
def get_limit(metric, source):
    row = limit_df[limit_df["Color_code"] == color]
    if row.empty:
        return None, None
    return (
        row[f"{source} {metric} LCL"].values[0],
        row[f"{source} {metric} UCL"].values[0]
    )

# ================== SPC CALC ==================
def calc_spc(n_col, s_col):
    d = df[[COL["batch"], COL["time"], n_col, s_col]].copy()
    d[n_col] = pd.to_numeric(d[n_col], errors="coerce")
    d[s_col] = pd.to_numeric(d[s_col], errors="coerce")

    d["value"] = d[[n_col, s_col]].mean(axis=1)

    return (
        d.groupby(COL["batch"])
        .agg(
            SPC=("value", "mean"),
            Time=(COL["time"], "max")
        )
        .reset_index()
        .sort_values("Time")
    )

# ================== SPC CHART ==================
def spc_chart(spc, metric, combined=True):
    mean = spc["SPC"].mean()
    std = spc["SPC"].std()

    lab_lcl, lab_ucl = get_limit(metric, "LAB")
    line_lcl, line_ucl = get_limit(metric, "LINE")

    colors = []
    for v in spc["SPC"]:
        if line_lcl is not None and (v < line_lcl or v > line_ucl):
            colors.append("red")        # internal spec NG
        elif abs(v - mean) > 3 * std:
            colors.append("orange")     # 3σ NG
        else:
            colors.append("#1f77b4")

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=spc[COL["batch"]],
        y=spc["SPC"],
        mode="lines+markers",
        marker=dict(size=10, color=colors),
        name="SPC"
    ))

    # limits
    for val, name, style in [
        (lab_lcl, "LAB LCL", "dash"),
        (lab_ucl, "LAB UCL", "dash"),
        (line_lcl, "LINE LCL", "dot"),
        (line_ucl, "LINE UCL", "dot"),
        (mean + 3*std, "+3σ", "dashdot"),
        (mean - 3*std, "-3σ", "dashdot"),
    ]:
        if val is not None:
            fig.add_hline(y=val, line_dash=style, annotation_text=name)

    fig.update_layout(
        height=450,
        template="plotly_white",
        title=f"{metric} SPC – {color}",
        xaxis_title="Batch",
        yaxis_title=metric
    )
    return fig

# ================== MAIN ==================
st.title("📊 SPC Dashboard")

MAP = {
    "ΔL": (COL["dL_n"], COL["dL_s"]),
    "Δa": (COL["da_n"], COL["da_s"]),
    "Δb": (COL["db_n"], COL["db_s"]),
}

for metric, cols in MAP.items():
    spc = calc_spc(cols[0], cols[1])

    st.subheader(f"COMBINED {metric}")
    fig = spc_chart(spc, metric)
    st.plotly_chart(fig, use_container_width=True)

    st.download_button(
        f"⬇ Download {metric}",
        fig.to_image(format="png"),
        file_name=f"{color}_{metric}_SPC.png"
    )
