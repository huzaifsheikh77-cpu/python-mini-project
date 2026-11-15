"""Payroll charts.

The web application renders every chart **in memory** and streams it as a PNG
response, so nothing is written to disk (required for Vercel's read-only
filesystem). ``generate_charts()`` still writes PNG files for the console
version and for offline use, and is never called by a web request.
"""

import threading
from io import BytesIO
from pathlib import Path

import matplotlib

# A non-interactive backend is required so charts can be rendered by the
# Flask server (and in tests) without opening a GUI window.
matplotlib.use("Agg")

from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

from analytics.salary_analysis import SalaryAnalysis

from storage.backend import get_store


BASE_DIR = Path(__file__).resolve().parent.parent
CHART_DIR = BASE_DIR / "charts"

CHART_FILES = {
    "comparison": "salary_comparison.png",
    "department": "department_payroll.png",
    "distribution": "salary_distribution.png",
}

FIGURE_SIZES = {
    "comparison": (10, 6),
    "department": (8, 8),
    "distribution": (10, 6),
}

CHART_DPI = 130

# Only one request at a time writes the PNG files (CLI path).
_LOCK = threading.Lock()

# Rendered PNGs for the current data signature only.
_MEMORY_CACHE = {}
_CACHE_LOCK = threading.Lock()


class ChartUnavailable(RuntimeError):
    """Raised when there is no payroll data to draw."""


# ==============================
# CHART STYLING (visual only)
# ==============================

NAVY = "#142c59"
ROYAL = "#2563eb"
ACCENT = "#3b82f6"
INK = "#172554"
MUTED = "#64748b"
GRID = "#dce4ef"

# Navy to light blue, plus a slate tone for extra departments.
SERIES_COLOURS = [
    "#142c59",
    "#2563eb",
    "#3b82f6",
    "#64748b",
    "#93c5fd",
    "#1e40af",
    "#cbd5e1",
]

# 1x1 transparent PNG, the last-resort placeholder.
_FALLBACK_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
    b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05"
    b"\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _style_axes(axis):
    """Apply the shared look: light grid, muted ticks, no top/right border."""

    axis.set_axisbelow(True)
    axis.grid(axis="y", color=GRID, linewidth=1)
    axis.grid(axis="x", visible=False)

    for side in ("top", "right"):
        axis.spines[side].set_visible(False)

    axis.spines["left"].set_color(GRID)
    axis.spines["bottom"].set_color(GRID)

    axis.tick_params(colors=MUTED, labelsize=9, length=0)


def _draw_comparison(figure, df):
    axis = figure.add_subplot(111)
    axis.set_facecolor("white")

    bars = axis.bar(
        df["name"],
        df["net_salary"],
        color=ROYAL,
        width=0.55,
        edgecolor=ROYAL,
        linewidth=0
    )

    for bar in bars:
        axis.annotate(
            f"{bar.get_height():,.0f}",
            xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
            color=MUTED
        )

    axis.set_title("Employee Net Salary Comparison", color=INK, fontsize=13,
                   fontweight="bold", pad=16)
    axis.set_xlabel("Employee", color=MUTED, fontsize=9.5, labelpad=10)
    axis.set_ylabel("Net Salary (Rs.)", color=MUTED, fontsize=9.5, labelpad=10)

    _style_axes(axis)
    axis.margins(y=0.12)

    for label in axis.get_xticklabels():
        label.set_rotation(35)
        label.set_ha("right")


def _draw_department(figure, df):
    department_data = df.groupby("department")["net_salary"].sum()
    colours = SERIES_COLOURS[:max(len(department_data), 1)]

    axis = figure.add_subplot(111)

    wedges, texts, percentages = axis.pie(
        department_data,
        labels=department_data.index,
        colors=colours,
        autopct="%1.1f%%",
        startangle=90,
        counterclock=False,
        pctdistance=0.78,
        wedgeprops={"edgecolor": "white", "linewidth": 2},
        textprops={"color": INK, "fontsize": 9.5}
    )

    for percentage in percentages:
        percentage.set_color("white")
        percentage.set_fontsize(9)
        percentage.set_fontweight("bold")

    axis.set_title("Department-wise Payroll Distribution", color=INK,
                   fontsize=13, fontweight="bold", pad=18)


