import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="SPC Dashboard", layout="wide")

# =====================
# GOOGLE SHEET URL
# =====================
DATA_URL = "https://docs.google.com/spreadsheets/d/1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534/export?format=csv"
LIMIT_URL = "https://docs.google.com/spreadsheets/d/1jbP8puBraQ5Xgs9oIpJ7PlLpjIK3sltrgbrgKUcJ-Qo/export?format=csv"

# =====================
# LOAD DATA
# =====================
@st.cache_data(ttl=300)
def load_data():
    return pd.read_csv(DATA_URL)

@st.cache_data(ttl=300)
def load_limit():
    return pd.read_csv(LIMIT_URL)

df = load_data()
limit_df = load_limit()

# =====================
# BASIC PREPROCESS
# =====================
df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
df["Year"] = df["Time"].dt.year
df["Month"] = df["Time"].dt.month

# =====================
# SAFE COLUMN FINDER
# =====================
def find_col(keyword1, keyword2):
    cols = [c for c in df.columns if keyword1 in c and keyword2 in c]
    return cols[0] if len(cols) > 0 else None

# LINE ΔL Δa Δb (AN TOÀN – KHÔNG KEYERROR)
north_L = find_col("正-北", "ΔL")
south_L = find_col("正-南", "ΔL")
north_a = find_col("正-北", "Δa")
south_a = find_col("正-南", "Δa")
north_b = find_col("正-北", "Δb")
south_b = find_col("正-南", "Δb")

if north_L and south_L:
    df["dL_line"] = df[[north_L, south_L]].mean(axis=1)
if north_a and south_a:
    df["da_line"] = df[[north_a, south_a]].mean(axis=1)
if north_b and south_b:
    df["db_line"] = df[[north_b, south_b]].mean(axis=1)

# =====================
# SIDEBAR FILTER
# =====================
st.sidebar.header("Filter")

color = st.sidebar.selectbox(
    "Color code",
    sorted(df["塗料編號"].dropna().unique())
)

years = sorted(df["Year"].dropna().unique())
year = st.sidebar.selectbox("Year", years)

months = sorted(df[df["Year"] == year]["Month"].dropna().unique())
month = st.sidebar.selectbox("Month", months)

df_f = df[
    (df["塗料編號"] == color) &
    (df["Year"] == year) &
    (df["Month"] == month)
]

if df_f.empty:
    st.warning("No data for selected filter")
    st.stop()

# =====================
# LOAD LIMIT FOR COLOR
# =====================
limit_row = limit_df[limit_df["Color_code"] == color]

def get_limit(name):
    if limit_row.empty:
        return None, None
    lcl_col = f"{name} LCL"
    ucl_col = f"{name} UCL"
    if lcl_col not in limit_row.columns:
        return None, None
    lcl = limit_row[lcl_col].iloc[0]
    ucl = limit_row[ucl_col].iloc[0]
    if pd.isna(lcl) or pd.isna(ucl):
        return None, None
    return float(lcl), float(ucl)

LCL_L, UCL_L = get_limit("ΔL")

# =====================
# SPC CHART
# =====================
def spc_chart(data, col, title, lcl_internal, ucl_internal):
    values = data[col].dropna()
    mean = values.mean()
    std = values.std()

    ucl_3s = mean + 3 * std
    lcl_3s = mean - 3 * std

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(values.index, values.values, marker="o")

    ax.axhline(mean, linestyle="--", label="Mean")
    ax.axhline(ucl_3s, linestyle="--", color="orange", label="+3σ")
    ax.axhline(lcl_3s, linestyle="--", color="orange", label="-3σ")

    if lcl_internal is not None:
        ax.axhline(lcl_internal, color="red", label="Internal LCL")
        ax.axhline(ucl_internal, color="red", label="Internal UCL")

    for i, v in zip(values.index, values.values):
        if lcl_internal is not None and (v < lcl_internal or v > ucl_internal):
            ax.scatter(i, v, color="red")
        elif v < lcl_3s or v > ucl_3s:
            ax.scatter(i, v, color="orange")

    ax.set_title(title)
    ax.legend()
    return fig

# =====================
# MAIN VIEW
# =====================
st.title("SPC LINE ΔL Dashboard")

fig = spc_chart(df_f, "dL_line", f"LINE ΔL – {color}", LCL_L, UCL_L)
st.pyplot(fig)
