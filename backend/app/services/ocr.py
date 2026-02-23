"""OCR and text extraction service.

Uses PyMuPDF for PDF text extraction and Pillow for image preprocessing.
Falls back to pytesseract OCR when available for scanned/image-based documents.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


def _configure_tesseract() -> None:
    """Set pytesseract binary path from settings or auto-detect for the current platform."""
    import sys

    try:
        import pytesseract
        from app.core.config import settings

        # Use explicitly configured path only if it actually exists on the current OS.
        if settings.TESSERACT_CMD and Path(settings.TESSERACT_CMD).is_file():
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
            logger.info("Tesseract binary configured from settings: %s", settings.TESSERACT_CMD)
            return

        # Auto-detect common installation locations per platform.
        if sys.platform == "win32":
            _candidates = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                str(Path.home() / "AppData" / "Local" / "Programs" / "Tesseract-OCR" / "tesseract.exe"),
            ]
        elif sys.platform == "darwin":
            _candidates = [
                "/opt/homebrew/bin/tesseract",  # Apple Silicon (M1/M2/M3)
                "/usr/local/bin/tesseract",     # Intel Mac (Homebrew)
            ]
        else:
            # Linux (Ubuntu, Debian, etc.)
            _candidates = [
                "/usr/bin/tesseract",
                "/usr/local/bin/tesseract",
            ]

        for candidate in _candidates:
            if Path(candidate).is_file():
                pytesseract.pytesseract.tesseract_cmd = candidate
                logger.info("Tesseract auto-detected at: %s", candidate)
                return

        # Fall back to pytesseract's default PATH lookup.
        logger.debug("Tesseract not explicitly configured; relying on PATH lookup.")
    except Exception:
        # Settings or pytesseract may not be available in test/import contexts — that's fine.
        pass


_configure_tesseract()


@dataclass
class ExtractionResult:
    """Result of text extraction from a single document."""

    text: str
    page_count: int = 0
    char_count: int = 0
    extraction_method: str = "none"
    confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return len(self.text.strip()) == 0


def extract_text_from_pdf(file_path: str | Path) -> ExtractionResult:
    """Extract text from a PDF using PyMuPDF (fitz).

    Works on digital (text-layer) PDFs. For scanned PDFs without a text layer,
    falls back to image-based OCR if Tesseract is available.
    """
    import fitz  # PyMuPDF

    path = Path(file_path)
    if not path.exists():
        return ExtractionResult(
            text="",
            extraction_method="error",
            warnings=[f"File not found: {path}"],
        )

    try:
        doc = fitz.open(str(path))
    except Exception as exc:
        return ExtractionResult(
            text="",
            extraction_method="error",
            warnings=[f"Failed to open PDF: {exc}"],
        )

    pages_text: list[str] = []
    for page in doc:
        page_text = page.get_text("text")
        if page_text.strip():
            pages_text.append(page_text.strip())

    doc.close()

    full_text = "\n\n".join(pages_text)

    if full_text.strip():
        char_count = len(full_text)
        # Heuristic confidence: more text = higher confidence
        confidence = min(1.0, char_count / 200)
        return ExtractionResult(
            text=full_text,
            page_count=len(pages_text),
            char_count=char_count,
            extraction_method="pymupdf_text_layer",
            confidence=round(confidence, 2),
        )

    # PDF has no text layer — try OCR via Tesseract on rendered pages
    return _ocr_pdf_pages(path)


def extract_text_from_image(file_path: str | Path) -> ExtractionResult:
    """Extract text from an image file using Tesseract OCR via Pillow."""
    path = Path(file_path)
    if not path.exists():
        return ExtractionResult(
            text="",
            extraction_method="error",
            warnings=[f"File not found: {path}"],
        )

    try:
        from PIL import Image

        image = Image.open(path)
        # Convert to RGB if needed (e.g. RGBA PNGs)
        if image.mode not in ("L", "RGB"):
            image = image.convert("RGB")
    except Exception as exc:
        return ExtractionResult(
            text="",
            extraction_method="error",
            warnings=[f"Failed to open image: {exc}"],
        )

    return _ocr_image(image)


def extract_text(file_path: str | Path, mime_type: str) -> ExtractionResult:
    """Route extraction to the appropriate handler based on MIME type."""
    if mime_type == "application/pdf":
        return extract_text_from_pdf(file_path)
    if mime_type in {"image/jpeg", "image/png", "image/webp"}:
        return extract_text_from_image(file_path)
    return ExtractionResult(
        text="",
        extraction_method="unsupported",
        warnings=[f"Unsupported MIME type: {mime_type}"],
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ocr_image(image: object) -> ExtractionResult:
    """Run Tesseract OCR on a PIL Image. Gracefully degrades if unavailable."""
    try:
        import pytesseract

        text = pytesseract.image_to_string(image, lang="eng+nor")
        text = text.strip()
        if text:
            confidence = min(1.0, len(text) / 150)
            return ExtractionResult(
                text=text,
                page_count=1,
                char_count=len(text),
                extraction_method="tesseract_ocr",
                confidence=round(confidence, 2),
            )
        return ExtractionResult(
            text="",
            extraction_method="tesseract_ocr",
            confidence=0.0,
            warnings=["Tesseract returned empty text"],
        )
    except Exception as exc:
        logger.warning("Tesseract OCR unavailable: %s", exc)
        return ExtractionResult(
            text="",
            extraction_method="ocr_unavailable",
            confidence=0.0,
            warnings=[
                "Tesseract OCR is not installed. "
                "Install Tesseract to enable image/scanned-PDF extraction."
            ],
        )


def _ocr_pdf_pages(pdf_path: Path) -> ExtractionResult:
    """Render PDF pages to images and OCR each one."""
    import fitz  # PyMuPDF
    from PIL import Image

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as exc:
        return ExtractionResult(
            text="",
            extraction_method="error",
            warnings=[f"Failed to open PDF for OCR: {exc}"],
        )

    all_text: list[str] = []
    warnings: list[str] = []

    for _page_num, page in enumerate(doc):
        # Render page at 300 DPI for OCR quality
        mat = fitz.Matrix(300 / 72, 300 / 72)
        pix = page.get_pixmap(matrix=mat)
        img = Image.open(io.BytesIO(pix.tobytes("png")))

        result = _ocr_image(img)
        if result.text.strip():
            all_text.append(result.text.strip())
        if result.warnings:
            warnings.extend(result.warnings)
        # If Tesseract is unavailable, stop trying more pages
        if result.extraction_method == "ocr_unavailable":
            break

    doc.close()

    full_text = "\n\n".join(all_text)
    method = "tesseract_ocr_pdf" if full_text else "ocr_unavailable"
    confidence = min(1.0, len(full_text) / 200) if full_text else 0.0

    if not full_text and not any("not installed" in w for w in warnings):
        warnings.append("No text could be extracted from scanned PDF")

    return ExtractionResult(
        text=full_text,
        page_count=len(all_text),
        char_count=len(full_text),
        extraction_method=method,
        confidence=round(confidence, 2),
        warnings=warnings,
    )
