import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
import numpy as np
import math

# ===== PDF =====
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm

# =========================
# PDF HELPER
# =========================
def fig_to_rl_image(fig, width_cm=16):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    img = Image(buf)
    img.drawWidth = width_cm * cm
    img.drawHeight = img.drawWidth * img.imageHeight / img.imageWidth
    return img

def export_pdf_report(color, year, summary_line_df, summary_lab_df, figs):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(
        f"<b>SPC COLOR REPORT</b><br/>Color: {color} | Year: {year}",
        styles["Title"]
    ))
    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>LINE SUMMARY</b>", styles["Heading2"]))
    for _, r in summary_line_df.iterrows():
        story.append(Paragraph(
            f"{r['Factor']} | Mean={r['Mean']} | Std={r['Std Dev']} | "
            f"Min={r['Min']} | Max={r['Max']}",
            styles["Normal"]
        ))

    story.append(Spacer(1, 12))
    story.append(Paragraph("<b>LAB SUMMARY</b>", styles["Heading2"]))
    for _, r in summary_lab_df.iterrows():
        story.append(Paragraph(
            f"{r['Factor']} | Mean={r['Mean']} | Std={r['Std Dev']} | "
            f"Min={r['Min']} | Max={r['Max']}",
            styles["Normal"]
        ))

    story.append(PageBreak())
    story.append(Paragraph("<b>CONTROL CHARTS</b>", styles["Heading2"]))
    story.append(Spacer(1, 12))

    for fig in figs:
        story.append(fig_to_rl_image(fig))
        story.append(Spacer(1, 16))

    doc.build(story)
    buf.seek(0)
    return buf

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="SPC Color Dashboard",
    page_icon="📊",
    layout="wide"
)

# =========================
# LOAD DATA
# =========================
DATA_URL = "https://docs.google.com/spreadsheets/d/1lqsLKSoDTbtvAsHzJaEri8tPo5pA3vqJ__LVHp2R534/export?format=csv"
LIMIT_URL = "https://docs.google.com/spreadsheets/d/1jbP8puBraQ5Xgs9oIpJ7PlLpjIK3sltrgbrgKUcJ-Qo/export?format=csv"

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
# FILTER
# =========================
df["year"] = df["Time"].dt.year
color = st.sidebar.selectbox("Color", sorted(df["塗料編號"].dropna().unique()))
df = df[df["塗料編號"] == color]

year = st.sidebar.selectbox("Year", sorted(df["year"].unique()))
df = df[df["year"] == year]

# =========================
# SPC PREP
# =========================
def prep_spc(df, a, b):
    tmp = df.copy()
    tmp["value"] = tmp[[a, b]].mean(axis=1)
    return tmp.groupby("製造批號", as_index=False).agg(value=("value", "mean"))

def prep_lab(df, col):
    return df.groupby("製造批號", as_index=False).agg(value=(col, "mean"))

spc = {
    "ΔL": {
        "lab": prep_lab(df, "入料檢測 ΔL 正面"),
        "line": prep_spc(df, "正-北 ΔL", "正-南 ΔL")
    },
    "Δa": {
        "lab": prep_lab(df, "入料檢測 Δa 正面"),
        "line": prep_spc(df, "正-北 Δa", "正-南 Δa")
    },
    "Δb": {
        "lab": prep_lab(df, "入料檢測 Δb 正面"),
        "line": prep_spc(df, "正-北 Δb", "正-南 Δb")
    }
}

# =========================
# SUMMARY
# =========================
summary_line, summary_lab = [], []

for k in spc:
    for name, target in [("line", summary_line), ("lab", summary_lab)]:
        v = spc[k][name]["value"]
        target.append({
            "Factor": k,
            "Min": round(v.min(), 2),
            "Max": round(v.max(), 2),
            "Mean": round(v.mean(), 2),
            "Std Dev": round(v.std(), 2)
        })

summary_line_df = pd.DataFrame(summary_line)
summary_lab_df = pd.DataFrame(summary_lab)

# =========================
# CHARTS
# =========================
def spc_combined(lab, line, title):
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(lab.index, lab["value"], "o-", label="LAB")
    ax.plot(line.index, line["value"], "o-", label="LINE")
    ax.set_title(title)
    ax.legend()
    ax.grid(True)
    return fig

st.markdown("### 📊 CONTROL CHARTS")

pdf_figs = []

for k in spc:
    fig = spc_combined(
        spc[k]["lab"],
        spc[k]["line"],
        f"{k} LAB vs LINE"
    )
    st.pyplot(fig)
    pdf_figs.append(fig)

# =========================
# EXPORT PDF
# =========================
st.markdown("### 📄 Export PDF")

pdf_buf = export_pdf_report(
    color,
    year,
    summary_line_df,
    summary_lab_df,
    pdf_figs
)

st.download_button(
    "⬇ Download SPC Audit PDF",
    data=pdf_buf,
    file_name=f"SPC_Report_{color}_{year}.pdf",
    mime="application/pdf"
)
