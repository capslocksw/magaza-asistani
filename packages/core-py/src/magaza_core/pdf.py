"""HTML -> PDF rendering.

Production (Linux containers) uses WeasyPrint. WeasyPrint needs Pango/GObject native libraries that
are usually missing on Windows/macOS dev machines; there we fall back to headless Chromium through
Playwright, which is installed by ``make setup`` anyway. ``PDF_RENDERER=weasyprint|chromium`` forces
one backend. See docs/adr/003-pdf-rendering.md.
"""

from __future__ import annotations

import logging
import os
import sys
from types import TracebackType
from typing import Any, Protocol

log = logging.getLogger(__name__)


class PdfRenderer(Protocol):
    name: str

    def render(self, html: str) -> bytes: ...

    def close(self) -> None: ...


class WeasyPrintRenderer:
    name = "weasyprint"

    def __init__(self) -> None:
        import weasyprint  # noqa: F401  (import errors are handled by get_pdf_renderer)

    def render(self, html: str) -> bytes:
        import weasyprint

        pdf: bytes = weasyprint.HTML(string=html).write_pdf()
        return pdf

    def close(self) -> None:
        return None


class ChromiumRenderer:
    """Re-uses one headless Chromium page for many documents (sync API; call from a worker thread)."""

    name = "chromium"

    def __init__(self) -> None:
        self._pw: Any = None
        self._browser: Any = None

    def _page(self) -> Any:
        if self._browser is None:
            from playwright.sync_api import sync_playwright

            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch()
        return self._browser.new_page()

    def render(self, html: str) -> bytes:
        page = self._page()
        try:
            page.set_content(html, wait_until="load")
            pdf: bytes = page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "16mm", "bottom": "16mm", "left": "14mm", "right": "14mm"},
            )
            return pdf
        finally:
            page.close()

    def close(self) -> None:
        if self._browser is not None:
            self._browser.close()
            self._pw.stop()
            self._browser = None
            self._pw = None


class _Managed:
    def __init__(self, renderer: PdfRenderer) -> None:
        self.renderer = renderer

    def __enter__(self) -> PdfRenderer:
        return self.renderer

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.renderer.close()


def get_pdf_renderer() -> PdfRenderer:
    mode = os.environ.get("PDF_RENDERER", "auto").lower()
    if mode == "auto" and sys.platform == "win32" and not os.environ.get("WEASYPRINT_DLL_DIRECTORIES"):
        # Importing WeasyPrint without GTK prints a long troubleshooting banner; skip it outright.
        mode = "chromium"
    if mode in ("auto", "weasyprint"):
        try:
            return WeasyPrintRenderer()
        except (ImportError, OSError) as exc:
            if mode == "weasyprint":
                raise
            log.info("WeasyPrint unavailable (%s); using headless Chromium for PDFs", type(exc).__name__)
    return ChromiumRenderer()


def pdf_renderer() -> _Managed:
    """Context manager: ``with pdf_renderer() as r: r.render(html)``."""
    return _Managed(get_pdf_renderer())


def html_to_pdf(html: str) -> bytes:
    with pdf_renderer() as renderer:
        return renderer.render(html)


__all__ = [
    "ChromiumRenderer",
    "PdfRenderer",
    "WeasyPrintRenderer",
    "get_pdf_renderer",
    "html_to_pdf",
    "pdf_renderer",
]
