import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

st.set_page_config(page_title="SPC Color Dashboard", layout="wide")

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
# SIDEBAR – FILTER
# =========================
st.sidebar.header("📌 Filter")

color = st.sidebar.selectbox(
    "Color code",
    sorted(df["塗料編號"].dropna().unique())
)

df = df[df["塗料編號"] == color]

latest_year = df["Time"].dt.year.max()
year = st.sidebar.selectbox(
    "Year",
    sorted(df["Time"].dt.year.unique()),
    index=list(sorted(df["Time"].dt.year.unique())).index(latest_year)
)

month = st.sidebar.multiselect(
    "Month (optional)",
    sorted(df["Time"].dt.month.unique())
)

df = df[df["Time"].dt.year == year]
if month:
    df = df[df["Time"].dt.month.isin(month)]

st.sidebar.markdown("---")

# =========================
# GET LIMIT FUNCTION
# =========================
def get_limit(color, prefix, factor):
    row = limit_df[limit_df["Color_code"] == color]
    if row.empty:
        return None, None
    return (
        row[f"{factor} {prefix} LCL"].values[0],
        row[f"{factor} {prefix} UCL"].values[0]
    )

# =========================
# PREPARE SPC DATA
# =========================
def prep_spc(df, north_col, south_col):
    tmp = df.copy()
    tmp["value"] = tmp[[north_col, south_col]].mean(axis=1)
    return tmp.groupby("製造批號", as_index=False).agg(
        Time=("Time", "min"),
        value=("value", "mean")
    )

def prep_lab(df, col):
    return df.groupby("製造批號", as_index=False).agg(
        Time=("Time", "min"),
        value=(col, "mean")
    )

# =========================
# SPC CHART FUNCTION
# =========================
def spc_chart(spc_lab, spc_line, title, lab_limit, line_limit):
    fig, ax = plt.subplots(figsize=(12, 4))

    # Mean & sigma (LINE)
    mean = spc_line["value"].mean()
    std = spc_line["value"].std()
    ucl_3s = mean + 3 * std
    lcl_3s = mean - 3 * std

    # Plot LAB & LINE
    ax.plot(spc_lab["Time"], spc_lab["value"], marker="o", label="LAB", color="blue")
    ax.plot(spc_line["Time"], spc_line["value"], marker="o", label="LINE", color="green")

    # ±3σ
    ax.axhline(ucl_3s, color="orange", linestyle="--", label="+3σ")
    ax.axhline(lcl_3s, color="orange", linestyle="--", label="-3σ")

    # LAB limit
    if lab_limit[0] is not None:
        ax.axhline(lab_limit[0], color="blue", linestyle=":")
        ax.axhline(lab_limit[1], color="blue", linestyle=":")

    # LINE limit
    if line_limit[0] is not None:
        ax.axhline(line_limit[0], color="red", linestyle="-")
        ax.axhline(line_limit[1], color="red", linestyle="-")

    # Highlight points
    for _, r in spc_line.iterrows():
        if line_limit[0] is not None and (r["value"] < line_limit[0] or r["value"] > line_limit[1]):
            ax.scatter(r["Time"], r["value"], color="red", s=80)
        elif r["value"] < lcl_3s or r["value"] > ucl_3s:
            ax.scatter(r["Time"], r["value"], color="orange", s=80)

    ax.set_title(title)
    ax.legend()
    ax.grid(True)

    return fig

# =========================
# PREP SPC DATA
# =========================
spc = {
    "ΔL": {
        "lab": prep_lab(df, "入料檢測\n ΔL 正面"),
        "line": prep_spc(df, "正-北\n ΔL", "正-南\nΔL")
    },
    "Δa": {
        "lab": prep_lab(df, "入料檢測\nΔa 正面"),
        "line": prep_spc(df, "正-北\nΔa", "正-南\nΔa")
    },
    "Δb": {
        "lab": prep_lab(df, "入料檢測\nΔb 正面"),
        "line": prep_spc(df, "正-北\nΔb", "正-南\nΔb")
    }
}

# =========================
# MAIN
# =========================
st.title(f"🎨 SPC Color Dashboard – {color}")

# === COMBINED FIRST ===
st.subheader("📊 COMBINED SPC")

for k in ["ΔL", "Δa", "Δb"]:
    lab_l = get_limit(color, k, "LAB")
    line_l = get_limit(color, k, "LINE")

    fig = spc_chart(
        spc[k]["lab"],
        spc[k]["line"],
        f"COMBINED {k}",
        lab_l,
        line_l
    )
    st.pyplot(fig)

st.markdown("---")

# === INDIVIDUAL ===
for k in ["ΔL", "Δa", "Δb"]:
    st.subheader(f"📈 SPC {k}")

    lab_l = get_limit(color, k, "LAB")
    line_l = get_limit(color, k, "LINE")

    fig = spc_chart(
        spc[k]["lab"],
        spc[k]["line"],
        f"{k} SPC",
        lab_l,
        line_l
    )
    st.pyplot(fig)
