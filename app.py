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

# ===============================
# 4. NORMALIZE COLUMN NAMES
# ===============================
df.columns = (
    df.columns
    .str.replace('\n', ' ', regex=False)
    .str.replace('  ', ' ', regex=False)
    .str.strip()
)

# ===============================
# 5. RENAME COLUMNS (SPC STANDARD)
# ===============================
COLUMN_MAP = {
    "製造批號": "Batch",
    "Coil No.": "Coil",
    "Time": "Time",

    "正-北 ΔE": "ΔE_N",
    "正-南 ΔE": "ΔE_S",
    "Average value ΔE 正面": "ΔE_avg",

    "正-北 ΔL": "ΔL_N",
    "正-南 ΔL": "ΔL_S",
    "Average value ΔL 正面": "ΔL_avg",

    "正-北 Δa": "Δa_N",
    "正-南 Δa": "Δa_S",
    "Average value Δa 正面": "Δa_avg",

    "正-北 Δb": "Δb_N",
    "正-南 Δb": "Δb_S",
    "Average value Δb 正面": "Δb_avg",

    "入料檢測 ΔE 正面": "ΔE_input",
    "入料檢測 ΔL 正面": "ΔL_input",
    "入料檢測 Δa 正面": "Δa_input",
    "入料檢測 Δb 正面": "Δb_input",
}

df = df.rename(columns=COLUMN_MAP)

st.success("Google Sheets data loaded and normalized successfully.")

# ===============================
# 6. DATA SUMMARY
# ===============================
st.subheader("Data summary")
st.write("Total rows:", len(df))
st.write("Total columns:", len(df.columns))

# ===============================
# 7. FINAL COLUMN NAMES
# ===============================
st.subheader("Final column names (SPC ready)")
st.write(df.columns.tolist())

# ===============================
# 8. FULL DATA VIEW
# ===============================
st.subheader("Full dataset")
st.dataframe(
    df,
    use_container_width=True,
    height=800
)

# ===============================
# 9. DOWNLOAD CSV
# ===============================
st.download_button(
    label="Download full dataset (CSV)",
    data=df.to_csv(index=False),
    file_name="spc_full_data.csv",
    mime="text/csv"
)

