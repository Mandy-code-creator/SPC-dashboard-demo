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
    df.columns = (
        df.columns
        .str.replace("\n", " ", regex=False)
        .str.replace("  ", " ", regex=False)
        .str.strip()
    )
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
# SAFE COLUMN FINDER
# =====================================================
def find_col(keywords):
    for c in df.columns:
        if all(k in c for k in keywords):
            return c
    return None


# =====================================================
# MAP DATA (100% SAFE)
# =====================================================
df["dL_lab"] = df[find_col(["入料檢測", "ΔL"])]
df["da_lab"] = df[find_col(["入料檢測", "Δa"])]
df["db_lab"] = df[find_col(["入料檢測", "Δb"])]

df["dL_line"] = df[
    [
        find_col(["正-北", "ΔL"]),
        find_col(["正-南", "ΔL"])
    ]
].mean(axis=1)

df["da_line"] = df[
    [
        find_col(["正-北", "Δa"]),
        find_col(["正-南", "Δa"])
    ]
].mean(axis=1)

df["db_line"] = df[
    [
        find_col(["正-北", "Δb"]),
        find_col(["正-南", "Δb"])
    ]
].mean(axis=1)

# =====================================================
# TIME
# =====================================================
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
st.sidebar.header("🎨 Color Code")

color_codes = df["塗料編號"].dropna().unique()
color_sel = st.sidebar.selectbox("Color Code", color_codes)

df = df[df["塗料編號"] == color_sel]

# =====================================================
# CONTROL LIMITS
# =====================================================
def get_limit(color, col):
    row = limit_df[limit_df["Color_code"] == color]
    if row.empty or col not in row.columns:
        return None
    return row[col].values[0]


limits = {
    "dL": (get_limit(color_sel, "ΔL LCL"), get_limit(color_sel, "ΔL UCL")),
    "da": (get_limit(color_sel, "Δa LCL"), get_limit(color_sel, "Δa UCL")),
    "db": (get_limit(color_sel, "Δb LCL"), get_limit(color_sel, "Δb UCL")),
}

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
            ax.scatter(i, v, color="red")
        elif abs(v - mean) > 3 * std:
            ax.scatter(i, v, color="orange")
        else:
            ax.scatter(i, v, color="black")

    ax.plot(y, alpha=0.4)
    ax.axhline(mean, color="blue", linestyle="--", label="Mean")
    ax.axhline(mean + 3 * std, color="orange", linestyle=":")
    ax.axhline(mean - 3 * std, color="orange", linestyle=":")

    if lcl is not None and ucl is not None:
        ax.axhline(lcl, color="red", label="LCL")
        ax.axhline(ucl, color="red", label="UCL")

    ax.set_title(title)
    ax.legend()
    return fig


# =====================================================
# DASHBOARD
# =====================================================
st.title("🎨 SPC Color Control Dashboard")

# ---- COMBINED FIRST ----
st.subheader("📌 COMBINED SPC – LINE Priority")

st.pyplot(
    spc_chart(
        df,
        "dL_line",
        "COMBINED ΔL",
        limits["dL"][0],
        limits["dL"][1],
    )
)

st.markdown("---")

# ---- DETAIL ----
tabs = st.tabs(["LAB SPC", "LINE SPC"])

with tabs[0]:
    st.pyplot(spc_chart(df, "dL_lab", "LAB ΔL", *limits["dL"]))
    st.pyplot(spc_chart(df, "da_lab", "LAB Δa", *limits["da"]))
    st.pyplot(spc_chart(df, "db_lab", "LAB Δb", *limits["db"]))

with tabs[1]:
    st.pyplot(spc_chart(df, "dL_line", "LINE ΔL", *limits["dL"]))
    st.pyplot(spc_chart(df, "da_line", "LINE Δa", *limits["da"]))
    st.pyplot(spc_chart(df, "db_line", "LINE Δb", *limits["db"]))
