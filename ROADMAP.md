# Product & AI Roadmap

## Guiding principle

Prioritize reviewer productivity and decision quality while preserving human control, explainability, and auditability.

## Phase A — Hackathon Ready (Now)

- Stabilize OCR + NLP extraction on realistic uploaded documents.
- Keep OpenAPI contract and frontend SDK in lockstep (Hey API generated client only).
- Deliver two AI-assist endpoints:
  - `GET /api/v1/applications/{application_id}/case-explainer`
  - `GET /api/v1/applications/{application_id}/evidence-recommendations`
- Surface AI outputs directly in the Applications workflow UI.

## Phase B — Reviewer Copilot (Next)

- Add contextual copilot Q&A for selected application:
  - Why this risk level?
  - Which rules failed and why?
  - What document would improve confidence most?
- Ground answers in rule evidence, OCR/NLP extraction, and audit timeline.
- Include strict citation payloads for every copilot answer to keep outputs traceable.

## Phase C — Predictive Operations (Short-Term)

- Train lightweight predictors for:
  - probability of `request_more_info`
  - expected SLA breach risk
  - confidence uplift from additional document classes
- Use model outputs only for ranking and triage, never automatic final decisions.

## Phase D — Policy Intelligence (Mid-Term)

- Expand deterministic policy rule coverage with legal-domain rule packs.
- Add versioned rule sets and decision reproducibility by rule version.
- Build simulation mode for caseworker training and policy-change impact analysis.

## Phase E — Governance & Production Hardening (Mid-Term)

- Add model monitoring for drift, quality, and latency.
- Add prompt/version lineage in audit events for AI-generated outputs.
- Add stronger access controls and governance workflows for model configuration changes.

## Additional AI roadmap candidates (post-hackathon)

- Retrieval-grounded reviewer copilot over policy text, prior decisions, and audit events.
- Active-learning loop where reviewer corrections improve extraction quality over time.
- Document tamper/anomaly detection (cross-file identity mismatch, suspicious edits, metadata inconsistencies).
- Auto-generated draft decision letters with mandatory reviewer approval before release.

## Suggested implementation order

1. Keep endpoint + SDK contract checks in CI (`verify:api-contract`).
2. Improve quality of evidence recommendations using reviewer feedback loops.
3. Introduce copilot Q&A with citation-first responses.
4. Add triage prediction and queue optimization models.
5. Expand policy/rule coverage and governance tooling.
