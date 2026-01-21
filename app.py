import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(page_title="SPC Dashboard", layout="wide")
st.title("SPC Dashboard – LAB vs LINE (ΔL, Δa, Δb)")

# =====================================================
# GOOGLE SHEET URLS
# =====================================================
DATA_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534"
    "/gviz/tq?tqx=out:csv"
)

LIMIT_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1jbP8puBraQ5Xgs9oIpJ7PlLpjIK3sltrgbrgKUcJ-Qo"
    "/gviz/tq?tqx=out:csv"
)

# =====================================================
# LOAD DATA
# =====================================================
df = pd.read_csv(DATA_SHEET_URL)
limit_df = pd.read_csv(LIMIT_SHEET_URL)

st.success("Google Sheets data loaded successfully.")

# =====================================================
# NORMALIZE COLUMN NAMES
# =====================================================
df.columns = (
    df.columns
    .str.replace("\n", " ", regex=False)
    .str.replace("  ", " ", regex=False)
    .str.strip()
)

limit_df.columns = (
    limit_df.columns
    .str.replace("\n", " ", regex=False)
    .str.strip()
)

# =====================================================
# RENAME MAIN DATA COLUMNS
# =====================================================
COLUMN_MAP = {
    "製造批號": "batch",
    "塗料編號": "color_code",
    "Time": "time",

    "Average value ΔL 正面": "dL_avg",
    "Average value Δa 正面": "da_avg",
    "Average value Δb 正面": "db_avg",

    "入料檢測 ΔL 正面": "dL_input",
    "入料檢測 Δa 正面": "da_input",
    "入料檢測 Δb 正面": "db_input",
}

df = df.rename(columns=COLUMN_MAP)

df["time"] = pd.to_datetime(df["time"], errors="coerce")

# =====================================================
# SIDEBAR FILTERS
# =====================================================
st.sidebar.header("Filters")

color_list = sorted(df["color_code"].dropna().unique())
selected_color = st.sidebar.selectbox("Select Color Code", color_list)

df = df[df["color_code"] == selected_color]

time_options = df["time"].dropna().sort_values().unique()
selected_times = st.sidebar.multiselect(
    "Select Production Time",
    options=time_options,
    default=time_options
)

df = df[df["time"].isin(selected_times)]

# =====================================================
# AGGREGATE DATA
# =====================================================
line_batch = (
    df.groupby("batch")[["dL_avg", "da_avg", "db_avg"]]
    .mean()
    .reset_index()
)

lab_batch = (
    df.groupby("batch")[["dL_input", "da_input", "db_input"]]
    .first()
    .reset_index()
)

# =====================================================
# GET CONTROL LIMIT BY COLOR
# =====================================================
def get_limits_by_color(df, color_code):
    row = df[df["Color_code"] == color_code]

    if row.empty:
        return {
            "dL": (None, None),
            "da": (None, None),
            "db": (None, None),
        }

    r = row.iloc[0]

    return {
        "dL": (r["ΔL LCL"], r["ΔL UCL"]),
        "da": (r["Δa LCL"], r["Δa UCL"]),
        "db": (r["Δb LCL"], r["Δb UCL"]),
    }

limits = get_limits_by_color(limit_df, selected_color)

# =====================================================
# SIDEBAR – CONTROL LIMIT (AUTO + OVERRIDE)
# =====================================================
def parse_limit(v):
    try:
        return float(v)
    except:
        return None

st.sidebar.header("LINE Control Limits (Internal)")

lcl_L_line = parse_limit(st.sidebar.text_input("ΔL LCL", value=str(limits["dL"][0])))
ucl_L_line = parse_limit(st.sidebar.text_input("ΔL UCL", value=str(limits["dL"][1])))

lcl_a_line = parse_limit(st.sidebar.text_input("Δa LCL", value=str(limits["da"][0])))
ucl_a_line = parse_limit(st.sidebar.text_input("Δa UCL", value=str(limits["da"][1])))

lcl_b_line = parse_limit(st.sidebar.text_input("Δb LCL", value=str(limits["db"][0])))
ucl_b_line = parse_limit(st.sidebar.text_input("Δb UCL", value=str(limits["db"][1])))

# =====================================================
# SPC PLOT FUNCTIONS
# =====================================================
def spc_chart(df, y_col, title, ylabel, lcl_manual=None, ucl_manual=None):
    y = df[y_col].dropna()
    if y.empty:
        st.warning("No data available.")
        return

    mean = y.mean()
    std = y.std()

    ucl_auto = mean + 3 * std
    lcl_auto = mean - 3 * std

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df["batch"], df[y_col], marker="o", label="Process")

    ax.axhline(mean, linestyle="--", label="CL")
    ax.axhline(ucl_auto, linestyle="--", color="red", label="UCL ±3σ")
    ax.axhline(lcl_auto, linestyle="--", color="red", label="LCL ±3σ")

    if ucl_manual is not None:
        ax.axhline(ucl_manual, linestyle="-.", color="orange", label="Internal UCL")
    if lcl_manual is not None:
        ax.axhline(lcl_manual, linestyle="-.", color="orange", label="Internal LCL")

    ax.set_title(title)
    ax.set_xlabel("Batch")
    ax.set_ylabel(ylabel)
    ax.legend()

    st.pyplot(fig)

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)

    st.download_button(
        "📥 Download chart",
        data=buf,
        file_name=f"{title}.png",
        mime="image/png"
    )

    plt.close(fig)

# =====================================================
# DISPLAY
# =====================================================
st.header(f"SPC Charts – Color Code: {selected_color}")

tabs = st.tabs(["ΔL", "Δa", "Δb"])

with tabs[0]:
    spc_chart(line_batch, "dL_avg", "SPC ΔL – LINE", "ΔL", lcl_L_line, ucl_L_line)

with tabs[1]:
    spc_chart(line_batch, "da_avg", "SPC Δa – LINE", "Δa", lcl_a_line, ucl_a_line)

with tabs[2]:
    spc_chart(line_batch, "db_avg", "SPC Δb – LINE", "Δb", lcl_b_line, ucl_b_line)
