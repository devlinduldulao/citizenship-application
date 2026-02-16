"""Tesseract OCR integration tests — verifies image-based text extraction.

These tests create real images with text and run Tesseract OCR on them,
confirming the full pytesseract → tesseract binary pipeline works.

Skip gracefully if Tesseract is not installed (CI without Tesseract, etc.).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.services.ocr import ExtractionResult, extract_text_from_image


def _tesseract_available() -> bool:
    """Check if Tesseract binary is reachable."""
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _tesseract_available(),
    reason="Tesseract OCR binary not available",
)


def _create_text_image(text: str, size: tuple[int, int] = (800, 200)) -> Path:
    """Create a PNG image with black text on white background."""
    img = Image.new("RGB", size, color="white")
    draw = ImageDraw.Draw(img)
    # Use a large built-in font for better OCR accuracy
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except OSError:
        font = ImageFont.load_default(size=28)
    draw.text((20, 40), text, fill="black", font=font)
    path = Path(tempfile.mktemp(suffix=".png"))
    img.save(str(path))
    return path


class TestTesseractImageOCR:
    """Verify Tesseract can extract text from generated images."""

    def test_simple_english_text(self) -> None:
        img_path = _create_text_image("Hello World Citizenship Application")
        try:
            result = extract_text_from_image(img_path)
            assert isinstance(result, ExtractionResult)
            assert result.extraction_method == "tesseract_ocr"
            assert result.confidence > 0
            assert not result.is_empty
            text_lower = result.text.lower()
            assert "hello" in text_lower or "world" in text_lower
        finally:
            img_path.unlink(missing_ok=True)

    def test_passport_style_text(self) -> None:
        img_path = _create_text_image("Passport No: NO1234567\nNationality: Norwegian")
        try:
            result = extract_text_from_image(img_path)
            assert result.extraction_method == "tesseract_ocr"
            assert not result.is_empty
            # Tesseract should pick up at least the passport number pattern
            assert "1234567" in result.text
        finally:
            img_path.unlink(missing_ok=True)

    def test_date_extraction_from_image(self) -> None:
        img_path = _create_text_image("Date of birth: 15.03.1990")
        try:
            result = extract_text_from_image(img_path)
            assert result.extraction_method == "tesseract_ocr"
            assert "1990" in result.text
        finally:
            img_path.unlink(missing_ok=True)

    def test_image_to_nlp_pipeline(self) -> None:
        """Full pipeline: image → OCR → NLP entity extraction."""
        from app.services.nlp import extract_entities

        img_path = _create_text_image(
            "Passport No: NO9876543  Nationality: Somali  Born: 22.08.1992"
        )
        try:
            ocr_result = extract_text_from_image(img_path)
            assert not ocr_result.is_empty

            entities = extract_entities(ocr_result.text)
            # At minimum the date should be picked up
            assert len(entities.dates) >= 1 or len(entities.passport_numbers) >= 1
        finally:
            img_path.unlink(missing_ok=True)

    def test_missing_image_file(self) -> None:
        result = extract_text_from_image("/nonexistent/image.png")
        assert result.extraction_method == "error"
        assert result.is_empty

    def test_scanned_pdf_ocr_fallback(self) -> None:
        """Verify scanned PDF (image-only, no text layer) triggers Tesseract OCR."""
        import fitz  # PyMuPDF

        from app.services.ocr import extract_text_from_pdf

        # Create a PDF that contains only an image (no text layer)
        img_path = _create_text_image("Scanned document test 2026", size=(600, 150))
        try:
            doc = fitz.open()
            page = doc.new_page(width=600, height=150)
            page.insert_image(
                fitz.Rect(0, 0, 600, 150),
                filename=str(img_path),
            )
            pdf_path = Path(tempfile.mktemp(suffix=".pdf"))
            doc.save(str(pdf_path))
            doc.close()

            result = extract_text_from_pdf(pdf_path)
            # Should fall through to Tesseract OCR since there's no text layer
            assert result.extraction_method in (
                "tesseract_ocr_pdf",
                "tesseract_ocr",
            )
            assert not result.is_empty
            # Should extract something recognizable
            assert "2026" in result.text or "scanned" in result.text.lower()
        finally:
            img_path.unlink(missing_ok=True)
            pdf_path.unlink(missing_ok=True)
