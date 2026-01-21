import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="SPC Dashboard", layout="wide", page_icon="📊")

DATA_URL = "https://docs.google.com/spreadsheets/d/1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534/export?format=csv"
LIMIT_URL = "https://docs.google.com/spreadsheets/d/1jbP8puBraQ5Xgs9oIpJ7PlLpjIK3sltrgbrgKUcJ-Qo/export?format=csv"

@st.cache_data
def load():
    df = pd.read_csv(DATA_URL)
    limit = pd.read_csv(LIMIT_URL)

    df.columns = df.columns.str.replace("\n", " ").str.strip()
    limit.columns = limit.columns.str.replace("\n", " ").str.strip()

    return df, limit

df, limit_df = load()

# ===== SAFE COLUMN MAP =====
COL = {
    "batch": [c for c in df.columns if "製造批號" in c][0],
    "color": [c for c in df.columns if "塗料編號" in c][0],
    "time": [c for c in df.columns if c.strip() == "Time"][0],
    "dL_n": [c for c in df.columns if "正-北" in c and "ΔL" in c][0],
    "dL_s": [c for c in df.columns if "正-南" in c and "ΔL" in c][0],
    "da_n": [c for c in df.columns if "正-北" in c and "Δa" in c][0],
    "da_s": [c for c in df.columns if "正-南" in c and "Δa" in c][0],
    "db_n": [c for c in df.columns if "正-北" in c and "Δb" in c][0],
    "db_s": [c for c in df.columns if "正-南" in c and "Δb" in c][0],
}

# ===== CLEAN =====
df[COL["batch"]] = df[COL["batch"]].astype(str).str.strip()
df[COL["color"]] = df[COL["color"]].astype(str).str.strip()
df[COL["time"]] = pd.to_datetime(df[COL["time"]], errors="coerce")

# ===== SIDEBAR =====
with st.sidebar:
    color = st.selectbox("🎨 Color code", sorted(df[COL["color"]].unique()))

df = df[df[COL["color"]] == color]

# ===== SPC CALC =====
def calc_spc(n_col, s_col):
    d = df[[COL["batch"], COL["time"], n_col, s_col]].copy()
    d[n_col] = pd.to_numeric(d[n_col], errors="coerce")
    d[s_col] = pd.to_numeric(d[s_col], errors="coerce")
    d["val"] = d[[n_col, s_col]].mean(axis=1)

    return (
        d.groupby(COL["batch"])
        .agg(SPC=("val", "mean"), Time=(COL["time"], "max"))
        .reset_index()
        .sort_values("Time")
    )

# ===== CHART =====
def spc_chart(spc, title):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=spc[COL["batch"]],
        y=spc["SPC"],
        mode="lines+markers",
        name=title
    ))
    fig.update_layout(height=450, template="plotly_white")
    return fig

st.title("📊 SPC Dashboard")

MAP = {
    "ΔL": (COL["dL_n"], COL["dL_s"]),
    "Δa": (COL["da_n"], COL["da_s"]),
    "Δb": (COL["db_n"], COL["db_s"]),
}

for k, cols in MAP.items():
    spc = calc_spc(cols[0], cols[1])
    fig = spc_chart(spc, k)
    st.plotly_chart(fig, use_container_width=True)
