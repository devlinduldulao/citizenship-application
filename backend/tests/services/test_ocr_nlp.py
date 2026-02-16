"""Unit tests for OCR and NLP extraction services."""

import tempfile
from pathlib import Path

from app.services.nlp import (
    ExtractedEntities,
    compute_document_nlp_score,
    extract_entities,
)
from app.services.ocr import ExtractionResult, extract_text, extract_text_from_pdf


def _create_temp_pdf_with_text(text: str) -> Path:
    """Create a minimal PDF with text content using PyMuPDF."""
    import fitz

    path = Path(tempfile.mktemp(suffix=".pdf"))
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=12)
    doc.save(str(path))
    doc.close()
    return path


class TestOCRExtraction:
    def test_pdf_text_extraction(self) -> None:
        text = "Name: John Doe\nPassport: AB1234567\nDate: 15.03.1990"
        pdf_path = _create_temp_pdf_with_text(text)
        try:
            result = extract_text_from_pdf(pdf_path)
            assert isinstance(result, ExtractionResult)
            assert result.extraction_method == "pymupdf_text_layer"
            assert result.char_count > 0
            assert not result.is_empty
            assert "John Doe" in result.text
            assert "AB1234567" in result.text
        finally:
            pdf_path.unlink(missing_ok=True)

    def test_missing_file_returns_error(self) -> None:
        result = extract_text_from_pdf("/nonexistent/file.pdf")
        assert result.extraction_method == "error"
        assert result.is_empty

    def test_extract_text_routing_pdf(self) -> None:
        text = "Test document content"
        pdf_path = _create_temp_pdf_with_text(text)
        try:
            result = extract_text(pdf_path, "application/pdf")
            assert result.extraction_method == "pymupdf_text_layer"
            assert "Test document" in result.text
        finally:
            pdf_path.unlink(missing_ok=True)

    def test_extract_text_unsupported_mime(self) -> None:
        result = extract_text("/some/file.txt", "text/plain")
        assert result.extraction_method == "unsupported"


class TestNLPExtraction:
    def test_date_extraction(self) -> None:
        text = "Born on 15.03.1990. Passport issued 2020-01-15."
        entities = extract_entities(text)
        assert len(entities.dates) >= 2

    def test_passport_number_extraction(self) -> None:
        text = "Passport number: AB1234567"
        entities = extract_entities(text)
        assert "AB1234567" in entities.passport_numbers

    def test_nationality_extraction(self) -> None:
        text = "The applicant is of Pakistani nationality."
        entities = extract_entities(text)
        assert any("pakistani" in n.lower() for n in entities.nationalities)

    def test_citizenship_keywords(self) -> None:
        text = "Application for citizenship and permanent residence in Norway."
        entities = extract_entities(text)
        assert "citizenship" in entities.keywords_found
        assert "permanent residence" in entities.keywords_found

    def test_language_indicators(self) -> None:
        text = "Norskprøve B1 bestått. Samfunnskunnskap passed."
        entities = extract_entities(text)
        assert len(entities.language_indicators) >= 2

    def test_residency_indicators(self) -> None:
        text = "7 years of residence in Norway. Folkeregistrert address confirmed."
        entities = extract_entities(text)
        assert len(entities.residency_indicators) >= 1

    def test_name_extraction(self) -> None:
        text = "Full name: Ahmed Hassan\nSurname: Hassan"
        entities = extract_entities(text)
        assert any("Ahmed Hassan" in n for n in entities.names)

    def test_norwegian_dates(self) -> None:
        text = "Født 15 mars 2000. Innvilget 3 januar 2020."
        entities = extract_entities(text)
        assert len(entities.dates) >= 2

    def test_empty_text(self) -> None:
        entities = extract_entities("")
        assert entities.raw_entity_count == 0

    def test_entity_count(self) -> None:
        text = (
            "Name: Omar Ali\n"
            "Passport: NO9876543\n"
            "Born: 01.06.1985\n"
            "Nationality: Somali\n"
            "Norskprøve B2 bestått\n"
            "7 years in Norway\n"
            "Application for citizenship\n"
        )
        entities = extract_entities(text)
        assert entities.raw_entity_count >= 5

    def test_nlp_score_computation(self) -> None:
        entities = ExtractedEntities(
            dates=["01.01.1990", "15.03.2020"],
            passport_numbers=["AB1234567"],
            names=["John Doe"],
            nationalities=["Pakistani"],
            keywords_found=["citizenship", "passport", "application"],
            language_indicators=["B1", "norskprøve"],
            residency_indicators=["years of residence"],
        )
        score = compute_document_nlp_score(entities)
        assert 0.0 < score <= 1.0

    def test_nlp_score_empty(self) -> None:
        score = compute_document_nlp_score(ExtractedEntities())
        assert score == 0.0


class TestEndToEndOCRNLP:
    """Integration: PDF -> OCR -> NLP pipeline."""

    def test_pdf_to_entities(self) -> None:
        text = (
            "KINGDOM OF NORWAY\n"
            "PASSPORT\n"
            "Surname: NGUYEN\n"
            "Given name: Thi Lan\n"
            "Nationality: Norwegian\n"
            "Date of birth: 22.08.1992\n"
            "Passport No: NO8765432\n"
            "Date of issue: 2023-05-10\n"
            "Valid until: 2033-05-10\n"
        )
        pdf_path = _create_temp_pdf_with_text(text)
        try:
            ocr_result = extract_text_from_pdf(pdf_path)
            assert not ocr_result.is_empty

            entities = extract_entities(ocr_result.text)
            assert len(entities.dates) >= 2
            assert len(entities.passport_numbers) >= 1
            assert any("norwegian" in n.lower() for n in entities.nationalities)
            assert any("NGUYEN" in n or "Thi Lan" in n for n in entities.names)
            assert "passport" in entities.keywords_found

            score = compute_document_nlp_score(entities)
            assert score > 0.3
        finally:
            pdf_path.unlink(missing_ok=True)
