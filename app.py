import streamlit as st
import pandas as pd

# ===============================
# 1. PAGE CONFIG
# ===============================
st.set_page_config(
    page_title="SPC Dashboard – Data Viewer",
    layout="wide"
)

st.title("SPC – Google Sheets Data Viewer")

# ===============================
# 2. GOOGLE SHEET CSV URL
# ===============================
url = (
    "https://docs.google.com/spreadsheets/d/"
    "1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534"
    "/gviz/tq?tqx=out:csv"
)

# ===============================
# 3. LOAD DATA
# ===============================
df = pd.read_csv(url)

st.success("Google Sheets data loaded successfully.")

# ===============================
# 4. DATA SUMMARY
# ===============================
st.write("Total rows:", len(df))
st.write("Total columns:", len(df.columns))

# ===============================
# 5. COLUMN NAMES (RAW)
# ===============================
st.subheader("Raw column names")
st.write(df.columns.tolist())

# ===============================
# 6. FULL DATA VIEW (SCROLLABLE)
# ===============================
st.subheader("Full dataset")

st.dataframe(
    df,
    use_container_width=True,
    height=800
)

# ===============================
# 7. DOWNLOAD CSV (OPTIONAL)
# ===============================
st.download_button(
    label="Download full dataset (CSV)",
    data=df.to_csv(index=False),
    file_name="spc_full_data.csv",
    mime="text/csv"
)
