import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="SPC Color Dashboard", layout="wide")

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

st.success("Data loaded successfully")

# =========================
# CLEAN & PREPARE
# =========================
df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
df["Year"] = df["Time"].dt.year
df["Month"] = df["Time"].dt.month

# LAB
df["dL_lab"] = df["入料檢測\n ΔL 正面"]
df["da_lab"] = df["入料檢測\nΔa 正面"]
df["db_lab"] = df["入料檢測\nΔb 正面"]

# LINE
df["dL_line"] = df["Average value\nΔL 正面"]
df["da_line"] = df["Average value\n Δa 正面"]
df["db_line"] = df["Average value\nΔb 正面"]

# =========================
# SIDEBAR – FILTER
# =========================
st.sidebar.header("Filters")

color_code = st.sidebar.selectbox(
    "Color Code",
    sorted(df["塗料編號"].dropna().unique())
)

year_selected = st.sidebar.selectbox(
    "Year",
    sorted(df["Year"].dropna().unique())
)

month_selected = st.sidebar.multiselect(
    "Month",
    sorted(df["Month"].dropna().unique()),
    default=sorted(df["Month"].dropna().unique())
)

df = df[
    (df["塗料編號"] == color_code) &
    (df["Year"] == year_selected) &
    (df["Month"].isin(month_selected))
]

# =========================
# LOAD LIMIT BY COLOR CODE
# =========================
limit_row = limit_df[limit_df["Color_code"] == color_code]

def get_limit(name):
    if limit_row.empty:
        return None, None
    return float(limit_row[f"{name}_LCL"]), float(limit_row[f"{name}_UCL"])

# LAB & LINE limit (theo thiết kế hiện tại dùng chung)
lab_limits = {
    "dL": get_limit("ΔL"),
    "da": get_limit("Δa"),
    "db": get_limit("Δb"),
}
line_limits = lab_limits

# =========================
# SIDEBAR – CONTROL LIMITS
# =========================
st.sidebar.header("LAB Control Limits")
lab_LCL_L = st.sidebar.number_input("LAB ΔL LCL", value=lab_limits["dL"][0])
lab_UCL_L = st.sidebar.number_input("LAB ΔL UCL", value=lab_limits["dL"][1])
lab_LCL_a = st.sidebar.number_input("LAB Δa LCL", value=lab_limits["da"][0])
lab_UCL_a = st.sidebar.number_input("LAB Δa UCL", value=lab_limits["da"][1])
lab_LCL_b = st.sidebar.number_input("LAB Δb LCL", value=lab_limits["db"][0])
lab_UCL_b = st.sidebar.number_input("LAB Δb UCL", value=lab_limits["db"][1])

st.sidebar.header("LINE Control Limits")
line_LCL_L, line_UCL_L = lab_LCL_L, lab_UCL_L
line_LCL_a, line_UCL_a = lab_LCL_a, lab_UCL_a
line_LCL_b, line_UCL_b = lab_LCL_b, lab_UCL_b

# =========================
# SPC FUNCTION
# =========================
def fig_to_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
    buf.seek(0)
    return buf

def spc_chart(df, y_col, title, lcl_internal, ucl_internal):
    y = df[y_col].dropna()
    mean = y.mean()
    std = y.std()

    ucl_3s = mean + 3 * std
    lcl_3s = mean - 3 * std

    colors = []
    for v in y:
        if v > ucl_internal or v < lcl_internal:
            colors.append("red")
        elif v > ucl_3s or v < lcl_3s:
            colors.append("orange")
        else:
            colors.append("blue")

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.scatter(y.index, y, c=colors)
    ax.plot(y.index, y, alpha=0.3)

    ax.axhline(mean, linestyle="--", label="Mean")
    ax.axhline(ucl_3s, linestyle="--", color="orange", label="UCL ±3σ")
    ax.axhline(lcl_3s, linestyle="--", color="orange", label="LCL ±3σ")
    ax.axhline(ucl_internal, linestyle="-.", color="red", label="Internal UCL")
    ax.axhline(lcl_internal, linestyle="-.", color="red", label="Internal LCL")

    ax.set_title(title)
    ax.legend()
    ax.grid(True)

    st.pyplot(fig)
    return fig

# =========================
# DASHBOARD
# =========================
st.title("SPC Color Control Dashboard")

# ---- COMBINED SPC ----
st.subheader("COMBINED SPC (LAB vs LINE – LINE LIMIT PRIORITY)")
fig = spc_chart(df, "dL_line", "COMBINED ΔL", line_LCL_L, line_UCL_L)
st.download_button(
    "Download SPC ΔL (PNG)",
    data=fig_to_png(fig),
    file_name=f"SPC_COMBINED_DeltaL_{color_code}.png",
    mime="image/png"
)

# ---- LAB SPC ----
st.subheader("LAB SPC")
spc_chart(df, "dL_lab", "LAB ΔL", lab_LCL_L, lab_UCL_L)
spc_chart(df, "da_lab", "LAB Δa", lab_LCL_a, lab_UCL_a)
spc_chart(df, "db_lab", "LAB Δb", lab_LCL_b, lab_UCL_b)

# ---- LINE SPC ----
st.subheader("LINE SPC")
spc_chart(df, "dL_line", "LINE ΔL", line_LCL_L, line_UCL_L)
spc_chart(df, "da_line", "LINE Δa", line_LCL_a, line_UCL_a)
spc_chart(df, "db_line", "LINE Δb", line_LCL_b, line_UCL_b)

# =========================
# NG SUMMARY BY MONTH
# =========================
def classify_ng(v, lcl, ucl):
    return "NG" if (v < lcl or v > ucl) else "OK"

df["NG_ΔL"] = df["dL_line"].apply(lambda x: classify_ng(x, line_LCL_L, line_UCL_L))
df["NG_Δa"] = df["da_line"].apply(lambda x: classify_ng(x, line_LCL_a, line_UCL_a))
df["NG_Δb"] = df["db_line"].apply(lambda x: classify_ng(x, line_LCL_b, line_UCL_b))

summary = (
    df.groupby(["Year", "Month"])
      .agg(
          Total=("dL_line", "count"),
          NG_ΔL=("NG_ΔL", lambda x: (x == "NG").sum()),
          NG_Δa=("NG_Δa", lambda x: (x == "NG").sum()),
          NG_Δb=("NG_Δb", lambda x: (x == "NG").sum()),
      )
      .reset_index()
)

st.subheader("NG Summary by Month")
st.dataframe(summary, use_container_width=True)
