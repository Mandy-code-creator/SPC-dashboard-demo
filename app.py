import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# ================= CONFIG =================
st.set_page_config(
    page_title="SPC Dashboard",
    layout="wide",
    page_icon="📊"
)

# ================= GOOGLE SHEET =================
SHEET_DATA = "https://docs.google.com/spreadsheets/d/1jbP8puBraQ5Xgs9oIpJ7PlLpjIK3sltrgbrgKUcJ-Qo/export?format=csv"
SHEET_LIMIT = "https://docs.google.com/spreadsheets/d/1jbP8puBraQ5Xgs9oIpJ7PlLpjIK3sltrgbrgKUcJ-Qo/export?format=csv&gid=0"

# ================= LOAD DATA =================
@st.cache_data
def load_data():
    df = pd.read_csv(SHEET_DATA)
    limit = pd.read_csv(SHEET_LIMIT)
    return df, limit

df, limit_df = load_data()

# ================= CLEAN DATA =================
df["製造批號"] = df["製造批號"].astype(str).str.strip()
df["塗料編號"] = df["塗料編號"].astype(str).str.strip()
df["Time"] = pd.to_datetime(df["Time"], errors="coerce")

# ================= TIME FILTER =================
df["Year"] = df["Time"].dt.year
df["Month"] = df["Time"].dt.month

latest_year = int(df["Year"].max())

with st.sidebar:
    st.header("⏱ Time Filter")
    year = st.selectbox("Year", ["All"] + sorted(df["Year"].dropna().unique().tolist()), index=1)
    month = st.selectbox("Month", ["All"] + list(range(1, 13)))

    if year != "All":
        df = df[df["Year"] == int(year)]
    if month != "All":
        df = df[df["Month"] == int(month)]

# ================= COLOR SELECT =================
color_list = sorted(df["塗料編號"].dropna().unique())
color = st.sidebar.selectbox("🎨 Color Code", color_list)

df = df[df["塗料編號"] == color]

# ================= LIMIT FUNCTION =================
def get_limit(color, metric, source):
    row = limit_df[limit_df["Color_code"] == color]
    if row.empty:
        return None, None
    return (
        row[f"{source} {metric} LCL"].values[0],
        row[f"{source} {metric} UCL"].values[0],
    )

# ================= SPC CALC =================
def spc_calc(df, north, south):
    df = df.copy()
    df[north] = pd.to_numeric(df[north], errors="coerce")
    df[south] = pd.to_numeric(df[south], errors="coerce")
    df = df.dropna(subset=[north, south])

    df["SPC"] = df[[north, south]].mean(axis=1)

    spc = (
        df.groupby("製造批號")
        .agg(
            SPC_Value=("SPC", "mean"),
            Time=("Time", "max")
        )
        .reset_index()
        .sort_values("Time")
    )
    return spc

# ================= COMBINED CHART =================
def combined_chart(spc, metric):
    mean = spc["SPC_Value"].mean()
    sigma = spc["SPC_Value"].std()

    lab_lcl, lab_ucl = get_limit(color, metric, "LAB")
    line_lcl, line_ucl = get_limit(color, metric, "LINE")

    fig = go.Figure()

    colors = []
    for v in spc["SPC_Value"]:
        if line_lcl is not None and (v < line_lcl or v > line_ucl):
            colors.append("red")
        elif abs(v - mean) > 3 * sigma:
            colors.append("orange")
        else:
            colors.append("#1f77b4")

    fig.add_trace(go.Scatter(
        x=spc["製造批號"],
        y=spc["SPC_Value"],
        mode="lines+markers",
        marker=dict(color=colors, size=10),
        name="SPC"
    ))

    for val, name, style in [
        (lab_lcl, "LAB LCL", "dash"),
        (lab_ucl, "LAB UCL", "dash"),
        (line_lcl, "LINE LCL", "dot"),
        (line_ucl, "LINE UCL", "dot"),
        (mean + 3 * sigma, "+3σ", "dashdot"),
        (mean - 3 * sigma, "-3σ", "dashdot"),
    ]:
        if val is not None:
            fig.add_hline(y=val, line_dash=style, annotation_text=name)

    fig.update_layout(
        height=500,
        title=f"COMBINED SPC – {color} – {metric}",
        xaxis_title="Batch",
        yaxis_title=metric,
        template="plotly_white"
    )

    return fig

# ================= MAIN =================
st.title("📊 SPC Dashboard")

metrics = {
    "ΔL": ("正-北\n ΔL", "正-南\nΔL"),
    "Δa": ("正-北\nΔa", "正-南\nΔa"),
    "Δb": ("正-北\nΔb", "正-南\nΔb"),
}

for metric, cols in metrics.items():
    spc = spc_calc(df, cols[0], cols[1])
    fig = combined_chart(spc, metric)
    st.plotly_chart(fig, use_container_width=True)

    st.download_button(
        f"⬇ Download {metric} PNG",
        fig.to_image(format="png"),
        file_name=f"{color}_{metric}_SPC.png"
    )