def _draw_distribution(figure, df):
    axis = figure.add_subplot(111)
    axis.set_facecolor("white")

    axis.hist(
        df["net_salary"],
        bins=5,
        color=ACCENT,
        edgecolor="white",
        linewidth=1.6
    )

    axis.set_title("Employee Salary Distribution", color=INK, fontsize=13,
                   fontweight="bold", pad=16)
    axis.set_xlabel("Net Salary (Rs.)", color=MUTED, fontsize=9.5, labelpad=10)
    axis.set_ylabel("Number of Records", color=MUTED, fontsize=9.5, labelpad=10)

    _style_axes(axis)


DRAWERS = {
    "comparison": _draw_comparison,
    "department": _draw_department,
    "distribution": _draw_distribution,
}


# ==============================
# RENDERING
# ==============================

def render_png(key, df):
    """Render one chart and return the PNG bytes."""

    if key not in DRAWERS:
        raise ValueError(f"Unknown chart: {key}")

    figure = Figure(figsize=FIGURE_SIZES[key], facecolor="white")
    FigureCanvasAgg(figure)

    DRAWERS[key](figure, df)

    figure.tight_layout()

    buffer = BytesIO()
    figure.savefig(buffer, format="png", dpi=CHART_DPI, facecolor="white")

    return buffer.getvalue()


def placeholder_png(message="Chart unavailable"):
    """Small PNG used when a chart cannot be drawn, so the page stays intact."""

    try:
        from PIL import Image, ImageDraw

        image = Image.new("RGB", (800, 500), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle([0, 0, 799, 499], outline="#dce4ef", width=2)
        draw.text((24, 24), "Employee Payroll Management System", fill="#172554")
        draw.text((24, 52), message, fill="#64748b")

        buffer = BytesIO()
        image.save(buffer, format="PNG")

        return buffer.getvalue()

    except Exception:
        return _FALLBACK_PNG


class PayrollCharts:

    #: Chart key -> PNG filename (the URL the templates link to).
    CHART_FILES = CHART_FILES

    #: Rendered placeholder used when a chart cannot be drawn.
    placeholder_png = staticmethod(placeholder_png)

    # --------------------------
    # WEB (in memory, no files)
    # --------------------------

    @staticmethod
    def key_for_filename(filename):
        for key, name in CHART_FILES.items():
            if name == filename:
                return key

        return None

    @staticmethod
    def chart_png(key, signature=""):
        """PNG bytes for one chart, cached per data signature."""

        entry = _MEMORY_CACHE.get(key)

        if entry is not None and entry[0] == signature:
            return entry[1]

        df = SalaryAnalysis.load_data()

        if df is None:
            raise ChartUnavailable("No payroll records available")

        data = render_png(key, df)

        with _CACHE_LOCK:
            _MEMORY_CACHE[key] = (signature, data)

        return data

    @staticmethod
    def clear_cache():
        with _CACHE_LOCK:
            _MEMORY_CACHE.clear()

    # --------------------------
    # FILE OUTPUT (CLI / offline)
    # --------------------------

    @staticmethod
    def chart_paths():
        return {
            key: CHART_DIR / name
            for key, name in CHART_FILES.items()
        }

    @staticmethod
    def signature_path():
        return CHART_DIR / ".data-signature"

    @staticmethod
    def is_stale():
        """True when a chart file is missing or the stored data changed."""

        paths = PayrollCharts.chart_paths()

        if any(not path.exists() for path in paths.values()):
            return True

        try:
            current = get_store().data_signature()
            previous = PayrollCharts.signature_path().read_text(encoding="utf-8").strip()
        except Exception:
            return True

        return current != previous

    @staticmethod
    def ensure_charts(force=False):
        """Generate the chart files if needed and return their paths."""

        with _LOCK:
            if force or PayrollCharts.is_stale():
                PayrollCharts.generate_charts()

            return PayrollCharts.chart_paths()

    @staticmethod
    def generate_charts():
        """Write the three payroll charts into the charts folder."""

        df = SalaryAnalysis.load_data()

        if df is None:
            return False

        CHART_DIR.mkdir(parents=True, exist_ok=True)

        for key, name in CHART_FILES.items():
            (CHART_DIR / name).write_bytes(render_png(key, df))

        try:
            PayrollCharts.signature_path().write_text(
                get_store().data_signature(), encoding="utf-8"
            )
        except Exception:
            pass

        print("\nThree payroll charts generated successfully!")

        return True
