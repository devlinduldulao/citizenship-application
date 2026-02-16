# Reviewer Guide (UDI / Police Officer / Admin) — End-to-End

This guide explains the full reviewer workflow for superusers (UDI/Politi/admin) handling manual-review cases.

## 1) Log in as reviewer/admin

1. Go to http://localhost:5173/login.
2. Log in with a reviewer account (superuser privileges required for queue/review actions).
3. You will enter the authenticated dashboard.

## 2) Open the Applications workspace

1. Navigate to **Applications**.
2. Use this page as the primary review workstation for queue, evidence, AI support, decisions, and audit trail.

## 3) Start with workload prioritization

1. Review **Manual Review Workload** metrics:
   - Pending manual count
   - Overdue count
   - High-priority count
2. Check top queue entries.
3. Prioritize overdue and high-risk items first.

## 4) Select a case

1. Click an application card from the list.
2. Confirm applicant identity fields and current status.
3. Use creation timestamps and status to triage urgency.

## 5) Review uploaded evidence

1. In **Uploaded Documents**, inspect:
   - Document type
   - Processing status
   - File naming context
2. Identify missing or weak evidence categories.

## 6) Use explainability + AI assist

1. Open **Decision Breakdown** to review rule-by-rule rationale and confidence/risk indicators.
2. Open **AI Case Explainer** for a structured case memo.
3. Open **AI Evidence Recommendations** for targeted missing-document suggestions.
4. Treat AI outputs as decision support; final judgment remains human-owned.

## 7) Submit decision

1. In **Caseworker Review Decision**:
   - Choose one action: `approve`, `reject`, or `request_more_info`
   - Enter a clear reason (minimum length enforced)
2. Submit the decision.
3. Confirm success message and updated application status.

## 8) Verify audit trail

1. Open **Audit Trail** for the selected application.
2. Confirm event history includes:
   - Processing events
   - Reviewer action
   - Decision reason metadata
3. Use the timeline for accountability and handoff.

## 9) Continue queue processing

1. Return to the review queue.
2. Repeat steps 4–8 for next prioritized case.
3. Re-check metrics periodically during shift operations.

---

## Reviewer operating standards

- Always evaluate evidence quality before final action.
- Use AI and rule outputs as transparent support, not automatic verdicts.
- Keep decision reasons precise and case-specific for legal/operational traceability.
- Process overdue/high-priority cases first to reduce SLA risk.
