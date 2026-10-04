"""HTML to PDF conversion through wkhtmltopdf (via pdfkit)."""

from __future__ import annotations

from pathlib import Path


class PdfError(RuntimeError):
    pass


def write_pdf(html: str, output_path: Path, wkhtmltopdf_path: str | None = None) -> Path:
    import pdfkit

    try:
        configuration = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path or "")
    except OSError as exc:
        raise PdfError(
            "wkhtmltopdf was not found. Install it or set WKHTMLTOPDF_PATH, or run with --no-pdf."
        ) from exc

    options = {"encoding": "UTF-8", "page-size": "A4", "quiet": ""}
    pdfkit.from_string(html, str(output_path), configuration=configuration, options=options)
    return output_path
