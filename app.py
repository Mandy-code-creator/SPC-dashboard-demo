import streamlit as st
import pandas as pd

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="SPC Batch Check",
    layout="wide"
)

st.title("🔍 KIỂM TRA GIÁ TRỊ TRUNG BÌNH THEO BATCH")

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    # 👉 THAY LINK CSV CỦA BẠN Ở ĐÂY
    url = "YOUR_GOOGLE_SHEET_CSV_LINK"
    return pd.read_csv(url)

df = load_data()

st.markdown("### 📄 DỮ LIỆU GỐC (5 dòng đầu)")
st.dataframe(df.head())

# =========================
# KIỂM TRA TRUNG BÌNH THEO BATCH (LINE)
# =========================
st.markdown("---")
st.markdown("## 🧪 BẢNG TRUNG BÌNH THEO BATCH (LINE ΔL / Δa / Δb)")

# 1️⃣ Giữ cuộn có đủ Bắc & Nam
required_cols = [
    "正-北 ΔL", "正-南 ΔL",
    "正-北 Δa", "正-南 Δa",
    "正-北 Δb", "正-南 Δb",
    "顏色代碼", "製造批號"
]

check_df = df[required_cols].dropna().copy()

# 2️⃣ Tính giá trị từng CUỘN
check_df["ΔL_coil"] = check_df[["正-北 ΔL", "正-南 ΔL"]].mean(axis=1)
check_df["Δa_coil"] = check_df[["正-北 Δa", "正-南 Δa"]].mean(axis=1)
check_df["Δb_coil"] = check_df[["正-北 Δb", "正-南 Δb"]].mean(axis=1)

# 3️⃣ Gộp theo BATCH
batch_mean = (
    check_df
    .groupby(["顏色代碼", "製造批號"], as_index=False)
    .agg(
        Mean_ΔL=("ΔL_coil", "mean"),
        Mean_Δa=("Δa_coil", "mean"),
        Mean_Δb=("Δb_coil", "mean"),
        Coil_Count=("Δb_coil", "count")
    )
)

# 4️⃣ Làm tròn để so tay
batch_mean[["Mean_ΔL", "Mean_Δa", "Mean_Δb"]] = (
    batch_mean[["Mean_ΔL", "Mean_Δa", "Mean_Δb"]].round(2)
)

# 5️⃣ HIỂN THỊ
st.dataframe(batch_mean)

# =========================
# FILTER ĐỂ SO TAY
# =========================
st.markdown("---")
st.markdown("## 🎯 LỌC ĐỂ SO TAY")

color_list = sorted(batch_mean["顏色代碼"].unique())
color = st.selectbox("Chọn mã màu", color_list)

batch_list = sorted(
    batch_mean.loc[batch_mean["顏色代碼"] == color, "製造批號"].unique()
)
batch = st.selectbox("Chọn batch", batch_list)

st.markdown("### 📌 KẾT QUẢ BATCH ĐƯỢC CHỌN")
st.dataframe(
    batch_mean[
        (batch_mean["顏色代碼"] == color) &
        (batch_mean["製造批號"] == batch)
    ]
)

# =========================
# CHI TIẾT TỪNG CUỘN (DEBUG)
# =========================
st.markdown("---")
st.markdown("## 🔎 CHI TIẾT TỪNG CUỘN TRONG BATCH")

coil_detail = check_df[
    (check_df["顏色代碼"] == color) &
    (check_df["製造批號"] == batch)
][[
    "正-北 Δb", "正-南 Δb", "Δb_coil"
]]

coil_detail["Δb_coil"] = coil_detail["Δb_coil"].round(3)

st.dataframe(coil_detail)
