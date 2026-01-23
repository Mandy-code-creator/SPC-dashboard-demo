import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="SPC Color Dashboard",
    page_icon="📈",
    layout="wide"
)

# =========================
# TITLE
# =========================
st.title("📈 SPC Color Dashboard")
st.caption("Xbar–R | Cp / Cpk | Normal Distribution")

# =========================
# DATA UPLOAD (FIX ERROR)
# =========================
st.subheader("📂 Upload Data")

uploaded_file = st.file_uploader(
    "Upload CSV file",
    type=["csv"]
)

if uploaded_file is None:
    st.warning("⬆️ Please upload a CSV file to continue")
    st.stop()

df = pd.read_csv(uploaded_file)

# =========================
# REQUIRED COLUMNS CHECK
# =========================
required_cols = [
    "Time", "Batch",
    "L_LINE", "a_LINE", "b_LINE",
    "L_LAB", "a_LAB", "b_LAB"
]

missing = [c for c in required_cols if c not in df.columns]

if missing:
    st.error(f"❌ Missing columns: {missing}")
    st.stop()

df["Time"] = pd.to_datetime(df["Time"])

# =========================
# TIME RANGE
# =========================
st.subheader("⏱ Time Range")

start_date, end_date = st.date_input(
    "Select time range",
    [df["Time"].min(), df["Time"].max()]
)

df = df[
    (df["Time"] >= pd.to_datetime(start_date)) &
    (df["Time"] <= pd.to_datetime(end_date))
]

# =========================
# SUMMARY TABLE
# =========================
def summary_table(df, cols):
    return (
        df[cols]
        .agg(["mean", "max", "min", "std"])
        .T
        .rename(columns={
            "mean": "Mean",
            "max": "Max",
            "min": "Min",
            "std": "Stdev"
        })
        .round(2)
        .reset_index()
        .rename(columns={"index": "Metric"})
    )

st.subheader("📊 Summary Statistics")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🏭 LINE")
    st.dataframe(
        summary_table(df, ["L_LINE", "a_LINE", "b_LINE"]),
        use_container_width=True
    )

with col2:
    st.markdown("### 🧪 LAB")
    st.dataframe(
        summary_table(df, ["L_LAB", "a_LAB", "b_LAB"]),
        use_container_width=True
    )

# =========================
# XBAR-R CHART (TEXTBOOK)
# =========================
st.subheader("📈 SPC Xbar–R Chart")

metric = st.selectbox(
    "Select metric",
    ["L_LINE", "a_LINE", "b_LINE"]
)

group = df.groupby("Batch")[metric]
xbar = group.mean()
r = group.max() - group.min()

xbar_bar = xbar.mean()
r_bar = r.mean()

# SPC constants (n≈5)
A2 = 0.577
D3 = 0
D4 = 2.114

UCLx = xbar_bar + A2 * r_bar
LCLx = xbar_bar - A2 * r_bar
UCLr = D4 * r_bar
LCLr = D3 * r_bar

out = (xbar > UCLx) | (xbar < LCLx)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True)

ax1.plot(xbar.index, xbar, marker="o")
ax1.scatter(xbar.index[out], xbar[out], color="red", zorder=5)
ax1.axhline(xbar_bar, linestyle="--", label="Mean")
ax1.axhline(UCLx, color="red", linestyle="--")
ax1.axhline(LCLx, color="red", linestyle="--")
ax1.set_title("X̄ Chart")
ax1.grid(True)

ax2.plot(r.index, r, marker="o")
ax2.axhline(r_bar, linestyle="--", label="R̄")
ax2.axhline(UCLr, color="red", linestyle="--")
ax2.axhline(LCLr, color="red", linestyle="--")
ax2.set_title("R Chart")
ax2.grid(True)

st.pyplot(fig)

# =========================
# CP / CPK + NORMAL CURVE
# =========================
st.subheader("🎯 Cp / Cpk & Normal Distribution")

USL = st.number_input("USL", value=float(df[metric].max()))
LSL = st.number_input("LSL", value=float(df[metric].min()))

mu = df[metric].mean()
sigma = df[metric].std()

Cp = (USL - LSL) / (6 * sigma)
Cpk = min(
    (USL - mu) / (3 * sigma),
    (mu - LSL) / (3 * sigma)
)

st.metric("Cp", round(Cp, 2))
st.metric("Cpk", round(Cpk, 2))

x = np.linspace(mu - 4*sigma, mu + 4*sigma, 200)
y = stats.norm.pdf(x, mu, sigma)

fig2, ax = plt.subplots(figsize=(10, 4))
ax.plot(x, y)
ax.axvline(USL, color="red", linestyle="--", label="USL")
ax.axvline(LSL, color="red", linestyle="--", label="LSL")
ax.axvline(mu, linestyle="--", label="Mean")
ax.legend()
ax.grid(True)

st.pyplot(fig2)

# =========================
# EXPORT PDF
# =========================
st.subheader("📄 Export SPC PDF")

def export_pdf():
    buf = BytesIO()
    doc = SimpleDocTemplate(buf)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("SPC Report", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Metric: {metric}", styles["Normal"]))
    story.append(Paragraph(f"Cp: {Cp:.2f}", styles["Normal"]))
    story.append(Paragraph(f"Cpk: {Cpk:.2f}", styles["Normal"]))

    doc.build(story)
    buf.seek(0)
    return buf

st.download_button(
    "📥 Download SPC PDF",
    export_pdf(),
    file_name="SPC_Report.pdf",
    mime="application/pdf"
)
