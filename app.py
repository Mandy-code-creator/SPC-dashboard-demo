import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import urllib.request

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
DATA_URL = "https://docs.google.com/spreadsheets/d/1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534/export?format=csv&gid=0"

@st.cache_data(ttl=300)
def load_data(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as r:
        return pd.read_csv(r)

df = load_data(DATA_URL)

# =========================
# CLEAN COLUMN NAMES
# =========================
df.columns = (
    df.columns.astype(str)
    .str.replace("\n", " ")
    .str.replace("　", " ")
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)

st.success("✅ Data loaded successfully")

# =========================
# COLUMN SELECTION (NO GUESS)
# =========================
st.sidebar.header("🔧 Column Mapping (Required)")

batch_col = st.sidebar.selectbox(
    "Batch column",
    df.columns
)

color_col = st.sidebar.selectbox(
    "Paint / Color code column",
    df.columns
)

lab_col = st.sidebar.selectbox(
    "LAB (Incoming / IQC) ΔL column",
    df.columns
)

line_north = st.sidebar.selectbox(
    "LINE ΔL – North",
    df.columns
)

line_south = st.sidebar.selectbox(
    "LINE ΔL – South",
    df.columns
)

# =========================
# FILTER COLOR
# =========================
st.sidebar.header("🎨 Filter")

colors = sorted(df[color_col].dropna().unique())
selected_colors = st.sidebar.multiselect(
    "Select color",
    colors,
    default=colors
)

df = df[df[color_col].isin(selected_colors)]

# =========================
# LAB – INCOMING
# =========================
lab_df = (
    df[[color_col, batch_col, lab_col]]
    .dropna()
    .groupby([color_col, batch_col])
    .agg(LAB_mean=(lab_col, "mean"))
    .reset_index()
)

# =========================
# LINE – PRODUCTION
# =========================
line_df = df[[color_col, batch_col, line_north, line_south]].dropna()
line_df["LINE_mean"] = line_df[[line_north, line_south]].mean(axis=1)

line_batch = (
    line_df
    .groupby([color_col, batch_col])
    .agg(LINE_mean=("LINE_mean", "mean"))
    .reset_index()
)

# =========================
# MERGE LAB vs LINE
# =========================
compare_df = pd.merge(
    lab_df,
    line_batch,
    on=[color_col, batch_col],
    how="inner"
)

# =========================
# LAB vs LINE CHART
# =========================
st.subheader("📈 LAB vs LINE (ΔL)")

for c in compare_df[color_col].unique():
    sub = compare_df[compare_df[color_col] == c]

    fig, ax = plt.subplots(figsize=(10,4))
    ax.plot(sub[batch_col], sub["LAB_mean"], marker="o", label="LAB (Incoming)")
    ax.plot(sub[batch_col], sub["LINE_mean"], marker="s", label="LINE (Production)")

    ax.set_title(f"Color: {c}")
    ax.set_xlabel("Batch")
    ax.set_ylabel("ΔL")
    ax.legend()
    ax.grid(True)
    plt.xticks(rotation=45, ha="right")

    st.pyplot(fig)

# =========================
# SPC CHART – LINE
# =========================
st.subheader("📊 SPC Chart – LINE ΔL")

vals = line_batch["LINE_mean"]
mean = vals.mean()
std = vals.std()

ucl = mean + 3 * std
lcl = mean - 3 * std

fig, ax = plt.subplots(figsize=(10,4))
ax.plot(line_batch[batch_col], vals, marker="o")
ax.axhline(mean, linestyle="--", label="Mean")
ax.axhline(ucl, linestyle="--", color="red", label="UCL (+3σ)")
ax.axhline(lcl, linestyle="--", color="red", label="LCL (-3σ)")
ax.legend()
ax.grid(True)
plt.xticks(rotation=45, ha="right")

st.pyplot(fig)

# =========================
# DISTRIBUTION (NO SCIPY)
# =========================
st.subheader("📉 Distribution – LINE ΔL")

fig, ax = plt.subplots(figsize=(6,4))
ax.hist(vals, bins=15, density=True, alpha=0.6)

x = np.linspace(vals.min(), vals.max(), 200)
pdf = (1 / (std * np.sqrt(2*np.pi))) * np.exp(-0.5*((x-mean)/std)**2)
ax.plot(x, pdf)

ax.set_xlabel("ΔL")
ax.set_ylabel("Density")
ax.set_title("Normal Distribution")

st.pyplot(fig)

# =========================
# TABLES
# =========================
st.subheader("📋 LAB – Batch Mean")
st.dataframe(lab_df, use_container_width=True)

st.subheader("📋 LINE – Batch Mean")
st.dataframe(line_batch, use_container_width=True)

st.subheader("📋 LAB vs LINE")
st.dataframe(compare_df, use_container_width=True)

# =========================
# EXPORT
# =========================
csv = compare_df.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    "⬇️ Download CSV",
    csv,
    "LAB_vs_LINE.csv",
    "text/csv"
)
