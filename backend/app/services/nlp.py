"""NLP entity extraction service.

Uses regex-based pattern matching to extract structured entities from
OCR-extracted text. Targets citizenship-relevant fields: dates, document
numbers, names, nationalities, and Norwegian-specific keywords.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from functools import lru_cache

try:
    import spacy
except Exception:  # pragma: no cover - optional runtime dependency safety
    spacy = None  # type: ignore[assignment]


@dataclass
class ExtractedEntities:
    """Structured entities found in document text."""

    dates: list[str] = field(default_factory=list)
    passport_numbers: list[str] = field(default_factory=list)
    names: list[str] = field(default_factory=list)
    nationalities: list[str] = field(default_factory=list)
    addresses: list[str] = field(default_factory=list)
    keywords_found: list[str] = field(default_factory=list)
    language_indicators: list[str] = field(default_factory=list)
    residency_indicators: list[str] = field(default_factory=list)
    numeric_values: list[str] = field(default_factory=list)
    # Dates that appear immediately after an expiry/validity label in the document.
    # Only populated when a label like "Expiry date:", "Gyldig til:", "Valid until:" is present.
    expiry_dates: list[str] = field(default_factory=list)
    raw_entity_count: int = 0

    def to_dict(self) -> dict[str, list[str] | int]:
        return {
            "dates": self.dates,
            "passport_numbers": self.passport_numbers,
            "names": self.names,
            "nationalities": self.nationalities,
            "addresses": self.addresses,
            "keywords_found": self.keywords_found,
            "language_indicators": self.language_indicators,
            "residency_indicators": self.residency_indicators,
            "numeric_values": self.numeric_values,
            "expiry_dates": self.expiry_dates,
            "raw_entity_count": self.raw_entity_count,
        }


# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

# Dates: DD.MM.YYYY, DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD
_DATE_PATTERNS = [
    r"\b(\d{1,2}[./\-]\d{1,2}[./\-]\d{4})\b",
    r"\b(\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2})\b",
    r"\b(\d{1,2}\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"\s+\d{4})\b",
    # Norwegian month names
    r"\b(\d{1,2}\s+(?:januar|februar|mars|april|mai|juni|"
    r"juli|august|september|oktober|november|desember)\s+\d{4})\b",
]

# Passport / ID numbers: letter(s) + digits, common formats
_PASSPORT_PATTERNS = [
    r"\b([A-Z]{1,3}\d{6,9})\b",  # e.g. AB1234567
    r"\b(\d{9})\b",  # 9-digit number (common passport format)
    r"\b(\d{2}\s?\d{2}\s?\d{2}\s?\d{5})\b",  # Norwegian fødselsnummer DD MM YY NNNNN
]

# Norwegian nationalities and common origins
_NATIONALITIES = [
    "norwegian", "norsk", "swedish", "svensk", "danish", "dansk",
    "finnish", "finsk", "icelandic", "islandsk",
    "german", "tysk", "french", "fransk", "british", "britisk",
    "american", "amerikansk", "polish", "polsk", "lithuanian", "litauisk",
    "somali", "somalisk", "eritrean", "eritreisk", "syrian", "syrisk",
    "iraqi", "irakisk", "afghan", "afghansk", "iranian", "iransk",
    "pakistani", "pakistansk", "indian", "indisk", "philippine", "filippinsk",
    "thai", "thailandsk", "russian", "russisk", "ukrainian", "ukrainsk",
    "turkish", "tyrkisk", "ethiopian", "etiopisk", "colombian", "colombiansk",
    "stateless", "statsløs",
]

# Citizenship / immigration keywords (Norwegian + English)
_CITIZENSHIP_KEYWORDS = [
    # English
    "citizenship", "nationality", "naturalization", "permanent residence",
    "residence permit", "work permit", "visa", "refugee", "asylum",
    "police clearance", "criminal record", "background check",
    "integration", "language test", "social studies",
    "fee", "application", "applicant", "passport", "identity",
    "birth certificate", "marriage certificate", "divorce",
    # Norwegian
    "statsborgerskap", "nasjonalitet", "innvilgelse", "søknad",
    "oppholdstillatelse", "permanent opphold", "arbeidstillatelse",
    "visum", "flyktning", "asyl", "politiattest", "vandelsattest",
    "integrering", "norskprøve", "samfunnskunnskap",
    "gebyr", "søker", "pass", "identitet",
    "fødselsattest", "vigselsattest", "skilsmisse",
    "utlendingsdirektoratet", "udi", "politi",
    "bosettingstillatelse", "midlertidig", "fornyelse",
]

# Language proficiency indicators
_LANGUAGE_INDICATORS = [
    "norskprøve", "norwegian test", "language certificate",
    "muntlig", "skriftlig", "oral", "written",
    "a1", "a2", "b1", "b2", "c1", "c2",
    "bestått", "passed", "godkjent", "approved",
    "samfunnskunnskap", "social studies", "civic integration",
    "norskkurs", "norwegian course", "language course",
    "kompetanse norge", "folkeuniversitetet",
]

# Expiry date context patterns.
# These match a date that immediately follows a label indicating document expiry or
# validity end date, in both English and Norwegian. Using contextual patterns (label +
# date) avoids misidentifying birth dates or issue dates as expiry dates.
_EXPIRY_CONTEXT_PATTERNS = [
    # English: "expiry date", "date of expiry", "expires", "valid until/through/to"
    r"(?:date\s+of\s+expir(?:y|ation)|expir(?:y|ation)\s+date|expir(?:es?|ed?)"
    r"|valid\s+(?:until|through|to|till|thru)|validity\s+period\s+ends?)"
    r"\s*[:\-]?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
    r"(?:date\s+of\s+expir(?:y|ation)|expir(?:y|ation)\s+date|expir(?:es?|ed?)"
    r"|valid\s+(?:until|through|to|till|thru)|validity\s+period\s+ends?)"
    r"\s*[:\-]?\s*(\d{4}[./\-]\d{1,2}[./\-]\d{1,2})",
    # Norwegian: "gyldig til", "utløpsdato", "utløper", "gyldig frem til"
    r"(?:gyldig\s+til|utløpsdato|utl(?:ø|o)psdato|utl(?:ø|o)per"
    r"|gyldig\s+frem\s+til|sist\s+gyldig|gyldighet\s+til)"
    r"\s*[:\-]?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
    r"(?:gyldig\s+til|utløpsdato|utl(?:ø|o)psdato|utl(?:ø|o)per"
    r"|gyldig\s+frem\s+til|sist\s+gyldig|gyldighet\s+til)"
    r"\s*[:\-]?\s*(\d{4}[./\-]\d{1,2}[./\-]\d{1,2})",
    # Textual month formats often found in IDs (e.g. "04 JUL 2019", "04 july 2019")
    r"(?:date\s+of\s+expir(?:y|ation)|expir(?:y|ation)\s+date|expir(?:es?|ed?)"
    r"|valid\s+(?:until|through|to|till|thru)|validity\s+period\s+ends?)"
    r"\s*[:\-]?\s*(\d{1,2}(?:[./_\-]|\s)+[A-Za-zÆØÅæøå]{3,10}(?:\s*/\s*[A-Za-zÆØÅæøå]{3,10})?(?:[./_\-]|\s)+\d{2,4})",
    r"(?:gyldig\s+til|utløpsdato|utl(?:ø|o)psdato|utl(?:ø|o)per"
    r"|gyldig\s+frem\s+til|sist\s+gyldig|gyldighet\s+til)"
    r"\s*[:\-]?\s*(\d{1,2}(?:[./_\-]|\s)+[A-Za-zÆØÅæøå]{3,10}(?:\s*/\s*[A-Za-zÆØÅæøå]{3,10})?(?:[./_\-]|\s)+\d{2,4})",
    # Underscore-separated OCR strings (e.g. "2019_07_04")
    r"(?:date\s+of\s+expir(?:y|ation)|expir(?:y|ation)\s+date|expir(?:es?|ed?)"
    r"|valid\s+(?:until|through|to|till|thru)|validity\s+period\s+ends?)"
    r"\s*[:\-]?\s*(\d{4}[._\-/]\d{1,2}[._\-/]\d{1,2})",
    r"(?:gyldig\s+til|utløpsdato|utl(?:ø|o)psdato|utl(?:ø|o)per"
    r"|gyldig\s+frem\s+til|sist\s+gyldig|gyldighet\s+til)"
    r"\s*[:\-]?\s*(\d{4}[._\-/]\d{1,2}[._\-/]\d{1,2})",
]

# Residency / duration indicators
_RESIDENCY_INDICATORS = [
    "years of residence", "years in norway", "år i norge", "botid",
    "permanent residence", "permanent opphold", "settled status",
    "continuous residence", "sammenhengende opphold",
    "registered address", "folkeregistrert",
    "d-number", "d-nummer", "national id", "fødselsnummer",
    r"\b\d+\s+(?:years?|år)\b",  # "7 years", "3 år"
]

# Address-like patterns (Norwegian postal format)
_ADDRESS_PATTERNS = [
    r"\b(\d{4})\s+([A-ZÆØÅ][a-zæøå]+(?:\s+[A-ZÆØÅ][a-zæøå]+)*)\b",  # 0001 Oslo
    r"\b([A-ZÆØÅ][a-zæøå]+(?:gata|gaten|veien|vegen|gate|vei|veg))\s+\d+",  # Storgata 12
]


@lru_cache(maxsize=1)
def _load_spacy_model() -> object | None:
    """Load spaCy model once; return None if unavailable.

    Priority:
    1) Norwegian model `nb_core_news_sm`
    2) Multilingual model `xx_ent_wiki_sm`
    """
    if spacy is None:
        return None

    for model_name in ("nb_core_news_sm", "xx_ent_wiki_sm"):
        try:
            return spacy.load(model_name)
        except Exception:
            continue

    return None


def extract_entities(text: str) -> ExtractedEntities:
    """Extract structured entities from document text using regex NLP."""
    if not text or not text.strip():
        return ExtractedEntities()

    entities = ExtractedEntities()
    text_lower = text.lower()

    # Dates
    for pattern in _DATE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        entities.dates.extend(matches)
    entities.dates = _dedupe(entities.dates)

    # Passport / ID numbers
    for pattern in _PASSPORT_PATTERNS:
        matches = re.findall(pattern, text)
        entities.passport_numbers.extend(matches)
    entities.passport_numbers = _dedupe(entities.passport_numbers)

    # Nationalities
    for nationality in _NATIONALITIES:
        if nationality.lower() in text_lower:
            entities.nationalities.append(nationality)
    entities.nationalities = _dedupe(entities.nationalities)

    # Citizenship keywords
    for keyword in _CITIZENSHIP_KEYWORDS:
        if keyword.lower() in text_lower:
            entities.keywords_found.append(keyword)
    entities.keywords_found = _dedupe(entities.keywords_found)

    # Language indicators
    for indicator in _LANGUAGE_INDICATORS:
        if indicator.lower() in text_lower:
            entities.language_indicators.append(indicator)
    entities.language_indicators = _dedupe(entities.language_indicators)

    # Residency indicators (mixed regex + literal)
    for indicator in _RESIDENCY_INDICATORS:
        if indicator.startswith(r"\b"):
            # It's a regex pattern
            if re.search(indicator, text, re.IGNORECASE):
                match = re.search(indicator, text, re.IGNORECASE)
                if match:
                    entities.residency_indicators.append(match.group())
        else:
            if indicator.lower() in text_lower:
                entities.residency_indicators.append(indicator)
    entities.residency_indicators = _dedupe(entities.residency_indicators)

    # Addresses
    for pattern in _ADDRESS_PATTERNS:
        matches = re.findall(pattern, text)
        for match in matches:
            if isinstance(match, tuple):
                entities.addresses.append(" ".join(match))
            else:
                entities.addresses.append(match)
    entities.addresses = _dedupe(entities.addresses)

    # Names: lines matching "Name: ...", "Navn: ...", "Full name: ..."
    name_patterns = [
        r"(?:full\s+)?name\s*[:]\s*(.+)",
        r"(?:fullt\s+)?navn\s*[:]\s*(.+)",
        r"(?:surname|etternavn)\s*[:]\s*(.+)",
        r"(?:given\s+name|fornavn)\s*[:]\s*(.+)",
    ]
    for pattern in name_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        entities.names.extend(m.strip() for m in matches if m.strip())
    entities.names = _dedupe(entities.names)

    # spaCy NER enrichment (if model is available)
    nlp_model = _load_spacy_model()
    if nlp_model is not None:
        try:
            doc = nlp_model(text)
            for ent in doc.ents:
                value = ent.text.strip()
                if not value:
                    continue

                # Person names
                if ent.label_ in {"PER", "PERSON"}:
                    entities.names.append(value)

                # Places / addresses
                if ent.label_ in {"GPE", "GPE_LOC", "LOC"}:
                    entities.addresses.append(value)

                # Date entities
                if ent.label_ in {"DATE"}:
                    entities.dates.append(value)

                # Organizations that may indicate UDI/Politi/Kompetanse Norge
                if ent.label_ in {"ORG"}:
                    lower_value = value.lower()
                    if any(
                        token in lower_value
                        for token in (
                            "udi",
                            "politi",
                            "kompetanse norge",
                            "utlendingsdirektoratet",
                        )
                    ):
                        entities.keywords_found.append(value)
        except Exception:
            # Keep regex-only behavior on any runtime model issue
            pass

    # Deduplicate again after spaCy enrichment
    entities.dates = _dedupe(entities.dates)
    entities.names = _dedupe(entities.names)
    entities.addresses = _dedupe(entities.addresses)
    entities.keywords_found = _dedupe(entities.keywords_found)

    # Numeric values (years, amounts)
    numeric_matches = re.findall(
        r"\b(\d{1,2})\s+(?:years?|år|months?|måneder?)\b", text, re.IGNORECASE
    )
    entities.numeric_values = _dedupe(numeric_matches)

    # Expiry dates — contextual patterns only (label + date)
    for pattern in _EXPIRY_CONTEXT_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        entities.expiry_dates.extend(matches)
    entities.expiry_dates = _dedupe(entities.expiry_dates)

    # Total entity count
    entities.raw_entity_count = (
        len(entities.dates)
        + len(entities.passport_numbers)
        + len(entities.names)
        + len(entities.nationalities)
        + len(entities.keywords_found)
        + len(entities.language_indicators)
        + len(entities.residency_indicators)
        + len(entities.addresses)
        + len(entities.numeric_values)
        + len(entities.expiry_dates)
    )

    return entities


def parse_date_flexible(date_str: str) -> date | None:
    """Parse a date string in the common formats found on travel/identity documents.

    Supports: DD.MM.YYYY, DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, YYYY.MM.DD, and
    two-digit-year variants.  Returns ``None`` when the string cannot be parsed.
    """
    date_str = date_str.strip()
    if not date_str:
        return None

    # Normalize OCR quirks and bilingual month fragments (e.g. "JUL / JUIL").
    normalized = date_str
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = normalized.replace("_", "-")
    normalized = normalized.replace("–", "-").replace("—", "-")
    normalized = re.sub(
        r"\b([A-Za-zÆØÅæøå]{3,10})\s*/\s*[A-Za-zÆØÅæøå]{3,10}\b",
        r"\1",
        normalized,
        flags=re.IGNORECASE,
    )

    month_map = {
        # English
        "jan": "01",
        "january": "01",
        "feb": "02",
        "february": "02",
        "mar": "03",
        "march": "03",
        "apr": "04",
        "april": "04",
        "may": "05",
        "jun": "06",
        "june": "06",
        "jul": "07",
        "july": "07",
        "aug": "08",
        "august": "08",
        "sep": "09",
        "sept": "09",
        "september": "09",
        "oct": "10",
        "october": "10",
        "nov": "11",
        "november": "11",
        "dec": "12",
        "december": "12",
        # Norwegian
        "januar": "01",
        "februar": "02",
        "mars": "03",
        "mai": "05",
        "juni": "06",
        "juli": "07",
        "okt": "10",
        "oktober": "10",
        "des": "12",
        "desember": "12",
    }
    for month_name, month_number in month_map.items():
        normalized = re.sub(
            rf"\b{month_name}\b",
            month_number,
            normalized,
            flags=re.IGNORECASE,
        )

    normalized = re.sub(r"[\s./]+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-")

    # MRZ-style compact dates occasionally appear (YYMMDD).
    if re.fullmatch(r"\d{6}", normalized):
        yy = int(normalized[0:2])
        mm = int(normalized[2:4])
        dd = int(normalized[4:6])
        try:
            current_yy = datetime.now().year % 100
            year = 2000 + yy if yy <= current_yy + 20 else 1900 + yy
            return date(year, mm, dd)
        except ValueError:
            return None

    for fmt in (
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%Y.%m.%d",
        "%Y/%m/%d",
        "%d.%m.%y",
        "%d/%m/%y",
        "%d-%m-%y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d-%m-%y",
    ):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d-%m-%y"):
        try:
            return datetime.strptime(normalized, fmt).date()
        except ValueError:
            continue
    return None


def compute_document_nlp_score(entities: ExtractedEntities) -> float:
    """Compute a 0–1 quality score based on how many entity categories are populated.

    Used as an input signal for the eligibility rule engine.
    """
    category_scores: list[float] = []

    # Identity signals (dates + passport numbers)
    identity_signal = min(1.0, (len(entities.dates) + len(entities.passport_numbers)) / 3)
    category_scores.append(identity_signal * 0.25)

    # Citizenship keyword density
    keyword_signal = min(1.0, len(entities.keywords_found) / 5)
    category_scores.append(keyword_signal * 0.20)

    # Nationality detection
    nationality_signal = 1.0 if entities.nationalities else 0.0
    category_scores.append(nationality_signal * 0.15)

    # Language indicators
    lang_signal = min(1.0, len(entities.language_indicators) / 2)
    category_scores.append(lang_signal * 0.15)

    # Residency indicators
    residency_signal = min(1.0, len(entities.residency_indicators) / 2)
    category_scores.append(residency_signal * 0.15)

    # Name extraction
    name_signal = 1.0 if entities.names else 0.0
    category_scores.append(name_signal * 0.10)

    return round(sum(category_scores), 2)


def _dedupe(items: list[str]) -> list[str]:
    """Remove duplicates while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = item.strip().lower()
        if normalized not in seen:
            seen.add(normalized)
            result.append(item.strip())
    return result
