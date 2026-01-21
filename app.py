import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="SPC Color Dashboard", layout="wide")

# =====================================================
# GOOGLE SHEET LINKS
# =====================================================
DATA_SHEET = (
    "https://docs.google.com/spreadsheets/d/"
    "1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534"
    "/export?format=csv"
)

LIMIT_SHEET = (
    "https://docs.google.com/spreadsheets/d/"
    "1jbP8puBraQ5Xgs9oIpJ7PlLpjIK3sltrgbrgKUcJ-Qo"
    "/export?format=csv"
)

# =====================================================
# LOAD DATA
# =====================================================
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_SHEET)
    df.columns = df.columns.str.replace("\n", " ").str.strip()
    df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
    return df


@st.cache_data
def load_limits():
    df = pd.read_csv(LIMIT_SHEET)
    df.columns = df.columns.str.strip()
    return df


df = load_data()
limit_df = load_limits()

st.success("Data loaded successfully from Google Sheets")

# =====================================================
# PREPARE DATA
# =====================================================
# LAB (Input)
df["dL_lab"] = df["入料檢測 ΔL 正面"]
df["da_lab"] = df["入料檢測 Δa 正面"]
df["db_lab"] = df["入料檢測 Δb 正面"]

# LINE (Average North + South)
df["dL_line"] = df[["正-北 ΔL", "正-南 ΔL"]].mean(axis=1)
df["da_line"] = df[["正-北 Δa", "正-南 Δa"]].mean(axis=1)
df["db_line"] = df[["正-北 Δb", "正-南 Δb"]].mean(axis=1)

# Time
df["Year"] = df["Time"].dt.year
df["Month"] = df["Time"].dt.month

# =====================================================
# SIDEBAR – TIME FILTER
# =====================================================
st.sidebar.header("⏱ Time Filter")

years = sorted(df["Year"].dropna().unique().astype(int))
latest_year = max(years)

year_sel = st.sidebar.selectbox(
    "Year",
    ["All"] + years,
    index=years.index(latest_year) + 1
)

month_sel = st.sidebar.selectbox(
    "Month",
    ["All"] + list(range(1, 13))
)

if year_sel != "All":
    df = df[df["Year"] == year_sel]

if month_sel != "All":
    df = df[df["Month"] == month_sel]

# =====================================================
# SIDEBAR – COLOR CODE
# =====================================================
st.sidebar.header("🎨 Color Filter")
color_codes = df["塗料編號"].dropna().unique()
color_sel = st.sidebar.selectbox("Color Code", color_codes)
df = df[df["塗料編號"] == color_sel]

# =====================================================
# GET LIMITS SAFELY
# =====================================================
def get_limit(color, col):
    row = limit_df[limit_df["Color_code"] == color]
    if row.empty or col not in row.columns:
        return None
    return row[col].values[0]


lab_limits = {
    "dL": (
        get_limit(color_sel, "ΔL LCL"),
        get_limit(color_sel, "ΔL UCL"),
    ),
    "da": (
        get_limit(color_sel, "Δa LCL"),
        get_limit(color_sel, "Δa UCL"),
    ),
    "db": (
        get_limit(color_sel, "Δb LCL"),
        get_limit(color_sel, "Δb UCL"),
    ),
}

# hiện tại LINE dùng chung limit (sau này tách sheet thì đổi)
line_limits = lab_limits

# =====================================================
# SPC CHART FUNCTION
# =====================================================
def spc_chart(data, col, title, lcl, ucl):
    fig, ax = plt.subplots(figsize=(11, 4))

    y = data[col].dropna().values
    mean = np.mean(y)
    std = np.std(y)

    for i, v in enumerate(y):
        if lcl is not None and ucl is not None and (v < lcl or v > ucl):
            ax.scatter(i, v, color="red", zorder=3)
        elif abs(v - mean) > 3 * std:
            ax.scatter(i, v, color="orange", zorder=3)
        else:
            ax.scatter(i, v, color="black", zorder=3)

    ax.plot(y, alpha=0.4)

    ax.axhline(mean, color="blue", linestyle="--", label="Mean")
    ax.axhline(mean + 3 * std, color="orange", linestyle=":")
    ax.axhline(mean - 3 * std, color="orange", linestyle=":")

    if lcl is not None and ucl is not None:
        ax.axhline(lcl, color="red", label="Internal LCL")
        ax.axhline(ucl, color="red", label="Internal UCL")

    ax.set_title(title)
    ax.legend()
    return fig


# =====================================================
# DASHBOARD
# =====================================================
st.title("🎨 SPC Color Control Dashboard")

# -----------------------------------------------------
# COMBINED – HIỂN THỊ ĐẦU TIÊN
# -----------------------------------------------------
st.subheader("📌 COMBINED SPC – LAB & LINE Overview")

fig = spc_chart(
    df,
    "dL_line",
    "COMBINED ΔL (Priority: LINE)",
    line_limits["dL"][0],
    line_limits["dL"][1],
)
st.pyplot(fig)

st.markdown("---")

# -----------------------------------------------------
# LAB / LINE TABS
# -----------------------------------------------------
tabs = st.tabs(["LAB SPC", "LINE SPC"])

with tabs[0]:
    st.subheader("LAB SPC")
    st.pyplot(spc_chart(df, "dL_lab", "LAB ΔL", *lab_limits["dL"]))
    st.pyplot(spc_chart(df, "da_lab", "LAB Δa", *lab_limits["da"]))
    st.pyplot(spc_chart(df, "db_lab", "LAB Δb", *lab_limits["db"]))

with tabs[1]:
    st.subheader("LINE SPC")
    st.pyplot(spc_chart(df, "dL_line", "LINE ΔL", *line_limits["dL"]))
    st.pyplot(spc_chart(df, "da_line", "LINE Δa", *line_limits["da"]))
    st.pyplot(spc_chart(df, "db_line", "LINE Δb", *line_limits["db"]))

# =====================================================
# SUMMARY NG
# =====================================================
st.subheader("📊 NG Summary by Month")

if line_limits["dL"][0] is not None:
    ng_df = df[
        (df["dL_line"] < line_limits["dL"][0])
        | (df["dL_line"] > line_limits["dL"][1])
    ]

    summary = (
        ng_df.groupby(["Year", "Month"])
        .size()
        .reset_index(name="NG Count")
    )

    st.dataframe(summary)
else:
    st.info("No internal limits found for this color code.")
