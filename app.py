import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# ===============================
# CONFIG
# ===============================
st.set_page_config(
    page_title="SPC Color Dashboard",
    layout="wide",
    page_icon="📊"
)

# ===============================
# GOOGLE SHEET URL
# ===============================
DATA_SHEET_URL = "https://docs.google.com/spreadsheets/d/XXXXXXXX/export?format=csv"
LIMIT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1jbP8puBraQ5Xgs9oIpJ7PlLpjIK3sltrgbrgKUcJ-Qo/export?format=csv"

# ===============================
# SAFE LOAD
# ===============================
@st.cache_data
def load_data():
    return pd.read_csv(DATA_SHEET_URL)

@st.cache_data
def load_limits():
    return pd.read_csv(LIMIT_SHEET_URL)

df = load_data()
limit_df = load_limits()

# ===============================
# STANDARDIZE COLUMN NAMES
# ===============================
df.columns = df.columns.str.strip()
limit_df.columns = limit_df.columns.str.strip()

# REQUIRED COLUMNS (EDIT IF NEEDED)
TIME_COL = "Time"
COLOR_COL = "Color_code"
BATCH_COL = "Batch"

LAB_COLS = {
    "dL": "dL_lab",
    "da": "da_lab",
    "db": "db_lab"
}

LINE_COLS = {
    "dL": "dL_line",
    "da": "da_line",
    "db": "db_line"
}

df[TIME_COL] = pd.to_datetime(df[TIME_COL])

# ===============================
# SIDEBAR – TIME FILTER
# ===============================
st.sidebar.title("⏱ Time Filter")

df["Year"] = df[TIME_COL].dt.year
df["Month"] = df[TIME_COL].dt.month

years = sorted(df["Year"].unique())
latest_year = max(years)

year = st.sidebar.selectbox("Year", ["All"] + years, index=years.index(latest_year) + 1)
month = st.sidebar.selectbox("Month", ["All"] + list(range(1, 13)))

if year != "All":
    df = df[df["Year"] == year]

if month != "All":
    df = df[df["Month"] == month]

# ===============================
# COLOR FILTER (FIX UI CONFUSION)
# ===============================
st.sidebar.markdown("### 🎨 Color Code")

colors = sorted(df[COLOR_COL].unique())
color = st.sidebar.selectbox(
    "Selected Color Code",
    options=colors,
    format_func=lambda x: f"✔ {x}"
)

df = df[df[COLOR_COL] == color]

st.sidebar.success(f"Selected: {color}")

# ===============================
# GET CONTROL LIMIT
# ===============================
def get_limit(color, factor, source="LAB"):
    row = limit_df[limit_df["Color_code"] == color]
    if row.empty:
        return None, None

    prefix = f"{factor} {source}"
    try:
        lcl = row[f"{prefix} LCL"].values[0]
        ucl = row[f"{prefix} UCL"].values[0]
        return lcl, ucl
    except:
        return None, None

# ===============================
# SPC CHART FUNCTION
# ===============================
def spc_chart(df, y_lab, y_line, title, lcl_i, ucl_i):
    fig, ax = plt.subplots(figsize=(12, 4))

    x = range(len(df))
    lab = df[y_lab]
    line = df[y_line]

    mean = line.mean()
    std = line.std()
    ucl_3s = mean + 3 * std
    lcl_3s = mean - 3 * std

    ax.plot(x, line, label="LINE", color="blue")
    ax.plot(x, lab, label="LAB", linestyle="--", marker="o", color="green")

    if lcl_i is not None:
        ax.axhline(lcl_i, color="purple", linestyle="-.", label="Internal LCL")
        ax.axhline(ucl_i, color="purple", linestyle="-.", label="Internal UCL")

    ax.axhline(ucl_3s, color="orange", linestyle="--", label="+3σ")
    ax.axhline(lcl_3s, color="orange", linestyle="--", label="-3σ")

    for i, v in enumerate(line):
        if lcl_i is not None and (v < lcl_i or v > ucl_i):
            ax.scatter(i, v, color="red", zorder=5)
        elif v < lcl_3s or v > ucl_3s:
            ax.scatter(i, v, color="orange", zorder=5)

    ax.set_title(title)
    ax.legend()
    ax.grid(True)

    return fig

# ===============================
# DASHBOARD
# ===============================
st.title("📊 SPC Color Control Dashboard")
st.markdown(f"### 🎨 Color Code: **{color}**")

for factor in ["dL", "da", "db"]:
    st.subheader(f"SPC {factor.upper()}")

    lcl_lab, ucl_lab = get_limit(color, f"Δ{factor[-1].upper()}", "LAB")

    fig = spc_chart(
        df,
        LAB_COLS[factor],
        LINE_COLS[factor],
        f"{factor.upper()} SPC (LINE + LAB)",
        lcl_lab,
        ucl_lab
    )

    st.pyplot(fig)

    st.download_button(
        label="📥 Export PNG",
        data=fig_to_png := plt.gcf(),
        file_name=f"{color}_{factor}_SPC.png",
        mime="image/png"
    )

st.success("✅ SPC Dashboard Loaded Successfully")
