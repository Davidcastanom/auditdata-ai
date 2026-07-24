import base64
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


COLORS = {
    "primary": "#0066FF",
    "accent": "#00D4FF",
    "danger": "#FF4444",
    "warning": "#FFB800",
    "success": "#00CC88",
    "bg": "#12121A",
    "text": "#F0F0F5",
    "muted": "#9090A0",
    "surface": "#1A1A2E",
}

plt.rcParams.update({
    "figure.facecolor": COLORS["bg"],
    "axes.facecolor": COLORS["surface"],
    "axes.edgecolor": COLORS["muted"],
    "axes.labelcolor": COLORS["text"],
    "text.color": COLORS["text"],
    "xtick.color": COLORS["muted"],
    "ytick.color": COLORS["muted"],
    "grid.color": "#2A2A3E",
    "grid.alpha": 0.5,
    "font.size": 11,
})


def _fig_to_base64(fig, dpi=150):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())
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

    fig, ax = plt.subplots(figsize=(8, max(3, len(cols) * 0.5)))
    bars = ax.barh(cols, pcts, color=COLORS["danger"], alpha=0.85, height=0.6)
    ax.set_xlabel("Valores nulos (%)")
    ax.set_title("Valores Nulos por Columna", fontsize=14, fontweight="bold", pad=12)
    ax.xaxis.set_major_formatter(ticker.PercentFormatter())
    for bar, pct in zip(bars, pcts):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2, f"{pct:.1f}%", va="center", fontsize=10, color=COLORS["text"])
    ax.invert_yaxis()
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
        "bool": COLORS["success"],
        "datetime": "#9B59B6",
        "mixed": COLORS["muted"],
    }
    colors = [color_map.get(lb, COLORS["muted"]) for lb in labels]

    fig, ax = plt.subplots(figsize=(6, 6))
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=colors, autopct="%1.0f%%",
        startangle=90, pctdistance=0.8, textprops={"color": COLORS["text"]},
    )
    for t in autotexts:
        t.set_fontsize(11)
        t.set_fontweight("bold")
    ax.set_title("Distribucion de Tipos de Dato", fontsize=14, fontweight="bold", pad=12)
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
    bar_colors = [COLORS["danger"] if "drop" in lb.lower() or "delete" in lb.lower() or "remove" in lb.lower() else COLORS["primary"] for lb in labels]

    fig, ax = plt.subplots(figsize=(8, max(3, len(labels) * 0.6)))
    bars = ax.barh(labels, values, color=bar_colors, alpha=0.85, height=0.6)
    ax.set_xlabel("Cantidad de acciones")
    ax.set_title("Resumen de Acciones de Limpieza", fontsize=14, fontweight="bold", pad=12)
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2, str(val), va="center", fontsize=11, fontweight="bold", color=COLORS["text"])
    ax.invert_yaxis()
    fig.tight_layout()
    return _fig_to_base64(fig)


def quality_score_gauge(score):
    fig, ax = plt.subplots(figsize=(4, 3))
    color = COLORS["success"] if score >= 80 else COLORS["warning"] if score >= 50 else COLORS["danger"]
    ax.barh([0], [score], color=color, height=0.5, alpha=0.85)
    ax.barh([0], [100 - score], left=[score], color=COLORS["muted"], height=0.5, alpha=0.3)
    ax.set_xlim(0, 100)
    ax.set_yticks([])
    ax.set_xlabel("Score")
    ax.set_title(f"Calidad General: {score:.0f}/100", fontsize=14, fontweight="bold", pad=12)
    ax.text(score / 2, 0, f"{score:.0f}%", ha="center", va="center", fontsize=16, fontweight="bold", color=COLORS["bg"])
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
