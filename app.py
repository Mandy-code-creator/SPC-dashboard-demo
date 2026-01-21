import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="SPC Color Dashboard", layout="wide")

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
    return pd.read_csv(DATA_URL)

@st.cache_data
def load_limits():
    return pd.read_csv(LIMIT_URL)

df = load_data()
limit_df = load_limits()

st.success("Data loaded successfully from Google Sheets")

# =========================
# BASIC CLEANING
# =========================
df["Time"] = pd.to_datetime(df["Time"], errors="coerce")

df["dL_lab"] = df["入料檢測\n ΔL 正面"]
df["da_lab"] = df["入料檢測\nΔa 正面"]
df["db_lab"] = df["入料檢測\nΔb 正面"]

df["dL_line"] = df["Average value\nΔL 正面"]
df["da_line"] = df["Average value\n Δa 正面"]
df["db_line"] = df["Average value\nΔb 正面"]

# =========================
# FILTERS
# =========================
st.sidebar.header("Filters")

color_code = st.sidebar.selectbox(
    "Color Code",
    sorted(df["塗料編號"].dropna().unique())
)

time_range = st.sidebar.date_input(
    "Time range",
    value=(df["Time"].min().date(), df["Time"].max().date())
)

df = df[
    (df["塗料編號"] == color_code) &
    (df["Time"].dt.date >= time_range[0]) &
    (df["Time"].dt.date <= time_range[1])
]

# =========================
# GET LIMITS BY COLOR CODE
# =========================
limit_row = limit_df[limit_df["Color_code"] == color_code]

def get_limit(col):
    if limit_row.empty:
        return None, None
    return float(limit_row[col + "_LCL"]), float(limit_row[col + "_UCL"])

lab_limits = {
    "dL": get_limit("ΔL"),
    "da": get_limit("Δa"),
    "db": get_limit("Δb"),
}

line_limits = lab_limits  # nếu sau này có LINE riêng → đổi tại đây

# =========================
# SIDEBAR – CONTROL LIMITS
# =========================
st.sidebar.header("LAB Control Limits")

lab_LCL_L, lab_UCL_L = st.sidebar.number_input(
    "LAB ΔL LCL", value=lab_limits["dL"][0]), st.sidebar.number_input(
    "LAB ΔL UCL", value=lab_limits["dL"][1])

lab_LCL_a, lab_UCL_a = st.sidebar.number_input(
    "LAB Δa LCL", value=lab_limits["da"][0]), st.sidebar.number_input(
    "LAB Δa UCL", value=lab_limits["da"][1])

lab_LCL_b, lab_UCL_b = st.sidebar.number_input(
    "LAB Δb LCL", value=lab_limits["db"][0]), st.sidebar.number_input(
    "LAB Δb UCL", value=lab_limits["db"][1])

st.sidebar.header("LINE Control Limits")

line_LCL_L, line_UCL_L = lab_LCL_L, lab_UCL_L
line_LCL_a, line_UCL_a = lab_LCL_a, lab_UCL_a
line_LCL_b, line_UCL_b = lab_LCL_b, lab_UCL_b

# =========================
# SPC FUNCTION
# =========================
def spc_chart(df, y_col, title, lcl, ucl):
    y = df[y_col].dropna()
    mean = y.mean()
    std = y.std()

    ucl_auto = mean + 3 * std
    lcl_auto = mean - 3 * std

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(y.index, y, marker="o", label="Data")
    ax.axhline(mean, linestyle="--", label="Mean")
    ax.axhline(ucl_auto, linestyle="--", color="red", label="UCL ±3σ")
    ax.axhline(lcl_auto, linestyle="--", color="red", label="LCL ±3σ")

    ax.axhline(ucl, linestyle="-.", color="orange", label="Manual UCL")
    ax.axhline(lcl, linestyle="-.", color="orange", label="Manual LCL")

    ax.set_title(title)
    ax.legend()
    st.pyplot(fig)

# =========================
# DASHBOARD
# =========================
st.title("SPC Color Control Dashboard")

st.subheader("COMBINED SPC (LAB vs LINE – LINE LIMIT PRIORITY)")
spc_chart(df, "dL_line", "COMBINED ΔL", line_LCL_L, line_UCL_L)

st.subheader("LAB SPC")
spc_chart(df, "dL_lab", "LAB ΔL", lab_LCL_L, lab_UCL_L)
spc_chart(df, "da_lab", "LAB Δa", lab_LCL_a, lab_UCL_a)
spc_chart(df, "db_lab", "LAB Δb", lab_LCL_b, lab_UCL_b)

st.subheader("LINE SPC")
spc_chart(df, "dL_line", "LINE ΔL", line_LCL_L, line_UCL_L)
spc_chart(df, "da_line", "LINE Δa", line_LCL_a, line_UCL_a)
spc_chart(df, "db_line", "LINE Δb", line_LCL_b, line_UCL_b)
