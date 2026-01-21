import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

st.set_page_config(page_title="SPC Color Dashboard", layout="wide")

# =============================
# GOOGLE SHEET LINKS
# =============================
DATA_SHEET = "https://docs.google.com/spreadsheets/d/1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534/export?format=csv"
LIMIT_SHEET = "https://docs.google.com/spreadsheets/d/1jbP8puBraQ5Xgs9oIpJ7PlLpjIK3sltrgbrgKUcJ-Qo/export?format=csv"

# =============================
# LOAD DATA
# =============================
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_SHEET)
    df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
    return df

@st.cache_data
def load_limits():
    return pd.read_csv(LIMIT_SHEET)

df = load_data()
limit_df = load_limits()

st.success("Data loaded successfully from Google Sheets")

# =============================
# STANDARDIZE COLUMN NAMES
# =============================
df.columns = df.columns.str.replace("\n", "").str.strip()

# LAB (input)
df["dL_lab"] = df["入料檢測 ΔL 正面"]
df["da_lab"] = df["入料檢測 Δa 正面"]
df["db_lab"] = df["入料檢測 Δb 正面"]

# LINE (average N + S)
df["dL_line"] = df[["正-北 ΔL", "正-南 ΔL"]].mean(axis=1)
df["da_line"] = df[["正-北 Δa", "正-南 Δa"]].mean(axis=1)
df["db_line"] = df[["正-北 Δb", "正-南 Δb"]].mean(axis=1)

# =============================
# TIME FILTER UI
# =============================
df["Year"] = df["Time"].dt.year
df["Month"] = df["Time"].dt.month

latest_year = int(df["Year"].max())

st.sidebar.header("⏱ Time Filter")
year_sel = st.sidebar.selectbox("Year", ["All"] + sorted(df["Year"].dropna().unique().astype(int).tolist()),
                                index=sorted(df["Year"].unique()).index(latest_year) + 1)

month_sel = st.sidebar.selectbox("Month", ["All"] + list(range(1, 13)))

if year_sel != "All":
    df = df[df["Year"] == year_sel]
if month_sel != "All":
    df = df[df["Month"] == month_sel]

# =============================
# COLOR CODE FILTER
# =============================
color_codes = df["塗料編號"].dropna().unique()
color_sel = st.sidebar.selectbox("Color Code", color_codes)
df = df[df["塗料編號"] == color_sel]

# =============================
# GET LIMITS SAFELY
# =============================
def get_limits(color, prefix):
    row = limit_df[limit_df["Color_code"] == color]
    if row.empty:
        return None, None
    return (
        row[f"{prefix} LCL"].values[0],
        row[f"{prefix} UCL"].values[0]
    )

lab_limits = {
    "dL": get_limits(color_sel, "ΔL"),
    "da": get_limits(color_sel, "Δa"),
    "db": get_limits(color_sel, "Δb")
}

line_limits = lab_limits  # nếu sheet 2 sau này thêm LINE thì đổi ở đây

# =============================
# SPC CHART FUNCTION
# =============================
def spc_chart(data, col, title, lcl, ucl):
    fig, ax = plt.subplots(figsize=(10, 4))

    mean = data[col].mean()
    std = data[col].std()

    for i, v in enumerate(data[col]):
        if lcl is not None and (v < lcl or v > ucl):
            ax.scatter(i, v, color="red")
        elif abs(v - mean) > 3 * std:
            ax.scatter(i, v, color="orange")
        else:
            ax.scatter(i, v, color="black")

    ax.plot(data[col].values, alpha=0.4)

    ax.axhline(mean, color="blue", linestyle="--", label="Mean")
    ax.axhline(mean + 3 * std, color="orange", linestyle=":")
    ax.axhline(mean - 3 * std, color="orange", linestyle=":")

    if lcl is not None:
        ax.axhline(lcl, color="red")
        ax.axhline(ucl, color="red")

    ax.set_title(title)
    ax.legend()
    return fig

# =============================
# DASHBOARD
# =============================
st.title("🎨 SPC Color Control Dashboard")

tabs = st.tabs(["COMBINED", "LAB", "LINE"])

with tabs[0]:
    st.subheader("COMBINED ΔL")
    fig = spc_chart(df, "dL_line", "COMBINED ΔL",
                    line_limits["dL"][0], line_limits["dL"][1])
    st.pyplot(fig)

with tabs[1]:
    st.subheader("LAB SPC")
    st.pyplot(spc_chart(df, "dL_lab", "LAB ΔL", *lab_limits["dL"]))
    st.pyplot(spc_chart(df, "da_lab", "LAB Δa", *lab_limits["da"]))
    st.pyplot(spc_chart(df, "db_lab", "LAB Δb", *lab_limits["db"]))

with tabs[2]:
    st.subheader("LINE SPC")
    st.pyplot(spc_chart(df, "dL_line", "LINE ΔL", *line_limits["dL"]))
    st.pyplot(spc_chart(df, "da_line", "LINE Δa", *line_limits["da"]))
    st.pyplot(spc_chart(df, "db_line", "LINE Δb", *line_limits["db"]))

# =============================
# SUMMARY NG
# =============================
st.subheader("📊 NG Summary by Month")

ng = df[
    (df["dL_line"] < line_limits["dL"][0]) |
    (df["dL_line"] > line_limits["dL"][1])
]

summary = ng.groupby(["Year", "Month"]).size().reset_index(name="NG count")
st.dataframe(summary)
