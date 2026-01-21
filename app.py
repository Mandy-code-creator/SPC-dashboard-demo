import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

# ===============================
# PAGE CONFIG
# ===============================
st.set_page_config(page_title="SPC Dashboard", layout="wide")
st.title("SPC Dashboard – ΔL / Δa / Δb (LAB vs LINE)")

# ===============================
# GOOGLE SHEET CSV
# ===============================
SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534"
    "/gviz/tq?tqx=out:csv"
)

# ===============================
# LOAD DATA
# ===============================
df = pd.read_csv(SHEET_URL)

# ===============================
# NORMALIZE COLUMN NAMES
# ===============================
df.columns = (
    df.columns
    .str.replace('\n', ' ', regex=False)
    .str.replace('  ', ' ', regex=False)
    .str.strip()
)

# ===============================
# RENAME COLUMNS
# ===============================
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

# ===============================
# TIME CONVERSION
# ===============================
df["time"] = pd.to_datetime(df["time"], errors="coerce")

st.success("Google Sheets data loaded successfully.")

# ===============================
# SIDEBAR FILTERS
# ===============================
st.sidebar.header("Filters")

# ---- Color filter
color_list = sorted(df["color_code"].dropna().unique())
selected_color = st.sidebar.selectbox("Select Color Code", color_list)
df = df[df["color_code"] == selected_color]

# ---- Select individual time
st.sidebar.subheader("Select Production Time")
time_options = df["time"].dropna().sort_values().unique()

selected_times = st.sidebar.multiselect(
    "Time",
    options=time_options,
    default=time_options
)

df = df[df["time"].isin(selected_times)]

# ===============================
# CONTROL LIMIT INPUT
# ===============================
def limit_input(label):
    return st.sidebar.number_input(label, value=None, step=0.1, format="%.2f")

st.sidebar.header("LAB Control Limits (Input)")

ucl_L_lab = limit_input("LAB UCL ΔL")
lcl_L_lab = limit_input("LAB LCL ΔL")

ucl_a_lab = limit_input("LAB UCL Δa")
lcl_a_lab = limit_input("LAB LCL Δa")

ucl_b_lab = limit_input("LAB UCL Δb")
lcl_b_lab = limit_input("LAB LCL Δb")

st.sidebar.header("LINE Control Limits (Output)")

ucl_L_line = limit_input("LINE UCL ΔL")
lcl_L_line = limit_input("LINE LCL ΔL")

ucl_a_line = limit_input("LINE UCL Δa")
lcl_a_line = limit_input("LINE LCL Δa")

ucl_b_line = limit_input("LINE UCL Δb")
lcl_b_line = limit_input("LINE LCL Δb")

# ===============================
# AGGREGATION
# ===============================
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

# ===============================
# SPC FUNCTIONS
# ===============================
def spc_chart(df, y_col, title, ylabel, ucl=None, lcl=None):
    if df.empty:
        st.warning("No data available.")
        return

    y = df[y_col].dropna()
    mean = y.mean()
    std = y.std()

    if ucl is None or lcl is None:
        ucl = mean + 3 * std
        lcl = mean - 3 * std

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df["batch"], df[y_col], marker="o")
    ax.axhline(mean, linestyle="--", label="CL")
    ax.axhline(ucl, linestyle="--", label="UCL")
    ax.axhline(lcl, linestyle="--", label="LCL")

    ax.set_title(title)
    ax.set_xlabel("Batch")
    ax.set_ylabel(ylabel)
    ax.legend()

    st.pyplot(fig)

    buffer = BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight")
    buffer.seek(0)

    st.download_button(
        "📥 Download chart",
        data=buffer,
        file_name=f"{title}.png",
        mime="image/png"
    )

    plt.close(fig)


def spc_combined_chart(line_df, lab_df, col_line, col_lab, title, ylabel, ucl=None, lcl=None):
    if line_df.empty or lab_df.empty:
        st.warning("No data available.")
        return

    y = pd.concat([line_df[col_line], lab_df[col_lab]]).dropna()
    mean = y.mean()
    std = y.std()

    if ucl is None or lcl is None:
        ucl = mean + 3 * std
        lcl = mean - 3 * std

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(line_df["batch"], line_df[col_line], marker="o", label="LINE")
    ax.plot(lab_df["batch"], lab_df[col_lab], marker="s", label="LAB")

    ax.axhline(mean, linestyle="--", label="CL")
    ax.axhline(ucl, linestyle="--", label="UCL")
    ax.axhline(lcl, linestyle="--", label="LCL")

    ax.set_title(title)
    ax.set_xlabel("Batch")
    ax.set_ylabel(ylabel)
    ax.legend()

    st.pyplot(fig)

    buffer = BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight")
    buffer.seek(0)

    st.download_button(
        "📥 Download chart",
        data=buffer,
        file_name=f"{title}.png",
        mime="image/png"
    )

    plt.close(fig)

# ===============================
# DISPLAY SPC CHARTS
# ===============================
st.header(f"SPC Charts – Color: {selected_color}")

# ---- Combined SPC (use LINE limits)
st.subheader("Combined SPC – LAB vs LINE")

spc_combined_chart(
    line_batch, lab_batch,
    "dL_avg", "dL_input",
    "SPC ΔL – LAB vs LINE",
    "ΔL",
    ucl_L_line, lcl_L_line
)

spc_combined_chart(
    line_batch, lab_batch,
    "da_avg", "da_input",
    "SPC Δa – LAB vs LINE",
    "Δa",
    ucl_a_line, lcl_a_line
)

spc_combined_chart(
    line_batch, lab_batch,
    "db_avg", "db_input",
    "SPC Δb – LAB vs LINE",
    "Δb",
    ucl_b_line, lcl_b_line
)

# ---- Detail SPC
st.subheader("Detail SPC Charts")

tabs = st.tabs(["ΔL", "Δa", "Δb"])

with tabs[0]:
    spc_chart(line_batch, "dL_avg", "SPC ΔL – LINE", "ΔL", ucl_L_line, lcl_L_line)
    spc_chart(lab_batch, "dL_input", "SPC ΔL – LAB", "ΔL", ucl_L_lab, lcl_L_lab)

with tabs[1]:
    spc_chart(line_batch, "da_avg", "SPC Δa – LINE", "Δa", ucl_a_line, lcl_a_line)
    spc_chart(lab_batch, "da_input", "SPC Δa – LAB", "Δa", ucl_a_lab, lcl_a_lab)

with tabs[2]:
    spc_chart(line_batch, "db_avg", "SPC Δb – LINE", "Δb", ucl_b_line, lcl_b_line)
    spc_chart(lab_batch, "db_input", "SPC Δb – LAB", "Δb", ucl_b_lab, lcl_b_lab)
