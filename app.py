import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# ===============================
# PAGE CONFIG
# ===============================
st.set_page_config(page_title="SPC Dashboard", layout="wide")
st.title("SPC Dashboard – ΔL / Δa / Δb (LAB vs LINE)")

# ===============================
# GOOGLE SHEET CSV
# ===============================
url = (
    "https://docs.google.com/spreadsheets/d/"
    "1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534"
    "/gviz/tq?tqx=out:csv"
)

# ===============================
# LOAD DATA
# ===============================
df = pd.read_csv(url)

# ===============================
# NORMALIZE & RENAME COLUMNS
# ===============================
df.columns = (
    df.columns
    .str.replace('\n', ' ', regex=False)
    .str.replace('  ', ' ', regex=False)
    .str.strip()
)

COLUMN_MAP = {
    "製造批號": "batch",

    "Average value ΔL 正面": "dL_avg",
    "Average value Δa 正面": "da_avg",
    "Average value Δb 正面": "db_avg",

    "入料檢測 ΔL 正面": "dL_input",
    "入料檢測 Δa 正面": "da_input",
    "入料檢測 Δb 正面": "db_input",
}

df = df.rename(columns=COLUMN_MAP)

st.success("Data loaded successfully.")

# ===============================
# LINE AVERAGE PER BATCH
# ===============================
line_batch = (
    df.groupby("batch")[["dL_avg", "da_avg", "db_avg"]]
    .mean()
    .reset_index()
)

# ===============================
# LAB INPUT PER BATCH
# ===============================
lab_batch = (
    df.groupby("batch")[["dL_input", "da_input", "db_input"]]
    .first()
    .reset_index()
)

# ===============================
# SPC FUNCTION
# ===============================
def spc_chart(df, y_col, title, ylabel):
    y = df[y_col].dropna()

    mean = y.mean()
    std = y.std()

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

# ===============================
# SPC CHARTS
# ===============================
st.header("SPC Charts")

tabs = st.tabs(["ΔL", "Δa", "Δb"])

with tabs[0]:
    spc_chart(line_batch, "dL_avg", "SPC ΔL – LINE", "ΔL")
    spc_chart(lab_batch, "dL_input", "SPC ΔL – LAB", "ΔL")

with tabs[1]:
    spc_chart(line_batch, "da_avg", "SPC Δa – LINE", "Δa")
    spc_chart(lab_batch, "da_input", "SPC Δa – LAB", "Δa")

with tabs[2]:
    spc_chart(line_batch, "db_avg", "SPC Δb – LINE", "Δb")
    spc_chart(lab_batch, "db_input", "SPC Δb – LAB", "Δb")
