import streamlit as st
import pandas as pd

# ===============================
# 1. CẤU HÌNH TRANG
# ===============================
st.set_page_config(
    page_title="SPC Dashboard – Data Viewer",
    layout="wide"
)

st.title("SPC – Google Sheet Data Viewer")

# ===============================
# 2. LINK GOOGLE SHEET (CSV)
# ===============================
url = (
    "https://docs.google.com/spreadsheets/d/"
    "1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534"
    "/gviz/tq?tqx=out:csv"
)

# ===============================
# 3. ĐỌC DỮ LIỆU
# ===============================
df = pd.read_csv(url)

st.success("Đọc dữ liệu từ Google Sheet thành công!")

# ===============================
# 4. THÔNG TIN TỔNG QUAN (KIỂM TRA ĐỦ DỮ LIỆU)
# ===============================
st.write("Tổng số dòng:", len(df))
st.write("Tổng số cột:", len(df.columns))

# ===============================
# 5. HIỂN THỊ DANH SÁCH CỘT
# ===============================
st.subheader("Danh sách tên cột (gốc)")
st.write(df.columns.tolist())

# ===============================
# 6. HIỂN THỊ ĐẦY ĐỦ DỮ LIỆU (SCROLL)
# ===============================
st.subheader("Toàn bộ dữ liệu")

st.dataframe(
    df,
    use_container_width=True,
    height=800
)

# ===============================
# 7. (TUỲ CHỌN) DOWNLOAD CSV
# ===============================
st.download_button(
    label="Download toàn bộ dữ liệu (CSV)",
    data=df.to_csv(index=False),
    file_name="spc_full_data.csv",
    mime="text/csv"
)
