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

    def test_pdf_expired_passport_expiry_date_extracted(self) -> None:
        """End-to-end: expiry date labeled in a PDF must land in expiry_dates."""
        text = (
            "PASSPORT\n"
            "Surname: DOE\n"
            "Date of birth: 15.03.1985\n"
            "Date of issue: 10.05.2015\n"
            "Expiry date: 10.05.2025\n"
        )
        pdf_path = _create_temp_pdf_with_text(text)
        try:
            ocr_result = extract_text_from_pdf(pdf_path)
            entities = extract_entities(ocr_result.text)
            assert "10.05.2025" in entities.expiry_dates
            # Birth date must NOT be misclassified as expiry
            assert "15.03.1985" not in entities.expiry_dates
        finally:
            pdf_path.unlink(missing_ok=True)


class TestExpiryDateExtraction:
    """Unit tests for expiry-date context pattern extraction in nlp.extract_entities."""

    def test_english_expiry_date_extracted(self) -> None:
        entities = extract_entities("Expiry date: 31.12.2028\nDate of birth: 01.01.1990")
        assert "31.12.2028" in entities.expiry_dates

    def test_valid_until_extracted(self) -> None:
        entities = extract_entities("Valid until: 2030-06-15")
        assert "2030-06-15" in entities.expiry_dates

    def test_expires_on_extracted(self) -> None:
        entities = extract_entities("This permit expires 01/09/2027.")
        assert "01/09/2027" in entities.expiry_dates

    def test_date_of_expiry_label(self) -> None:
        entities = extract_entities("Date of expiry: 15-08-2029")
        assert "15-08-2029" in entities.expiry_dates

    def test_expiration_date_label(self) -> None:
        entities = extract_entities("Expiration date: 2031-12-01")
        assert "2031-12-01" in entities.expiry_dates

    def test_norwegian_utloepsdato_extracted(self) -> None:
        entities = extract_entities("Utl\u00f8psdato: 15.08.2026")
        assert "15.08.2026" in entities.expiry_dates

    def test_norwegian_gyldig_til_extracted(self) -> None:
        entities = extract_entities("Gyldig til: 01.03.2027")
        assert "01.03.2027" in entities.expiry_dates

    def test_norwegian_gyldig_frem_til_extracted(self) -> None:
        entities = extract_entities("Gyldig frem til: 20.11.2025")
        assert "20.11.2025" in entities.expiry_dates

    def test_textual_month_expiry_extracted(self) -> None:
        entities = extract_entities("Expiry date: 04 JUL 2019")
        assert "04 JUL 2019" in entities.expiry_dates

    def test_textual_month_bilingual_expiry_extracted(self) -> None:
        entities = extract_entities("Valid until: 04 JUL / JUIL 2019")
        assert "04 JUL / JUIL 2019" in entities.expiry_dates

    def test_underscore_date_expiry_extracted(self) -> None:
        entities = extract_entities("Gyldig til: 2019_07_04")
        assert "2019_07_04" in entities.expiry_dates

    def test_birth_date_not_classified_as_expiry(self) -> None:
        entities = extract_entities("Date of birth: 15.03.1990\nName: John Doe")
        assert "15.03.1990" not in entities.expiry_dates

    def test_issue_date_not_classified_as_expiry(self) -> None:
        entities = extract_entities("Date of issue: 10.05.2020")
        assert "10.05.2020" not in entities.expiry_dates

    def test_expiry_dates_present_in_to_dict(self) -> None:
        entities = extract_entities("Expires 31.12.2025")
        d = entities.to_dict()
        assert "expiry_dates" in d

    def test_multiple_expiry_dates_deduplicated(self) -> None:
        entities = extract_entities("Expiry date: 31.12.2025\nExpiry date: 31.12.2025")
        assert entities.expiry_dates.count("31.12.2025") == 1

    def test_no_expiry_label_no_expiry_dates(self) -> None:
        entities = extract_entities("Born 01.01.1990. Issued 15.04.2020.")
        assert entities.expiry_dates == []

    def test_expiry_dates_contribute_to_raw_entity_count(self) -> None:
        entities_no_expiry = extract_entities("Name: Ali Hassan")
        entities_with_expiry = extract_entities("Name: Ali Hassan\nExpiry date: 31.12.2030")
        assert entities_with_expiry.raw_entity_count > entities_no_expiry.raw_entity_count

    def test_bilingual_label_newline_gap(self) -> None:
        text = "Date of expiry / Date d\u2019expiration\n04 JUL 2029\n"
        entities = extract_entities(text)
        assert len(entities.expiry_dates) > 0

    def test_bilingual_label_with_date_dexpiration(self) -> None:
        entities = extract_entities("Date d'expiration\n15.08.2029")
        assert len(entities.expiry_dates) > 0

    def test_french_label_standalone(self) -> None:
        entities = extract_entities("Date d'expiration: 04.07.2019")
        assert "04.07.2019" in entities.expiry_dates

    def test_norwegian_label_newline_gap(self) -> None:
        entities = extract_entities("Utl\u00f8psdato\n04.07.2019")
        assert "04.07.2019" in entities.expiry_dates

    def test_mrz_expiry_extraction(self) -> None:
        text = (
            "P<NORHASSAN<<AHMED<<<<<<<<<<<<<<<<<<<<<<<<<<\n"
            "NO1234567<0NOR9003155M2907047<<<<<<<<<<<<<<00\n"
        )
        entities = extract_entities(text)
        assert "290704" in entities.expiry_dates

    def test_mrz_only_passport_has_expiry(self) -> None:
        text = (
            "KINGDOM OF NORWAY\nPASSPORT\n"
            "P<NORHASSAN<<AHMED<<<<<<<<<<<<<<<<<<<<<<<<<<\n"
            "NO1234567<0NOR9003155M2907047<<<<<<<<<<<<<<00\n"
        )
        entities = extract_entities(text)
        assert len(entities.expiry_dates) > 0

    def test_both_label_and_mrz_expiry(self) -> None:
        text = (
            "Date of expiry: 04.07.2029\n"
            "P<NORHASSAN<<AHMED<<<<<<<<<<<<<<<<<<<<<<<<<<\n"
            "NO1234567<0NOR9003155M2907047<<<<<<<<<<<<<<00\n"
        )
        entities = extract_entities(text)
        assert len(entities.expiry_dates) >= 1


