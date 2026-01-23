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
    page_title="SPC Color Dashboard",
    page_icon="🎨",
    layout="wide"
)

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

# =========================
# GOOGLE SHEET LINKS
# =========================
DATA_URL = "https://docs.google.com/spreadsheets/d/1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534/export?format=csv"
LIMIT_URL = "https://docs.google.com/spreadsheets/d/1jbP8puBraQ5Xgs9oIpJ7PlLpjIK3sltrgbrgKUcJ-Qo/export?format=csv"

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

# =========================
# SIDEBAR FILTER
# =========================
color = st.sidebar.selectbox("Color code", sorted(df["塗料編號"].dropna().unique()))
df = df[df["塗料編號"] == color]

# =========================
# LIMIT FUNCTION
# =========================
def get_limit(color, prefix, factor):
    row = limit_df[limit_df["Color_code"] == color]
    if row.empty:
        return None, None
    return (
        row.get(f"{factor} {prefix} LCL", [None]).values[0],
        row.get(f"{factor} {prefix} UCL", [None]).values[0]
    )

# =====================================================
# 🔴 CHỈ PHẦN DƯỚI ĐÂY ĐƯỢC SỬA – LOGIC ĐÚNG
# =====================================================

# 1 cuộn = 1 dòng
# 1 cuộn = mean(Bắc, Nam)
# 1 batch = mean(các cuộn)

def prep_spc(df, north, south):
    tmp = df[[ "製造批號", north, south ]].dropna()
    tmp["value"] = tmp[[north, south]].mean(axis=1)

    # batch = trung bình các cuộn
    return tmp.groupby("製造批號", as_index=False).agg(
        value=("value", "mean")
    )


def prep_lab(df, col):
    tmp = df[[ "製造批號", col ]].dropna()

    return tmp.groupby("製造批號", as_index=False).agg(
        value=(col, "mean")
    )

# =========================
# SPC DATA
# =========================
spc = {
    "ΔL": {
        "lab": prep_lab(df, "入料檢測 ΔL 正面"),
        "line": prep_spc(df, "正-北 ΔL", "正-南 ΔL")
    },
    "Δa": {
        "lab": prep_lab(df, "入料檢測 Δa 正面"),
        "line": prep_spc(df, "正-北 Δa", "正-南 Δa")
    },
    "Δb": {
        "lab": prep_lab(df, "入料檢測 Δb 正面"),
        "line": prep_spc(df, "正-北 Δb", "正-南 Δb")
    }
}

# =========================
# SUMMARY TABLE
# =========================
summary_line = []
summary_lab = []

for k in spc:
    line_vals = spc[k]["line"]["value"]
    lab_vals = spc[k]["lab"]["value"]

    summary_line.append({
        "Factor": k,
        "Min": round(line_vals.min(), 2),
        "Max": round(line_vals.max(), 2),
        "Mean": round(line_vals.mean(), 2),
        "Std Dev": round(line_vals.std(), 2),
        "n": line_vals.count()
    })

    summary_lab.append({
        "Factor": k,
        "Min": round(lab_vals.min(), 2),
        "Max": round(lab_vals.max(), 2),
        "Mean": round(lab_vals.mean(), 2),
        "Std Dev": round(lab_vals.std(), 2),
        "n": lab_vals.count()
    })

st.markdown("### 📋 SPC Summary Statistics")

c1, c2 = st.columns(2)
with c1:
    st.markdown("#### 🏭 LINE")
    st.dataframe(pd.DataFrame(summary_line), hide_index=True)

with c2:
    st.markdown("#### 🧪 LAB")
    st.dataframe(pd.DataFrame(summary_lab), hide_index=True)
