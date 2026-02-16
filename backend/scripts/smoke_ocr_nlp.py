"""Live smoke test for real OCR + NLP pipeline."""

import os
import tempfile
import time
import uuid

import fitz  # PyMuPDF
import httpx

# --- Create realistic test PDFs ---

pdf_path = os.path.join(tempfile.gettempdir(), "test_passport.pdf")
doc = fitz.open()
page = doc.new_page()
page.insert_text((72, 72), "KINGDOM OF NORWAY", fontsize=16)
page.insert_text((72, 100), "PASSPORT / PASS", fontsize=14)
page.insert_text((72, 140), "Surname: HASSAN", fontsize=11)
page.insert_text((72, 160), "Given name: Ahmed Mohamed", fontsize=11)
page.insert_text((72, 180), "Nationality: Somali", fontsize=11)
page.insert_text((72, 200), "Date of birth: 15.03.1990", fontsize=11)
page.insert_text((72, 220), "Passport No: NO1234567", fontsize=11)
page.insert_text((72, 240), "Date of issue: 2023-01-15", fontsize=11)
page.insert_text((72, 260), "Valid until: 2033-01-15", fontsize=11)
page.insert_text((72, 280), "Place of birth: Mogadishu", fontsize=11)
doc.save(pdf_path)
doc.close()

lang_path = os.path.join(tempfile.gettempdir(), "test_norskprove.pdf")
doc2 = fitz.open()
page2 = doc2.new_page()
page2.insert_text((72, 72), "KOMPETANSE NORGE", fontsize=14)
page2.insert_text((72, 100), "Norskprøve - Test i norsk", fontsize=12)
page2.insert_text((72, 130), "Full name: Ahmed Mohamed Hassan", fontsize=11)
page2.insert_text((72, 150), "Date of birth: 15 mars 1990", fontsize=11)
page2.insert_text((72, 170), "Muntlig: B1 - Bestått", fontsize=11)
page2.insert_text((72, 190), "Skriftlig: B2 - Bestått", fontsize=11)
page2.insert_text((72, 210), "Samfunnskunnskap: Passed", fontsize=11)
page2.insert_text((72, 230), "Date: 20 oktober 2024", fontsize=11)
doc2.save(lang_path)
doc2.close()

print("Test PDFs created")

# --- API calls ---

base = "http://localhost:8000/api/v1"

email = f"ai-test-{uuid.uuid4().hex[:6]}@test.com"
httpx.post(
    f"{base}/users/signup",
    json={"email": email, "password": "testpass123", "full_name": "AI Test User"},
    timeout=30,
).raise_for_status()
tok = httpx.post(
    f"{base}/login/access-token",
    data={"username": email, "password": "testpass123"},
    timeout=30,
).json()
headers = {"Authorization": f"Bearer {tok['access_token']}"}

app_resp = httpx.post(
    f"{base}/applications/",
    headers=headers,
    json={
        "applicant_full_name": "Ahmed Mohamed Hassan",
        "applicant_nationality": "Somali",
        "notes": "Lived in Norway for 7 years. Permanent residence since 2020.",
    },
    timeout=30,
).json()
app_id = app_resp["id"]

with open(pdf_path, "rb") as f:
    httpx.post(
        f"{base}/applications/{app_id}/documents",
        headers=headers,
        data={"document_type": "passport"},
        files={"file": ("passport.pdf", f, "application/pdf")},
        timeout=30,
    ).raise_for_status()

with open(lang_path, "rb") as f:
    httpx.post(
        f"{base}/applications/{app_id}/documents",
        headers=headers,
        data={"document_type": "language_certificate"},
        files={"file": ("norskprove.pdf", f, "application/pdf")},
        timeout=30,
    ).raise_for_status()

print("Documents uploaded, processing...")
httpx.post(
    f"{base}/applications/{app_id}/process",
    headers=headers,
    json={"force_reprocess": False},
    timeout=30,
).raise_for_status()

# Wait until processing completes (poll status)
for attempt in range(20):
    time.sleep(1)
    status_resp = httpx.get(
        f"{base}/applications/{app_id}",
        headers=headers,
        timeout=30,
    ).json()
    status = status_resp["status"]
    print(f"  Poll {attempt + 1}: status={status}")
    if status not in ("queued", "processing"):
        break
else:
    print("WARNING: Timed out waiting for processing to complete")

# --- Decision Breakdown ---
breakdown = httpx.get(
    f"{base}/applications/{app_id}/decision-breakdown",
    headers=headers,
    timeout=30,
).json()

print("\n=== DECISION BREAKDOWN ===")
print(f"Recommendation: {breakdown['recommendation']}")
print(f"Confidence: {breakdown['confidence_score']}")
print(f"Risk level: {breakdown['risk_level']}")
print()

for rule in breakdown["rules"]:
    status = "PASS" if rule["passed"] else "FAIL"
    print(
        f"  [{status}] {rule['rule_name']}: "
        f"score={rule['score']}, weight={rule['weight']}"
    )
    print(f"        Rationale: {rule['rationale']}")
    evidence = rule.get("evidence", {})
    for key in [
        "nlp_passport_numbers",
        "nlp_language_indicators",
        "nlp_residency_indicators",
        "total_entities_extracted",
        "nationalities_found",
        "keywords_found",
        "names_found",
        "nlp_addresses",
    ]:
        if key in evidence and evidence[key]:
            val = evidence[key]
            if isinstance(val, list):
                val = val[:8]
            print(f"        {key}: {val}")
    print()

# --- Document extraction details ---
docs = httpx.get(
    f"{base}/applications/{app_id}/documents",
    headers=headers,
    timeout=30,
).json()

for d in docs["data"]:
    print(f"--- Document: {d['original_filename']} ({d['document_type']}) ---")
    print(f"  Status: {d.get('status', '?')}")
    print(f"  Processing error: {d.get('processing_error', 'None')}")
    ocr_text = d.get("ocr_text", "")
    print(f"  OCR text (first 200 chars): {(ocr_text or '')[:200]}")
    ef = d.get("extracted_fields", {}) or {}
    print(f"  Raw extracted_fields keys: {list(ef.keys())}")
    print(f"  Extraction method: {ef.get('extraction_method', 'N/A')}")
    print(f"  Confidence: {ef.get('extraction_confidence', 'N/A')}")
    print(f"  Chars extracted: {ef.get('char_count', 0)}")
    print(f"  NLP score: {ef.get('nlp_score', 0)}")
    entities = ef.get("entities", {})
    if entities:
        print(f"  Dates: {entities.get('dates', [])}")
        print(f"  Passport numbers: {entities.get('passport_numbers', [])}")
        print(f"  Nationalities: {entities.get('nationalities', [])}")
        print(f"  Names: {entities.get('names', [])}")
        print(f"  Keywords: {entities.get('keywords_found', [])[:8]}")
        print(f"  Language indicators: {entities.get('language_indicators', [])}")
        print(f"  Residency indicators: {entities.get('residency_indicators', [])}")
    print()

os.unlink(pdf_path)
os.unlink(lang_path)
print("SMOKE TEST COMPLETE")