class TestParseDateFlexible:
    """Unit tests for the parse_date_flexible utility."""

    def test_dd_mm_yyyy_dot(self) -> None:
        from datetime import date

        from app.services.nlp import parse_date_flexible

        assert parse_date_flexible("31.12.2025") == date(2025, 12, 31)

    def test_yyyy_mm_dd_iso(self) -> None:
        from datetime import date

        from app.services.nlp import parse_date_flexible

        assert parse_date_flexible("2025-12-31") == date(2025, 12, 31)

    def test_dd_slash_mm_slash_yyyy(self) -> None:
        from datetime import date

        from app.services.nlp import parse_date_flexible

        assert parse_date_flexible("31/12/2025") == date(2025, 12, 31)

    def test_dd_dash_mm_dash_yyyy(self) -> None:
        from datetime import date

        from app.services.nlp import parse_date_flexible

        assert parse_date_flexible("31-12-2025") == date(2025, 12, 31)

    def test_yyyy_dot_mm_dot_dd(self) -> None:
        from datetime import date

        from app.services.nlp import parse_date_flexible

        assert parse_date_flexible("2025.12.31") == date(2025, 12, 31)

    def test_two_digit_year(self) -> None:
        from app.services.nlp import parse_date_flexible

        result = parse_date_flexible("31.12.25")
        assert result is not None
        assert result.month == 12
        assert result.day == 31

    def test_invalid_returns_none(self) -> None:
        from app.services.nlp import parse_date_flexible

        assert parse_date_flexible("not-a-date") is None

    def test_empty_string_returns_none(self) -> None:
        from app.services.nlp import parse_date_flexible

        assert parse_date_flexible("") is None

    def test_whitespace_stripped(self) -> None:
        from datetime import date

        from app.services.nlp import parse_date_flexible

        assert parse_date_flexible("  31.12.2025  ") == date(2025, 12, 31)

    def test_textual_month_parsing(self) -> None:
        from datetime import date

        from app.services.nlp import parse_date_flexible

        assert parse_date_flexible("04 JUL 2019") == date(2019, 7, 4)

    def test_textual_month_bilingual_parsing(self) -> None:
        from datetime import date

        from app.services.nlp import parse_date_flexible

        assert parse_date_flexible("04 JUL / JUIL 2019") == date(2019, 7, 4)

    def test_underscore_separated_parsing(self) -> None:
        from datetime import date

        from app.services.nlp import parse_date_flexible

        assert parse_date_flexible("2019_07_04") == date(2019, 7, 4)

    def test_mrz_yymmdd_parsing(self) -> None:
        from app.services.nlp import parse_date_flexible

        parsed = parse_date_flexible("190704")
        assert parsed is not None
        assert parsed.month == 7
        assert parsed.day == 4
