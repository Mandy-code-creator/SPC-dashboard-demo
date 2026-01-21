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
# MAP DATA (SAFE – KHÔNG KEYERROR)
# =====================================================
df["dL_lab"] = df[find_col(["入料檢測", "ΔL"])]
df["da_lab"] = df[find_col(["入料檢測", "Δa"])]
df["db_lab"] = df[find_col(["入料檢測", "Δb"])]

df["dL_line"] = df[
    [find_col(["正-北", "ΔL"]), find_col(["正-南", "ΔL"])]
].mean(axis=1)

df["da_line"] = df[
    [find_col(["正-北", "Δa"]), find_col(["正-南", "Δa"])]
].mean(axis=1)

df["db_line"] = df[
    [find_col(["正-北", "Δb"]), find_col(["正-南", "Δb"])]
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
# CONTROL LIMITS (LAB & LINE TÁCH RIÊNG)
# =====================================================
def get_limit(color, col):
    row = limit_df[limit_df["Color_code"] == color]
    if row.empty or col not in row.columns:
        return None
    return row[col].values[0]


lab_limits = {
    "dL": (get_limit(color_sel, "ΔL LCL"), get_limit(color_sel, "ΔL UCL")),
    "da": (get_limit(color_sel, "Δa LCL"), get_limit(color_sel, "Δa UCL")),
    "db": (get_limit(color_sel, "Δb LCL"), get_limit(color_sel, "Δb UCL")),
}

# hiện tại LINE dùng chung sheet 2
line_limits = lab_limits

# =====================================================
# SPC CHART FUNCTION (2 BỘ LIMIT)
# =====================================================
def spc_chart(
    data,
    col,
    title,
    lab_lcl=None,
    lab_ucl=None,
    line_lcl=None,
    line_ucl=None,
):
    fig, ax = plt.subplots(figsize=(11, 4))

    y = data[col].dropna().values
    mean = np.mean(y)
    std = np.std(y)

    for i, v in enumerate(y):
        if lab_lcl is not None and lab_ucl is not None and (v < lab_lcl or v > lab_ucl):
            ax.scatter(i, v, color="red", zorder=3)
        elif abs(v - mean) > 3 * std:
            ax.scatter(i, v, color="orange", zorder=3)
        else:
            ax.scatter(i, v, color="black", zorder=3)

    ax.plot(y, alpha=0.4)

    # ±3σ
    ax.axhline(mean, color="blue", linestyle="--", label="Mean")
    ax.axhline(mean + 3 * std, color="orange", linestyle=":", label="+3σ")
    ax.axhline(mean - 3 * std, color="orange", linestyle=":", label="-3σ")

    # LAB limits
    if lab_lcl is not None and lab_ucl is not None:
        ax.axhline(lab_lcl, color="red", linestyle="-", label="LAB LCL")
        ax.axhline(lab_ucl, color="red", linestyle="-", label="LAB UCL")

    # LINE limits
    if line_lcl is not None and line_ucl is not None:
        ax.axhline(line_lcl, color="purple", linestyle="--", label="LINE LCL")
        ax.axhline(line_ucl, color="purple", linestyle="--", label="LINE UCL")

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
st.subheader("📌 COMBINED SPC – LAB & LINE")

st.pyplot(
    spc_chart(
        df,
        "dL_line",
        "COMBINED ΔL",
        lab_limits["dL"][0],
        lab_limits["dL"][1],
        line_limits["dL"][0],
        line_limits["dL"][1],
    )
)

st.markdown("---")

# -----------------------------------------------------
# DETAIL TABS
# -----------------------------------------------------
tabs = st.tabs(["LAB SPC", "LINE SPC"])

with tabs[0]:
    st.pyplot(
        spc_chart(
            df,
            "dL_lab",
            "LAB ΔL",
            lab_limits["dL"][0],
            lab_limits["dL"][1],
        )
    )
    st.pyplot(
        spc_chart(
            df,
            "da_lab",
            "LAB Δa",
            lab_limits["da"][0],
            lab_limits["da"][1],
        )
    )
    st.pyplot(
        spc_chart(
            df,
            "db_lab",
            "LAB Δb",
            lab_limits["db"][0],
            lab_limits["db"][1],
        )
    )

with tabs[1]:
    st.pyplot(
        spc_chart(
            df,
            "dL_line",
            "LINE ΔL",
            None,
            None,
            line_limits["dL"][0],
            line_limits["dL"][1],
        )
    )
    st.pyplot(
        spc_chart(
            df,
            "da_line",
            "LINE Δa",
            None,
            None,
            line_limits["da"][0],
            line_limits["da"][1],
        )
    )
    st.pyplot(
        spc_chart(
            df,
            "db_line",
            "LINE Δb",
            None,
            None,
            line_limits["db"][0],
            line_limits["db"][1],
        )
    )
