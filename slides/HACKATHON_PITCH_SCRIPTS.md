# Hackathon Pitch Scripts

## AI Hackathon talking points

- **Real AI in production flow:** Tesseract OCR + spaCy Norwegian NER are live in the processing pipeline.
- **Explainable AI, not black box:** Every recommendation is linked to rule evidence, extracted entities, and traceable rationale.
- **Human-in-the-loop governance:** AI assists triage and explanation; caseworkers keep final decision authority.
- **Demo-ready value:** Uploading real documents triggers OCR, entity extraction, confidence scoring, and reviewer guidance end-to-end.

## On-stage cheat sheet (60–90 seconds)

**Hook (10s):** "We built an AI-assisted citizenship review system that reduces manual triage time while keeping humans in control."

**What it does (20s):** "The pipeline reads uploaded files with OCR (PyMuPDF + Tesseract), extracts key evidence with NLP (spaCy Norwegian NER + domain rules), and produces an explainable confidence/risk breakdown."

**Why it matters (15s):** "Reviewers don’t just get a score—they get rule-by-rule rationale and evidence. That improves speed, consistency, and trust."

**Governance (10s):** "This is human-in-the-loop by design: AI assists, caseworkers decide, and actions are auditable."

**Roadmap close (10s):** "Next, we add citation-grounded copilot Q&A, queue risk prediction, and anomaly detection."

**Transition line:** "Now I’ll show one live case going from upload to explainable recommendation."

## 1-minute pitch

"We built an AI-assisted citizenship review system for Norway focused on the real bottleneck: manual document triage.

When someone uploads documents, we run OCR with PyMuPDF and Tesseract to read both digital and scanned files. Then we run NLP with spaCy Norwegian NER plus domain-specific extraction to detect identities, dates, nationalities, residency, and language signals. Finally, an explainable rule engine turns that evidence into confidence, risk level, and a reviewer recommendation.

This isn’t black-box automation. Every score is traceable to evidence, and final decisions always stay with human caseworkers. So we improve speed and consistency while keeping trust and accountability."

## 3-minute pitch

"Today, citizenship caseworkers spend too much time on repetitive document checks. Our system gives them an AI copilot for evidence review while keeping people in control.

Step 1 is document intelligence. We extract text from uploads using PyMuPDF for digital PDFs and Tesseract OCR for scans and images. Step 2 is NLP understanding. We combine spaCy’s Norwegian model with domain rules to identify key entities like names, passport numbers, dates, nationalities, language indicators, and residency clues. Step 3 is explainable scoring. Seven weighted rules turn that evidence into a confidence score, risk level, and rule-by-rule rationale.

For reviewers, this means they don’t just see a score—they see why. Which rules passed, what evidence was found, and what is still missing. We also generate case explanations and evidence recommendations to reduce cognitive load.

Most importantly, this is human-in-the-loop by design. AI helps with triage and consistency, but final approvals and rejections remain caseworker decisions, captured in an immutable audit trail.

From here, our roadmap adds retrieval-grounded reviewer Q&A, queue risk prediction, anomaly detection across documents, and active-learning feedback from reviewer corrections. So this MVP is already useful today and built to scale into a stronger public-sector AI platform."

## Suggested live demo flow (2–4 minutes)

1. Create/open an application and upload `passport` + `language_certificate` sample files.
2. Trigger processing and show extracted OCR text and entities.
3. Open decision breakdown and highlight rule evidence + rationale.
4. Show missing-evidence recommendation and explain human final decision control.
5. Close with roadmap: copilot Q&A, risk forecasting, anomaly detection.

## Speaking style variants

**Recommended default for hackathon judges:** Start with **Energetic** for the first 20–30 seconds to hook attention, then shift to **Formal** for architecture, governance, and Q&A credibility.

**Transition cue (say this verbatim):** "Now I’ll quickly switch from the problem framing to how the system works, why it’s explainable, and how governance is built in."

**Closing transition cue (say this verbatim):** "You’ve seen the system work end-to-end, so I’ll close with what we can deliver next: reviewer copilot Q&A, risk prediction, and stronger governance at production scale."

