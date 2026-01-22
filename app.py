import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
import numpy as np
import math

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="SPC Color Dashboard (Between Batch)",
    page_icon="🎨",
    layout="wide"
)

# =========================
# GOOGLE SHEET LINKS
# =========================
DATA_URL = "https://docs.google.com/spreadsheets/d/1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534/export?format=csv"
LIMIT_URL = "https://docs.google.com/spreadsheets/d/1jbP8puBraQ5Xgs9oIpJ7PlLpjIK3sltrgbrgKUcJ-Qo/export?format=csv"

# =========================
# LOAD DATA
# =========================
@st.cache_data(ttl=300)
def load_data():
    df = pd.read_csv(DATA_URL)
    df["Time"] = pd.to_datetime(df["Time"])
    return df

@st.cache_data(ttl=300)
def load_limit():
    return pd.read_csv(LIMIT_URL)

df = load_data()
limit_df = load_limit()

# =========================
# FIX COLUMN NAMES
# =========================
df.columns = (
    df.columns
    .str.replace("\r\n", " ", regex=False)
    .str.replace("\n", " ", regex=False)
    .str.replace("　", " ", regex=False)
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)

# Fix typo rL -> ΔL
df.rename(columns={
    "入料檢測 rL 正面": "入料檢測 ΔL 正面"
}, inplace=True)

# =========================
# SIDEBAR FILTER
# =========================
st.sidebar.title("🎨 Filter")

color = st.sidebar.selectbox(
    "Color code",
    sorted(df["塗料編號"].dropna().unique())
)

df = df[df["塗料編號"] == color]

year = st.sidebar.selectbox(
    "Year",
    sorted(df["Time"].dt.year.unique())
)

df = df[df["Time"].dt.year == year]

# =========================
# LIMIT FUNCTION
# =========================
def get_limit(color, factor, stage):
    row = limit_df[limit_df["Color_code"] == color]
    if row.empty:
        return None, None
    return (
        row.get(f"{factor} {stage} LCL", [None]).values[0],
        row.get(f"{factor} {stage} UCL", [None]).values[0]
    )

# =========================
# BATCH MEAN FUNCTIONS
# =========================
def prep_lab_batch_mean(df, col):
    tmp = df[pd.notnull(df[col])]
    return tmp.groupby("製造批號", as_index=False).agg(
        Time=("Time", "min"),
        BatchMean=(col, "mean")
    )

def prep_line_batch_mean(df, north, south):
    tmp = df.dropna(subset=[north, south])
    tmp["coil_mean"] = tmp[[north, south]].mean(axis=1)
    return tmp.groupby("製造批號", as_index=False).agg(
        Time=("Time", "min"),
        BatchMean=("coil_mean", "mean")
    )

# =========================
# SPC DATA (BATCH LEVEL)
# =========================
spc = {
    "ΔL": {
        "lab": prep_lab_batch_mean(df, "入料檢測 ΔL 正面"),
        "line": prep_line_batch_mean(df, "正-北 ΔL", "正-南 ΔL")
    },
    "Δa": {
        "lab": prep_lab_batch_mean(df, "入料檢測 Δa 正面"),
        "line": prep_line_batch_mean(df, "正-北 Δa", "正-南 Δa")
    },
    "Δb": {
        "lab": prep_lab_batch_mean(df, "入料檢測 Δb 正面"),
        "line": prep_line_batch_mean(df, "正-北 Δb", "正-南 Δb")
    }
}

# =========================
# SPC SUMMARY (BETWEEN BATCH)
# =========================
def spc_summary(batch_df):
    v = batch_df["BatchMean"].dropna()
    return {
        "Min": round(v.min(), 3),
        "Max": round(v.max(), 3),
        "Mean": round(v.mean(), 3),
        "Std Dev": round(v.std(ddof=1), 3),
        "n (batch)": v.count()
    }

summary_line = []
summary_lab = []

for k in spc:
    line = spc_summary(spc[k]["line"])
    line["Factor"] = k
    summary_line.append(line)

    lab = spc_summary(spc[k]["lab"])
    lab["Factor"] = k
    summary_lab.append(lab)

summary_line_df = pd.DataFrame(summary_line)
summary_lab_df = pd.DataFrame(summary_lab)

# =========================
# DISPLAY SUMMARY
# =========================
st.title(f"🎨 SPC Color Dashboard — {color} ({year})")

c1, c2 = st.columns(2)
with c1:
    st.markdown("### 🏭 LINE (Between Batch)")
    st.dataframe(summary_line_df, use_container_width=True, hide_index=True)

with c2:
    st.markdown("### 🧪 LAB (Between Batch)")
    st.dataframe(summary_lab_df, use_container_width=True, hide_index=True)

# =========================
# SPC CHART FUNCTION
# =========================
def spc_chart(batch_df, title, limit):
    fig, ax = plt.subplots(figsize=(12, 4))

    y = batch_df["BatchMean"]
    mean = y.mean()
    std = y.std(ddof=1)

    ax.plot(batch_df["製造批號"], y, marker="o", linestyle="-")

    if std > 0:
        ax.axhline(mean + 3 * std, linestyle="--", color="orange", label="+3σ")
        ax.axhline(mean - 3 * std, linestyle="--", color="orange", label="-3σ")

    if limit[0] is not None:
        ax.axhline(limit[0], color="red", label="LCL")
        ax.axhline(limit[1], color="red", label="UCL")

    ax.set_title(title)
    ax.legend()
    ax.grid(True)
    ax.tick_params(axis="x", rotation=45)

    return fig

# =========================
# PLOT SPC
# =========================
st.markdown("## 📊 SPC Chart (Between Batch)")

for k in spc:
    fig = spc_chart(
        spc[k]["line"],
        f"LINE {k} — Batch Mean",
        get_limit(color, k, "LINE")
    )
    st.pyplot(fig)

    fig = spc_chart(
        spc[k]["lab"],
        f"LAB {k} — Batch Mean",
        get_limit(color, k, "LAB")
    )
    st.pyplot(fig)
