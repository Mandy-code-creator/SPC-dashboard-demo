import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math
import io
import os

from reportlab.platypus import SimpleDocTemplate, Image
from reportlab.lib.pagesizes import A4

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(page_title="SPC Distribution", layout="wide")

# =========================
# SAMPLE DATA (thay bằng data của bạn)
# =========================
np.random.seed(1)
spc = {
    "L": {
        "line": {"value": pd.Series(np.random.normal(50, 2, 120))}
    },
    "a": {
        "line": {"value": pd.Series(np.random.normal(20, 1.5, 120))}
    },
    "b": {
        "line": {"value": pd.Series(np.random.normal(10, 1.0, 120))}
    }
}

color = "RED"

def get_limit(color, k, source):
    limits = {
        "L": (45, 55),
        "a": (16, 24),
        "b": (7, 13)
    }
    return limits.get(k, (None, None))

# =========================
# CAPABILITY
# =========================
def calc_capability(values, lsl, usl):
    if lsl is None or usl is None:
        return None, None, None
    mean = values.mean()
    std = values.std()
    if std == 0 or np.isnan(std):
        return None, None, None
    cp = (usl - lsl) / (6 * std)
    cpk = min(
        (usl - mean) / (3 * std),
        (mean - lsl) / (3 * std)
    )
    ca = abs(mean - (usl + lsl) / 2) / ((usl - lsl) / 2)
    return round(ca, 2), round(cp, 2), round(cpk, 2)

# =========================
# NORMAL PDF
# =========================
def normal_pdf(x, mean, std):
    return (1 / (std * math.sqrt(2 * math.pi))) * np.exp(
        -0.5 * ((x - mean) / std) ** 2
    )

# =========================
# SAVE FIG → IMAGE (PDF)
# =========================
def save_fig_to_png(fig, name):
    os.makedirs("tmp", exist_ok=True)
    path = f"tmp/{name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path

pdf_images = []

# =========================
# LINE DISTRIBUTION DASHBOARD
# =========================
st.markdown("## 📈 Line Process Distribution")

cols = st.columns(3)

for i, k in enumerate(spc):
    with cols[i]:
        values = spc[k]["line"]["value"].dropna()
        mean = values.mean()
        std = values.std()
        lsl, usl = get_limit(color, k, "LINE")

        ca, cp, cpk = calc_capability(values, lsl, usl)

        fig, ax = plt.subplots(figsize=(5, 4))

        bins = np.histogram_bin_edges(values, bins=10)
        counts, _, patches = ax.hist(
            values,
            bins=bins,
            color="#4dabf7",
            edgecolor="white",
            alpha=0.85
        )

        # Highlight OOS
        for p, l, r in zip(patches, bins[:-1], bins[1:]):
            center = (l + r) / 2
            if lsl is not None and usl is not None:
                if center < lsl or center > usl:
                    p.set_facecolor("#ff6b6b")

        # Normal curve (long tail)
        if std > 0:
            x = np.linspace(mean - 4 * std, mean + 4 * std, 500)
            pdf = normal_pdf(x, mean, std)
            ax.plot(
                x,
                pdf * len(values) * (bins[1] - bins[0]),
                color="black",
                linewidth=2
            )

        # LSL / USL
        if lsl is not None:
            ax.axvline(lsl, color="red", linestyle="--", linewidth=1.5)
        if usl is not None:
            ax.axvline(usl, color="red", linestyle="--", linewidth=1.5)

        # Capability box
        if cp is not None:
            ax.text(
                0.98, 0.95,
                f"Ca = {ca}\nCp = {cp}\nCpk = {cpk}",
                transform=ax.transAxes,
                ha="right",
                va="top",
                fontsize=9,
                bbox=dict(facecolor="white", alpha=0.9)
            )

        # Info box
        ax.text(
            0.02, 0.95,
            f"N = {len(values)}\nMean = {mean:.2f}\nStd = {std:.2f}",
            transform=ax.transAxes,
            va="top",
            fontsize=9,
            bbox=dict(facecolor="white", alpha=0.9)
        )

        ax.set_title(k)
        ax.grid(axis="y", alpha=0.3)

        st.pyplot(fig)

        # 👉 SAVE IMAGE FOR PDF
        img_path = save_fig_to_png(fig, f"{color}_{k}")
        pdf_images.append(img_path)

# =========================
# EXPORT PDF
# =========================
def export_pdf(images):
    path = "SPC_Distribution_Report.pdf"
    doc = SimpleDocTemplate(path, pagesize=A4)
    story = []
    for img in images:
        story.append(Image(img, width=500, height=350))
    doc.build(story)
    return path

st.markdown("---")

if st.button("📄 Export PDF (with charts)"):
    pdf_path = export_pdf(pdf_images)
    with open(pdf_path, "rb") as f:
        st.download_button(
            "⬇ Download PDF",
            f,
            file_name=pdf_path,
            mime="application/pdf"
        )
