# Hackathon Judge Q&A

## Is this real AI or just rules?

It’s both. We use real AI components in the production flow:

- OCR with Tesseract for scanned/image documents.
- NLP with spaCy Norwegian NER for entity recognition.
- Rule-based explainability layer to convert evidence into transparent scoring.

This hybrid design is easier to trust and audit than black-box-only models.

## Why not use an LLM for everything?

- Public-sector decisions require traceability and reproducibility.
- Deterministic rules are easier to audit and govern.
- We use generative components for assistance (case explanation/recommendations), not final decisions.

## How do you avoid bias and unfair automation?

- Human-in-the-loop by default: final decision stays with the caseworker.
- Rule-level rationale and evidence are shown for every recommendation.
- Audit trail records all processing and review actions.
- Roadmap includes monitoring and governance controls for model behavior.

## What happens if OCR or NLP fails?

- Graceful degradation is built in.
- Without Tesseract, digital PDFs still process via PyMuPDF.
- Without spaCy model, regex extraction still runs.
- Failures reduce confidence and increase review priority rather than auto-rejecting.

## How accurate is it?

Accuracy depends on the scenario and document quality.

- We show confidence and per-rule evidence instead of claiming perfect automation.
- The system is designed to improve triage quality and consistency, not replace legal review.
- Active-learning feedback from reviewers is in the roadmap.

## What is the measurable value for operations?

- Faster triage by pre-structuring evidence from raw documents.
- More consistent manual decisions using shared explainable criteria.
- Better queue control via confidence/risk-aware prioritization.

## Is the data secure?

- Standard API auth (JWT) and backend access controls are in place.
- Decisions and reviewer actions are logged in an audit trail.
- Production hardening (expanded governance/monitoring) is explicitly in roadmap scope.

## What makes this hackathon project credible beyond demo day?

- Real end-to-end processing (upload → OCR → NLP → explainable scoring → review guidance).
- Automated tests for backend/frontend and OCR/NLP service behavior.
- Clear phased roadmap from MVP to governance-grade production capability.