**Final 10-second close (say this verbatim):** "Thank you for your time—our goal is simple: faster citizenship review with explainable AI and human accountability. We’d love your feedback on where this should be piloted first."

### Energetic

"We’re solving a real public-sector bottleneck: manual citizenship document triage. Our AI pipeline reads uploaded files with OCR, understands key evidence with NLP, and produces explainable recommendations reviewers can trust. The key point is this: we speed up decisions without losing human control. Every score is evidence-backed, auditable, and ready for real operations—not just a hackathon demo."

### Formal

"This solution addresses a high-friction stage in citizenship processing: evidence triage during manual review. The system applies OCR and NLP to transform unstructured documents into structured, explainable signals. These signals are evaluated through transparent weighted rules that produce confidence and risk outputs with explicit rationale. Final authority remains with caseworkers, ensuring governance, accountability, and operational trust."

### Simple English

"Our system helps officers review citizenship documents faster. First, it reads documents with OCR. Second, it finds important information with NLP, like names, dates, and passport numbers. Third, it gives a clear score with reasons. People still make the final decision. So the system saves time, keeps quality high, and stays safe and transparent."

## 6-slide pitch outline (presenter notes)

### Slide 1 — Problem

- Citizenship case review is document-heavy, repetitive, and time-constrained.
- Manual triage creates queue bottlenecks and inconsistent outcomes.
- Caseworkers need faster evidence synthesis without losing governance.

**Talk track:** "The bottleneck isn’t data entry—it’s review time per case. We cut review friction while keeping accountability intact."

### Slide 2 — Solution

- AI-assisted review workflow for uploaded citizenship documents.
- Converts unstructured files into structured evidence and reviewer guidance.
- Keeps final approval/rejection decisions with human caseworkers.

**Talk track:** "We support decisions; we don’t replace decision-makers."

### Slide 3 — AI architecture

- OCR layer: PyMuPDF + Tesseract for digital and scanned documents.
- NLP layer: spaCy Norwegian NER + domain regex extraction.
- Explainability layer: weighted rules with evidence and rationale per rule.

**Talk track:** "Every score is inspectable: what we extracted, which rule triggered, and why."

### Slide 4 — Live demo

- Upload `passport` and `language_certificate` sample documents.
- Trigger processing and show OCR text + extracted entities.
- Open decision breakdown and highlight confidence, risk, and failed rules.

**Talk track:** "In under a minute, reviewers move from raw files to a structured case view."

### Slide 5 — Impact

- Faster triage for manual-review queues.
- More consistent reviewer decisions through standardized evidence views.
- Stronger trust via human-in-the-loop controls and audit trail.

**Talk track:** "Speed, consistency, and governance improve together—not as trade-offs."

### Slide 6 — Roadmap

- Retrieval-grounded reviewer copilot Q&A with citations.
- Queue risk prediction and proactive SLA breach alerts.
- Cross-document anomaly detection and active-learning feedback loops.

**Talk track:** "This MVP is useful now and ready to grow into a full public-sector AI copilot."

## Closing + demo fallback lines

### 30-second closing statement

"This project shows practical public-sector AI: real OCR and NLP in the workflow, explainable recommendations instead of black-box outcomes, and clear human accountability for final decisions. We reduce reviewer workload and improve consistency today, and our roadmap adds citation-grounded copilot support, risk forecasting, and stronger governance. In short: useful now, trustworthy by design, and built to scale responsibly."

### Fallback answer 1 — If live processing is slow

"The pipeline is asynchronous by design, so brief delays don’t block reviewers. While this request completes, I can show the same end-to-end result from our smoke test output: extracted entities, rule breakdown, confidence score, and recommendation rationale."

### Fallback answer 2 — If OCR/NLP service dependency is unavailable

"The system is built with graceful degradation. If Tesseract or spaCy is unavailable, we still process what we can, lower confidence accordingly, and prioritize human review instead of making unsafe automated conclusions."

### Fallback answer 3 — If frontend demo fails

"The backend contract and logic are independently verifiable. We can demonstrate the same workflow through API endpoints and test outputs: upload, extraction, rule scoring, and audit evidence are all reproducible without UI dependence."
