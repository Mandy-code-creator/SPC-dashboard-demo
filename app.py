import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
import numpy as np
import urllib.request

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="SPC Color Dashboard",
    page_icon="🎨",
    layout="wide"
)

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(
            270deg,
            #ffffff,
            #f0f9ff,
            #e0f2fe,
            #fef3c7,
            #ecfeff
        );
        background-size: 800% 800%;
        animation: gradientBG 20s ease infinite;
    }
    @keyframes gradientBG {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# REFRESH BUTTON
# =========================
if st.button("🔄 Refresh data"):
    st.cache_data.clear()
    st.rerun()

# =========================
# SIDEBAR STYLE
# =========================
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background-color: #f6f8fa;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# GOOGLE SHEET LINKS
# =========================
DATA_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534/"
    "export?format=csv&gid=0"
)

LIMIT_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1jbP8puBraQ5Xgs9oIpJ7PlLpjIK3sltrgbrgKUcJ-Qo/"
    "export?format=csv&gid=0"
)

COLOR_COL = "塗料編號"
BATCH_COL = "製造批號"

# =========================
# LOAD DATA
# =========================
@st.cache_data(ttl=300)
def load_data(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req) as response:
        df = pd.read_csv(response)
    return df

df = load_data(DATA_URL)
limit_df = load_data(LIMIT_URL)

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
# TIME COLUMN
# =========================
if "Time" in df.columns:
    df["Time"] = pd.to_datetime(df["Time"], errors="coerce")

st.success("✅ Google Sheets loaded successfully")

# =========================
# COLOR FILTER
# =========================
st.sidebar.header("🎨 Bộ lọc 塗料編號")

color_list = sorted(df[COLOR_COL].dropna().unique())
selected_colors = st.sidebar.multiselect(
    "Chọn 塗料編號",
    color_list,
    default=color_list
)

filtered_df = df[df[COLOR_COL].isin(selected_colors)]

# =========================
# CALC PER COIL
# =========================
def calc_per_coil(df):
    tmp = df[
        [
            BATCH_COL,
            COLOR_COL,
            "正-北 ΔL", "正-南 ΔL",
            "正-北 Δa", "正-南 Δa",
            "正-北 Δb", "正-南 Δb"
        ]
    ].copy()

    tmp = tmp.dropna()

    tmp["L"] = tmp[["正-北 ΔL", "正-南 ΔL"]].mean(axis=1)
    tmp["a"] = tmp[["正-北 Δa", "正-南 Δa"]].mean(axis=1)
    tmp["b"] = tmp[["正-北 Δb", "正-南 Δb"]].mean(axis=1)

    return tmp[[BATCH_COL, COLOR_COL, "L", "a", "b"]]

coil_df = calc_per_coil(filtered_df)

# =========================
# BATCH MEAN
# =========================
batch_mean_df = (
    coil_df
    .groupby([COLOR_COL, BATCH_COL])
    .agg(
        coil_count=("L", "count"),
        L_mean=("L", "mean"),
        a_mean=("a", "mean"),
        b_mean=("b", "mean"),
    )
    .round(2)
    .reset_index()
)

st.subheader("📊 Batch LAB Mean (theo 塗料編號)")
st.dataframe(batch_mean_df, use_container_width=True)

# =========================
# BATCH SUMMARY
# =========================
batch_summary_df = (
    coil_df
    .groupby([COLOR_COL, BATCH_COL])
    .agg(
        coil_count=("L", "count"),

        L_mean=("L", "mean"),
        a_mean=("a", "mean"),
        b_mean=("b", "mean"),

        L_std=("L", "std"),
        a_std=("a", "std"),
        b_std=("b", "std"),

        L_min=("L", "min"),
        a_min=("a", "min"),
        b_min=("b", "min"),

        L_max=("L", "max"),
        a_max=("a", "max"),
        b_max=("b", "max"),
    )
    .round(2)
    .reset_index()
)

st.subheader("📊 Batch LAB Summary (theo 塗料編號)")
st.dataframe(batch_summary_df, use_container_width=True)

# =========================
# TREND CHART
# =========================
st.subheader("📈 So sánh Batch theo 塗料編號")

metric = st.selectbox(
    "Chọn chỉ số",
    ["L_mean", "a_mean", "b_mean"]
)

for color in batch_summary_df[COLOR_COL].unique():
    sub = batch_summary_df[batch_summary_df[COLOR_COL] == color]

    fig, ax = plt.subplots()
    ax.plot(sub[BATCH_COL], sub[metric], marker="o")
    ax.set_title(f"{metric} – 塗料編號 {color}")
    ax.set_xlabel("Batch")
    ax.set_ylabel(metric)
    ax.grid(True)

    st.pyplot(fig)

# =========================
# Z-SCORE OUTLIER
# =========================
st.subheader("🚨 Batch lệch màu (Z-score > 2)")

z_df = batch_summary_df.copy()

for m in ["L_mean", "a_mean", "b_mean"]:
    z_df[f"{m}_z"] = (z_df[m] - z_df[m].mean()) / z_df[m].std()

out_df = z_df[
    (z_df["L_mean_z"].abs() > 2) |
    (z_df["a_mean_z"].abs() > 2) |
    (z_df["b_mean_z"].abs() > 2)
]

if out_df.empty:
    st.success("✅ Không có batch lệch màu bất thường")
else:
    st.warning("⚠️ Phát hiện batch lệch màu")
    st.dataframe(
        out_df[
            [
                COLOR_COL,
                BATCH_COL,
                "L_mean",
                "a_mean",
                "b_mean",
                "coil_count"
            ]
        ],
        use_container_width=True
    )

# =========================
# EXPORT EXCEL
# =========================
st.subheader("📤 Xuất báo cáo")

output = io.BytesIO()
with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
    batch_summary_df.to_excel(
        writer,
        index=False,
        sheet_name="Batch_Summary"
    )
    coil_df.to_excel(
        writer,
        index=False,
        sheet_name="Coil_Data"
    )

st.download_button(
    label="⬇️ Download Excel Report",
    data=output.getvalue(),
    file_name="Batch_LAB_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
