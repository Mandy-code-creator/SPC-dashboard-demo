import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import math

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="SPC Color Dashboard",
    page_icon="🎨",
    layout="wide"
)

st.title("🎨 SPC Color Dashboard")

# =========================
# NORMAL DISTRIBUTION (NO SCIPY)
# =========================
def normal_pdf(x, mean, std):
    return (1 / (std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mean) / std) ** 2)

# =========================
# LOAD DATA
# =========================
DATA_URL = "https://docs.google.com/spreadsheets/d/1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534/export?format=csv"
LAB_URL  = "https://docs.google.com/spreadsheets/d/1jbP8puBraQ5Xgs9oIpJ7PlLpjIK3sltrgbrgKUcJ-Qo/export?format=csv"

@st.cache_data
def load_data():
    line = pd.read_csv(DATA_URL)
    lab  = pd.read_csv(LAB_URL)
    return line, lab

df_line, df_lab = load_data()

# =========================
# STANDARDIZE COLUMNS
# =========================
df_line["Batch"] = df_line["Batch"].astype(str)
df_lab["Batch"]  = df_lab["Batch"].astype(str)

# =========================
# FILTER
# =========================
color_list = sorted(df_line["塗料編號"].dropna().unique())
color = st.selectbox("Select Color Code", color_list)

line_f = df_line[df_line["塗料編號"] == color]
lab_f  = df_lab[df_lab["塗料編號"] == color]

# =========================
# COMPUTE DELTA E
# =========================
def delta_e(df):
    if {"L","a","b"}.issubset(df.columns):
        return np.sqrt(df["L"]**2 + df["a"]**2 + df["b"]**2)
    else:
        return abs(df["L"])

line_f["DeltaE"] = delta_e(line_f)
lab_f["DeltaE"]  = delta_e(lab_f)

# =========================
# CHART FIRST
# =========================
st.subheader("📈 LAB vs LINE Trend")

fig, ax = plt.subplots()
ax.plot(lab_f["Batch"], lab_f["DeltaE"], marker="o", label="LAB (Incoming / IQC)")
ax.plot(line_f["Batch"], line_f["DeltaE"], marker="s", label="LINE")
ax.axhline(0.5, linestyle="--", label="LAB Limit (0.5)")
ax.axhline(1.0, linestyle="--", label="LINE Limit (1.0)")
ax.legend()
ax.set_xlabel("Batch")
ax.set_ylabel("Delta E")
st.pyplot(fig)

# =========================
# SPC CHART
# =========================
st.subheader("📊 SPC Chart")

mean = line_f["DeltaE"].mean()
std  = line_f["DeltaE"].std()

ucl = mean + 3*std
lcl = mean - 3*std

fig2, ax2 = plt.subplots()
ax2.plot(line_f["Batch"], line_f["DeltaE"], marker="o")
ax2.axhline(mean, label="Mean")
ax2.axhline(ucl, linestyle="--", label="UCL")
ax2.axhline(lcl, linestyle="--", label="LCL")
ax2.legend()
st.pyplot(fig2)

# =========================
# DISTRIBUTION
# =========================
st.subheader("📉 Distribution")

data = line_f["DeltaE"]
x = np.linspace(data.min(), data.max(), 200)

fig3, ax3 = plt.subplots()
ax3.hist(data, bins=10, density=True, alpha=0.6)
ax3.plot(x, normal_pdf(x, mean, std))
st.pyplot(fig3)

# =========================
# TABLES
# =========================
st.subheader("📋 LAB Summary")
st.dataframe(lab_f.groupby("Batch")["DeltaE"].mean().round(2))

st.subheader("📋 LINE Summary")
st.dataframe(line_f.groupby("Batch")["DeltaE"].mean().round(2))
