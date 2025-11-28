from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from importlib import resources

from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

from src.config import settings
from src.core.errors import NotFoundError
from src.forecasts.models import ForecastJob
from src.forecasts.repository import (
    IForecastJobRepository,
    IForecastSeriesRepository,
    IForecastHouseSeriesRepository,
)


class ForecastReportService:
    def __init__(
        self,
        job_repo: IForecastJobRepository,
        series_repo: IForecastSeriesRepository,
        house_series_repo: IForecastHouseSeriesRepository,
    ):
        self.job_repo = job_repo
        self.series_repo = series_repo
        self.house_series_repo = house_series_repo

    def generate_pdf(self, job_id, user_id: int) -> Path:
        job = self.job_repo.get(job_id)
        if not job or job.user_id != user_id:
            raise NotFoundError("Forecast job not found")

        aggregated_points = self.series_repo.list_points(job_id, limit=10_000)
        if not aggregated_points:
            raise NotFoundError("Forecast series not available")

        house_summaries = self.house_series_repo.list_house_summaries(job_id)
        top_houses = house_summaries[:5]

        output_dir = Path(settings.REPORT_OUTPUT_PATH) / str(job_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = output_dir / "forecast_report.pdf"
        chart_path = output_dir / "forecast_chart.png"
        house_charts: list[tuple[dict, Path]] = []

        self._build_chart(aggregated_points, chart_path, title="Суммарная нагрузка")
        for house in top_houses:
            points = self.house_series_repo.list_points(job_id, house["house_id"], limit=10_000)
            if not points:
                continue
            path = output_dir / f"house_{house['house_id']}.png"
            self._build_chart(points, path, title=f"Дом {house['house_id']}")
            house_charts.append((house, path))

        self._build_pdf(job, aggregated_points, house_summaries, chart_path, house_charts, pdf_path)
        return pdf_path

    @staticmethod
    def _build_chart(points: Sequence, chart_path: Path, title: str) -> None:
        dates = [p.timestamp for p in points]
        values = [p.value for p in points]
        plt.figure(figsize=(8, 3))
        plt.plot(dates, values, color="#1f77b4", linewidth=1.5)
        plt.title(title)
        plt.xlabel("Дата")
        plt.ylabel("Условные единицы")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(chart_path, dpi=150)
        plt.close()

    @staticmethod
    def _build_pdf(
        job: ForecastJob,
        aggregated_points: Sequence,
        house_summaries: list[dict],
        chart_path: Path,
        house_charts: list[tuple[dict, Path]],
        pdf_path: Path,
    ) -> None:
        metrics = job.metrics or {}
        top_houses = house_summaries[:10]

        base_font, bold_font = _ensure_cyrillic_font()

        c = canvas.Canvas(str(pdf_path), pagesize=A4)
        width, height = A4

        c.setFont(bold_font, 14)
        c.drawString(2 * cm, height - 2 * cm, "Отчёт по прогнозу тепловой нагрузки")
        c.setFont(base_font, 10)
        c.drawString(2 * cm, height - 2.8 * cm, f"Job ID: {job.id}")
        if job.created_at:
            c.drawString(2 * cm, height - 3.3 * cm, f"Создан: {job.created_at:%d.%m.%Y %H:%M}")
        c.drawString(2 * cm, height - 3.8 * cm, f"Статус: {job.status}")

        c.setFont(bold_font, 12)
        c.drawString(2 * cm, height - 5 * cm, "Метрики модели")
        c.setFont(base_font, 10)
        y = height - 5.7 * cm
        for key in sorted(metrics.keys()):
            c.drawString(2 * cm, y, f"{key}: {metrics[key]}")
            y -= 0.5 * cm

        c.setFont(bold_font, 12)
        c.drawString(2 * cm, y - 0.5 * cm, "Топ домов по суммарному прогнозу")
        y -= 1.2 * cm
        c.setFont(base_font, 10)
        for house in top_houses:
            c.drawString(
                2 * cm,
                y,
                f"{house['house_id']}: всего {house['total']:.2f}, среднее {house['avg']:.2f}, пик {house['peak']:.2f}",
            )
            y -= 0.5 * cm
            if y < 6 * cm:
                break

        if chart_path.exists():
            c.drawImage(str(chart_path), 2 * cm, 2 * cm, width=16 * cm, height=8 * cm, preserveAspectRatio=True)

        # Графики по домам на отдельных страницах
        for house, h_chart in house_charts:
            c.showPage()
            c.setFont(bold_font, 12)
            c.drawString(2 * cm, height - 2 * cm, f"Дом {house['house_id']}")
            c.setFont(base_font, 10)
            c.drawString(
                2 * cm,
                height - 2.7 * cm,
                f"Суммарно {house['total']:.2f}, среднее {house['avg']:.2f}, пик {house['peak']:.2f}",
            )
            if h_chart.exists():
                c.drawImage(str(h_chart), 2 * cm, height - 12 * cm, width=16 * cm, height=8 * cm, preserveAspectRatio=True)

        c.showPage()
        c.save()


def _ensure_cyrillic_font() -> tuple[str, str]:
    """
    Пытаемся зарегистрировать DejaVuSans/DejaVuSans-Bold (кириллица).
    Если не получилось — возвращаем Helvetica.
    """
    try:
        import matplotlib.font_manager as fm

        def _find_font(name: str, weight: str | None = None) -> Path | None:
            try:
                path = Path(fm.findfont(name, fallback_to_default=False, weight=weight))
                return path if path.exists() else None
            except Exception:  # noqa: BLE001
                return None

        regular = _find_font("DejaVu Sans")
        bold = _find_font("DejaVu Sans", weight="bold")

        # fallback: взять из mpl-data
        if not regular:
            try:
                with resources.path("matplotlib", "mpl-data/fonts/ttf/DejaVuSans.ttf") as p:
                    regular = Path(p)
            except Exception:  # noqa: BLE001
                regular = None
        if not bold:
            try:
                with resources.path("matplotlib", "mpl-data/fonts/ttf/DejaVuSans-Bold.ttf") as p:
                    bold = Path(p)
            except Exception:  # noqa: BLE001
                bold = None

        if regular:
            pdfmetrics.registerFont(TTFont("DejaVuSans", str(regular)))
        if bold:
            pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", str(bold)))
        if regular or bold:
            pdfmetrics.registerFontFamily(
                "DejaVuSans",
                normal="DejaVuSans",
                bold="DejaVuSans-Bold" if bold else "DejaVuSans",
                italic="DejaVuSans",
                boldItalic="DejaVuSans-Bold" if bold else "DejaVuSans",
            )
            return "DejaVuSans", "DejaVuSans-Bold" if bold else "DejaVuSans"
    except Exception:  # noqa: BLE001
        pass

    return "Helvetica", "Helvetica-Bold"
