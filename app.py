import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import urllib.request
from scipy.stats import norm

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="SPC Color Dashboard",
    page_icon="🎨",
    layout="wide"
)

# =========================
# GOOGLE SHEET
# =========================
DATA_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534/"
    "export?format=csv&gid=0"
)

COLOR_COL = "塗料編號"
BATCH_COL = "製造批號"

# =========================
# LOAD DATA
# =========================
@st.cache_data(ttl=300)
def load_data(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as r:
        return pd.read_csv(r)

df = load_data(DATA_URL)

# =========================
# CLEAN & FIX DATA
# =========================
df.columns = df.columns.astype(str).str.strip()
df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
df = df.dropna(subset=["Time"])
df[COLOR_COL] = df[COLOR_COL].astype(str)
df[BATCH_COL] = df[BATCH_COL].astype(str)

# =========================
# SIDEBAR FILTER
# =========================
st.sidebar.title("🎨 Filter")

color = st.sidebar.selectbox(
    "Color code",
    sorted(df[COLOR_COL].unique())
)

df = df[df[COLOR_COL] == color]

year = st.sidebar.selectbox(
    "Year",
    sorted(df["Time"].dt.year.unique())
)

month = st.sidebar.multiselect(
    "Month (optional)",
    sorted(df["Time"].dt.month.unique())
)

df = df[df["Time"].dt.year == year]
if month:
    df = df[df["Time"].dt.month.isin(month)]

# =====================================================
# HEADER
# =====================================================
st.title("🎨 SPC Color Quality Dashboard")
st.markdown(f"### 📅 Time Range: {year} {f'| Month: {month}' if month else ''}")
st.divider()

# =====================================================
# LINE DATA
# =====================================================
def calc_line(df):
    tmp = df[
        [
            COLOR_COL, BATCH_COL,
            "正-北 ΔL", "正-南 ΔL",
            "正-北 Δa", "正-南 Δa",
            "正-北 Δb", "正-南 Δb",
        ]
    ].dropna()

    tmp["L"] = tmp[["正-北 ΔL", "正-南 ΔL"]].mean(axis=1)
    tmp["a"] = tmp[["正-北 Δa", "正-南 Δa"]].mean(axis=1)
    tmp["b"] = tmp[["正-北 Δb", "正-南 Δb"]].mean(axis=1)

    return tmp[[COLOR_COL, BATCH_COL, "L", "a", "b"]]

line_batch = (
    calc_line(df)
    .groupby([COLOR_COL, BATCH_COL])
    .mean()
    .round(3)
    .reset_index()
    .rename(columns={"L": "L_LINE", "a": "a_LINE", "b": "b_LINE"})
)

# =====================================================
# LAB DATA
# =====================================================
lab_df = df[
    [
        COLOR_COL, BATCH_COL,
        "入料檢測 ΔL 正面",
        "入料檢測 Δa 正面",
        "入料檢測 Δb 正面",
    ]
].dropna()

lab_batch = (
    lab_df.rename(columns={
        "入料檢測 ΔL 正面": "L",
        "入料檢測 Δa 正面": "a",
        "入料檢測 Δb 正面": "b",
    })
    .groupby([COLOR_COL, BATCH_COL])
    .mean()
    .round(3)
    .reset_index()
    .rename(columns={"L": "L_LAB", "a": "a_LAB", "b": "b_LAB"})
)

# =====================================================
# SUMMARY
# =====================================================
st.header("📊 Summary Statistics")

def summary(df, cols):
    return (
        df[cols]
        .agg(["mean", "max", "min", "std"])
        .T.round(3)
        .rename(columns={
            "mean": "Mean",
            "max": "Max",
            "min": "Min",
            "std": "Stdev"
        })
    )

c1, c2 = st.columns(2)
with c1:
    st.subheader("🏭 LINE")
    st.dataframe(summary(line_batch, ["L_LINE", "a_LINE", "b_LINE"]))

with c2:
    st.subheader("🧪 LAB")
    st.dataframe(summary(lab_batch, ["L_LAB", "a_LAB", "b_LAB"]))

st.divider()

# =====================================================
# MERGE
# =====================================================
compare = pd.merge(
    lab_batch, line_batch,
    on=[COLOR_COL, BATCH_COL],
    how="inner"
)

compare["Delta_E"] = np.sqrt(
    (compare["L_LINE"] - compare["L_LAB"])**2 +
    (compare["a_LINE"] - compare["a_LAB"])**2 +
    (compare["b_LINE"] - compare["b_LAB"])**2
)

# =====================================================
# SPC FUNCTIONS
# =====================================================
def imr_limits(x):
    mr = np.abs(np.diff(x))
    mean = x.mean()
    mrbar = mr.mean()
    return mean, mean + 2.66 * mrbar, mean - 2.66 * mrbar

def cp_cpk(x, lsl, usl):
    mean = x.mean()
    std = x.std(ddof=1)
    cp = (usl - lsl) / (6 * std)
    cpk = min((usl - mean), (mean - lsl)) / (3 * std)
    return round(cp, 2), round(cpk, 2)

# =====================================================
# SPC I-MR
# =====================================================
st.header("📈 SPC I-MR Chart")

metric = st.selectbox(
    "Select Metric",
    ["L_LINE", "a_LINE", "b_LINE", "Delta_E"]
)

x = compare.sort_values(BATCH_COL)[metric].values
mean, UCL, LCL = imr_limits(x)

fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(x, marker="o")
ax.axhline(mean, linestyle="--", label="Mean")
ax.axhline(UCL, color="red", linestyle="--", label="UCL")
ax.axhline(LCL, color="red", linestyle="--", label="LCL")

# 🚨 Out-of-control
for i, v in enumerate(x):
    if v > UCL or v < LCL:
        ax.plot(i, v, "ro")

ax.legend()
ax.grid(True)
st.pyplot(fig)

# =====================================================
# XBAR-R CHART
# =====================================================
st.header("📉 SPC X̄–R Chart")

subgroup = calc_line(df)

xbar = subgroup.groupby(BATCH_COL)["L"].mean()
r = subgroup.groupby(BATCH_COL)["L"].max() - subgroup.groupby(BATCH_COL)["L"].min()

xbar_bar = xbar.mean()
r_bar = r.mean()

UCLx = xbar_bar + 0.577 * r_bar
LCLx = xbar_bar - 0.577 * r_bar

fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(xbar.index, xbar.values, marker="o")
ax.axhline(xbar_bar, linestyle="--")
ax.axhline(UCLx, color="red", linestyle="--")
ax.axhline(LCLx, color="red", linestyle="--")
ax.grid(True)
st.pyplot(fig)

# =====================================================
# Cp / Cpk + NORMAL CURVE
# =====================================================
st.header("🎯 Process Capability (Cp / Cpk)")

lsl = st.number_input("LSL", value=-1.0)
usl = st.number_input("USL", value=1.0)

cp, cpk = cp_cpk(x, lsl, usl)

st.metric("Cp", cp)
st.metric("Cpk", cpk)

fig, ax = plt.subplots(figsize=(8, 4))
ax.hist(x, bins=10, density=True, alpha=0.6)
xmin, xmax = ax.get_xlim()
xx = np.linspace(xmin, xmax, 100)
ax.plot(xx, norm.pdf(xx, x.mean(), x.std()), "r-")
ax.axvline(lsl, color="red", linestyle="--")
ax.axvline(usl, color="red", linestyle="--")
ax.set_title("Normal Distribution with Spec Limits")
ax.grid(True)
st.pyplot(fig)
