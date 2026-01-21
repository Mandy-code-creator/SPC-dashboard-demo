import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="SPC Color Dashboard", layout="wide")

# ======================
# CONFIG – GOOGLE SHEET
# ======================
DATA_SHEET_URL = "https://docs.google.com/spreadsheets/d/1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534/export?format=csv"
LIMIT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1jbP8puBraQ5Xgs9oIpJ7PlLpjIK3sltrgbrgKUcJ-Qo/export?format=csv"

# ======================
# LOAD DATA
# ======================
@st.cache_data(ttl=300)
def load_data():
    return pd.read_csv(DATA_SHEET_URL)

@st.cache_data(ttl=300)
def load_limit():
    return pd.read_csv(LIMIT_SHEET_URL)

df = load_data()
limit_df = load_limit()

# ======================
# PREPROCESS
# ======================
df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
df["Year"] = df["Time"].dt.year
df["Month"] = df["Time"].dt.month

# Chuẩn hóa cột cần dùng
df["dL_lab"] = df["Average value\nΔL 正面"]
df["da_lab"] = df["Average value\n Δa 正面"]
df["db_lab"] = df["Average value\nΔb 正面"]

df["dL_line"] = df[["正-北\nΔL", "正-南\nΔL"]].mean(axis=1)
df["da_line"] = df[["正-北\nΔa", "正-南\nΔa"]].mean(axis=1)
df["db_line"] = df[["正-北\nΔb", "正-南\nΔb"]].mean(axis=1)

# ======================
# SIDEBAR – FILTER
# ======================
st.sidebar.header("🔎 Filter")

color = st.sidebar.selectbox(
    "Color code",
    sorted(df["塗料編號"].dropna().unique())
)

years = sorted(df["Year"].dropna().unique())
year = st.sidebar.selectbox("Year", years)

months = sorted(df[df["Year"] == year]["Month"].unique())
month = st.sidebar.selectbox("Month", months)

df_f = df[
    (df["塗料編號"] == color) &
    (df["Year"] == year) &
    (df["Month"] == month)
]

# ======================
# LOAD LIMIT ROW
# ======================
limit_row = limit_df[limit_df["Color_code"] == color]

def get_limit(source, name):
    if limit_row.empty:
        return None, None

    lcl_col = f"{source} {name} LCL"
    ucl_col = f"{source} {name} UCL"

    if lcl_col not in limit_row.columns:
        return None, None

    lcl = limit_row[lcl_col].iloc[0]
    ucl = limit_row[ucl_col].iloc[0]

    if pd.isna(lcl) or pd.isna(ucl):
        return None, None

    return float(lcl), float(ucl)

# ======================
# SIDEBAR – LIMIT VIEW
# ======================
st.sidebar.markdown("---")
st.sidebar.subheader("🔹 LAB Control Limits")
lab_LCL_L, lab_UCL_L = get_limit("LAB", "ΔL")
lab_LCL_a, lab_UCL_a = get_limit("LAB", "Δa")
lab_LCL_b, lab_UCL_b = get_limit("LAB", "Δb")

st.sidebar.write("ΔL:", lab_LCL_L, lab_UCL_L)
st.sidebar.write("Δa:", lab_LCL_a, lab_UCL_a)
st.sidebar.write("Δb:", lab_LCL_b, lab_UCL_b)

st.sidebar.markdown("---")
st.sidebar.subheader("🔹 LINE Control Limits")
line_LCL_L, line_UCL_L = get_limit("LINE", "ΔL")
line_LCL_a, line_UCL_a = get_limit("LINE", "Δa")
line_LCL_b, line_UCL_b = get_limit("LINE", "Δb")

st.sidebar.write("ΔL:", line_LCL_L, line_UCL_L)
st.sidebar.write("Δa:", line_LCL_a, line_UCL_a)
st.sidebar.write("Δb:", line_LCL_b, line_UCL_b)

# ======================
# SPC CHART FUNCTION
# ======================
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

# ======================
# MAIN VIEW
# ======================
st.title("🎨 SPC Color Control Dashboard")

st.subheader("📊 COMBINED SPC (LAB vs LINE)")
fig = spc_chart(df_f, "dL_line", "COMBINED ΔL (Priority LINE)", line_LCL_L, line_UCL_L)
st.pyplot(fig)

st.subheader("📈 LAB SPC")
col1, col2, col3 = st.columns(3)
with col1:
    st.pyplot(spc_chart(df_f, "dL_lab", "LAB ΔL", lab_LCL_L, lab_UCL_L))
with col2:
    st.pyplot(spc_chart(df_f, "da_lab", "LAB Δa", lab_LCL_a, lab_UCL_a))
with col3:
    st.pyplot(spc_chart(df_f, "db_lab", "LAB Δb", lab_LCL_b, lab_UCL_b))

st.subheader("🏭 LINE SPC")
col1, col2, col3 = st.columns(3)
with col1:
    st.pyplot(spc_chart(df_f, "dL_line", "LINE ΔL", line_LCL_L, line_UCL_L))
with col2:
    st.pyplot(spc_chart(df_f, "da_line", "LINE Δa", line_LCL_a, line_UCL_a))
with col3:
    st.pyplot(spc_chart(df_f, "db_line", "LINE Δb", line_LCL_b, line_UCL_b))
