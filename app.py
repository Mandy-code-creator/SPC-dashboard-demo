def spc_combined(lab, line, title, lab_lim, line_lim):
    fig, ax = plt.subplots(figsize=(12, 4))

    mean = line["value"].mean()
    std = line["value"].std()

    ax.plot(lab["製造批號"], lab["value"], "o-", label="LAB", color="#1f77b4")
    ax.plot(line["製造批號"], line["value"], "o-", label="LINE", color="#2ca02c")

    ax.axhline(mean + 3 * std, color="orange", linestyle="--", label="+3σ")
    ax.axhline(mean - 3 * std, color="orange", linestyle="--", label="-3σ")

    if lab_lim[0] is not None:
        ax.axhline(lab_lim[0], color="#1f77b4", linestyle=":", label="LAB LCL")
        ax.axhline(lab_lim[1], color="#1f77b4", linestyle=":", label="LAB UCL")

    if line_lim[0] is not None:
        ax.axhline(line_lim[0], color="red", label="LINE LCL")
        ax.axhline(line_lim[1], color="red", label="LINE UCL")

    # ===== ĐÁNH DẤU CÁC ĐIỂM VƯỢT GIỚI HẠN =====
    if line_lim[0] is not None and line_lim[1] is not None:
        for batch, val in zip(line["製造批號"], line["value"]):
            if val < line_lim[0] or val > line_lim[1]:
                ax.scatter(batch, val, color="red", s=80, zorder=5)
                ax.text(batch, val, f"{batch}\n{val:.2f}",
                        color="red", fontsize=8, ha="center", va="bottom", rotation=45)

    if lab_lim[0] is not None and lab_lim[1] is not None:
        for batch, val in zip(lab["製造批號"], lab["value"]):
            if val < lab_lim[0] or val > lab_lim[1]:
                ax.scatter(batch, val, color="red", s=80, marker="x", zorder=5)
                ax.text(batch, val, f"{batch}\n{val:.2f}",
                        color="red", fontsize=8, ha="center", va="bottom", rotation=45)

    ax.set_title(title)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.grid(True)
    ax.tick_params(axis="x", rotation=45)
    fig.subplots_adjust(right=0.78)
    return fig
