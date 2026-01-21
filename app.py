import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO

# ======================
# PAGE CONFIG
# ======================
st.set_page_config(
    page_title="SPC Color Dashboard",
    layout="wide",
    page_icon="📊"
)

# ======================
# STYLE
# ======================
st.markdown("""
<style>
.stApp { background-color: #f7f9fc; }
h1, h2, h3 { color: #0f172a; }
section[data-testid="stSidebar"] { background-color: #0f172a; }
section[data-testid="stSidebar"] * { color: white; }
.metric-box {
    background: white;
    padding: 16px;
    border-radius: 12px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.05);
}
</style>
""", unsafe_allow_html=True)

# ======================
# LOAD GOOGLE SHEET
# ======================
@st.cache_data
def load_sheet(url):
    csv_url = url.replace("/edit?gid=", "/export?format=csv&gid=")
    df = pd.read_csv(csv_url)
    # normalize column names
    df.columns = (
        df.columns
        .str.replace("\n", " ", regex=False)
        .str.replace("  ", " ", regex=False)
        .str.strip()
    )
    return df

DATA_URL = "https://docs.google.com/spreadsheets/d/1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534/edit?gid=0"
LIMIT_URL = "https://docs.google.com/spreadsheets/d/1jbP8puBraQ5Xgs9oIpJ7PlLpjIK3sltrgbrgKUcJ-Qo/edit?gid=0"

df = load_sheet(DATA_URL)
limit_df = load_sheet(LIMIT_URL)

st.success("✅ Data loaded successfully from Google Sheets")

# ======================
# BASIC CLEAN
# ======================
df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
df = df.dropna(subset=["Time"])

df["Year"] = df["Time"].dt.year
df["Month"] = df["Time"].dt.month

# ======================
# CALCULATED COLUMNS
# ======================
df["dL_line"] = df[["正-北 ΔL", "正-南 ΔL"]].mean(axis=1)
df["da_line"] = df[["正-北 Δa", "正-南 Δa"]].mean(axis=1)
df["db_line"] = df[["正-北 Δb", "正-南 Δb"]].mean(axis=1)

df["dL_lab"] = df["入料檢測 ΔL 正面"]
df["da_lab"] = df["入料檢測 Δa 正面"]
df["db_lab"] = df["入料檢測 Δb 正面"]

# ======================
# SIDEBAR FILTER
# ======================
st.sidebar.markdown("## ⏱ Time Filter")

latest_year = int(df["Year"].max())
year = st.sidebar.selectbox(
    "Year",
    sorted(df["Year"].unique()),
    index=sorted(df["Year"].unique()).index(latest_year)
)

month = st.sidebar.multiselect(
    "Month",
    sorted(df["Month"].unique())
)

df_f = df[df["Year"] == year]
if month:
    df_f = df_f[df_f["Month"].isin(month)]

# ======================
# COLOR CODE FILTER
# ======================
st.sidebar.markdown("## 🎨 Color Code")

color_codes = df_f["塗料編號"].dropna().unique()
color = st.sidebar.selectbox("Select Color Code", color_codes)
df_f = df_f[df_f["塗料編號"] == color]

# ======================
# CONTROL LIMIT LOOKUP
# ======================
def get_limit(color, name):
    row = limit_df[limit_df["Color_code"] == color]
    if row.empty:
        return None, None
    lcl = row[f"{name} LCL"].values[0]
    ucl = row[f"{name} UCL"].values[0]
    return lcl, ucl

lab_limits = {
    "dL": get_limit(color, "ΔL"),
    "da": get_limit(color, "Δa"),
    "db": get_limit(color, "Δb"),
}

line_limits = lab_limits  # same sheet, separated logically

# ======================
# SPC FUNCTION
# ======================
def spc_chart(data, y, title, lcl_int, ucl_int):
    mean = data[y].mean()
    std = data[y].std()
    ucl_3s = mean + 3 * std
    lcl_3s = mean - 3 * std

    fig, ax = plt.subplots(figsize=(12,4))

    for i, v in enumerate(data[y]):
        if lcl_int is not None and (v < lcl_int or v > ucl_int):
            ax.scatter(i, v, color="red")
        elif v < lcl_3s or v > ucl_3s:
            ax.scatter(i, v, color="orange")
        else:
            ax.scatter(i, v, color="black")

    ax.plot(data[y].values, linewidth=0.5)
    ax.axhline(mean, linestyle="--", color="blue", label="Mean")
    ax.axhline(ucl_3s, linestyle="--", color="orange", label="±3σ")
    ax.axhline(lcl_3s, linestyle="--", color="orange")

    if lcl_int is not None:
        ax.axhline(ucl_int, linestyle="--", color="purple", label="Internal Spec")
        ax.axhline(lcl_int, linestyle="--", color="purple")

    ax.set_title(title)
    ax.legend()
    return fig

# ======================
# DASHBOARD
# ======================
st.title("📊 SPC Color Control Dashboard")

st.markdown("### 📌 COMBINED SPC – LAB & LINE")

fig = spc_chart(df_f, "dL_line", "COMBINED ΔL", *lab_limits["dL"])
st.pyplot(fig)

tabs = st.tabs(["🧪 LAB SPC", "🏭 LINE SPC"])

with tabs[0]:
    st.pyplot(spc_chart(df_f, "dL_lab", "LAB ΔL", *lab_limits["dL"]))
    st.pyplot(spc_chart(df_f, "da_lab", "LAB Δa", *lab_limits["da"]))
    st.pyplot(spc_chart(df_f, "db_lab", "LAB Δb", *lab_limits["db"]))

with tabs[1]:
    st.pyplot(spc_chart(df_f, "dL_line", "LINE ΔL", *line_limits["dL"]))
    st.pyplot(spc_chart(df_f, "da_line", "LINE Δa", *line_limits["da"]))
    st.pyplot(spc_chart(df_f, "db_line", "LINE Δb", *line_limits["db"]))
