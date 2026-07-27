import base64
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


COLORS = {
    "primary": "#0066FF",
    "primary_dark": "#0052CC",
    "accent": "#00D4FF",
    "danger": "#EF4444",
    "warning": "#F59E0B",
    "success": "#22C55E",
}

PDF_COLORS = {
    "bg": "#FFFFFF",
    "surface": "#F8F9FA",
    "text": "#1A1A2E",
    "muted": "#6B7280",
    "grid": "#E5E7EB",
    "border": "#D1D5DB",
}

plt.rcParams.update({
    "figure.facecolor": PDF_COLORS["bg"],
    "axes.facecolor": PDF_COLORS["bg"],
    "axes.edgecolor": PDF_COLORS["border"],
    "axes.labelcolor": PDF_COLORS["text"],
    "text.color": PDF_COLORS["text"],
    "xtick.color": PDF_COLORS["muted"],
    "ytick.color": PDF_COLORS["muted"],
    "grid.color": PDF_COLORS["grid"],
    "grid.alpha": 0.6,
    "font.size": 9,
    "axes.titlesize": 11,
    "axes.labelsize": 9,
})


def _fig_to_base64(fig, dpi=150):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _null_pct(col, total_rows):
    return round(col.get("missing", 0) / max(total_rows, 1) * 100, 1)


def missing_values_chart(profile, total_rows):
    cols = []
    pcts = []
    for p in profile:
        pct = _null_pct(p, total_rows)
        if pct > 0:
            cols.append(p.get("column", p.get("name", "?")))
            pcts.append(pct)
    if not cols:
        return None

    n = len(cols)
    fig_h = max(2, min(n * 0.45, 5))
    fig, ax = plt.subplots(figsize=(7, fig_h))
    bars = ax.barh(cols, pcts, color=COLORS["danger"], alpha=0.8, height=0.55)
    ax.set_xlabel("Valores nulos (%)")
    ax.set_title("Valores Nulos por Columna", fontweight="bold", pad=8)
    ax.xaxis.set_major_formatter(ticker.PercentFormatter())
    for bar, pct in zip(bars, pcts):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                f"{pct:.1f}%", va="center", fontsize=8, color=PDF_COLORS["muted"])
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    return _fig_to_base64(fig)


def data_types_chart(profile):
    type_counts = {}
    for p in profile:
        t = p.get("detected_type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    labels = list(type_counts.keys())
    values = list(type_counts.values())
    color_map = {
        "number": COLORS["primary"],
        "text": COLORS["warning"],
        "boolean": COLORS["success"],
        "bool": COLORS["success"],
        "datetime": "#9B59B6",
        "mixed": "#9CA3AF",
    }
    colors = [color_map.get(lb, "#9CA3AF") for lb in labels]

    fig, ax = plt.subplots(figsize=(5, 3.5))
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=colors, autopct="%1.0f%%",
        startangle=90, pctdistance=0.75,
        textprops={"color": PDF_COLORS["text"], "fontsize": 9},
    )
    for t in autotexts:
        t.set_fontsize(9)
        t.set_fontweight("bold")
        t.set_color("white")
    ax.set_title("Distribucion de Tipos de Dato", fontweight="bold", pad=8)
    fig.tight_layout()
    return _fig_to_base64(fig)


def cleaning_summary_chart(actions_log):
    action_types = {}
    for action in actions_log:
        t = action.get("action_type", action.get("kind", "other"))
        action_types[t] = action_types.get(t, 0) + 1
    if not action_types:
        return None

    labels = list(action_types.keys())
    values = list(action_types.values())
    bar_colors = [
        COLORS["danger"] if any(k in lb.lower() for k in ("drop", "delete", "remove"))
        else COLORS["primary"]
        for lb in labels
    ]

    n = len(labels)
    fig_h = max(2, min(n * 0.5, 4))
    fig, ax = plt.subplots(figsize=(7, fig_h))
    bars = ax.barh(labels, values, color=bar_colors, alpha=0.8, height=0.55)
    ax.set_xlabel("Cantidad de acciónes")
    ax.set_title("Resumen de Acciónes de Limpieza", fontweight="bold", pad=8)
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=9, fontweight="bold", color=PDF_COLORS["text"])
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    return _fig_to_base64(fig)


def quality_score_gauge(score):
    fig, ax = plt.subplots(figsize=(5, 1.5))
    color = COLORS["success"] if score >= 80 else COLORS["warning"] if score >= 50 else COLORS["danger"]
    ax.barh([0], [score], color=color, height=0.5, alpha=0.85)
    ax.barh([0], [100 - score], left=[score], color=PDF_COLORS["grid"], height=0.5, alpha=0.5)
    ax.set_xlim(0, 100)
    ax.set_yticks([])
    ax.set_xlabel("Score")
    ax.set_title(f"Calidad General: {score:.0f}/100", fontweight="bold", pad=8)
    ax.text(score / 2, 0, f"{score:.0f}%", ha="center", va="center",
            fontsize=12, fontweight="bold", color="white")
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    return _fig_to_base64(fig)


def generate_all_charts(profile, total_rows=None, actions_log=None):
    charts = {}
    if total_rows is None:
        total_rows = max((p.get("total_rows", 0) for p in profile), default=0)
    mv = missing_values_chart(profile, total_rows)
    if mv:
        charts["missing_values"] = mv
    charts["data_types"] = data_types_chart(profile)
    score = _estimate_quality_score(profile, total_rows)
    g = quality_score_gauge(score)
    if g:
        charts["quality_gauge"] = g
    if actions_log:
        cs = cleaning_summary_chart(actions_log)
        if cs:
            charts["cleaning_summary"] = cs
    return charts


def _estimate_quality_score(profile, total_rows=None):
    if not profile:
        return 0
    if total_rows is None:
        total_rows = max((p.get("total_rows", 0) for p in profile), default=0)
    total = 0
    for p in profile:
        completeness = 100 - _null_pct(p, total_rows)
        total += completeness
    return round(total / len(profile), 1)
