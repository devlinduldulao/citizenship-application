# Immigrant User Guide (End-to-End)

This guide explains the full flow for an applicant (immigrant) using the citizenship application portal.

## 1) Open the app

1. Go to http://localhost:5173.
2. You will be redirected to the login page if not authenticated.

## 2) Create an account (first-time users)

1. Click **Sign up**.
2. Enter:
   - Email
   - Full name
   - Password
3. Submit the form.
4. After success, log in using your new credentials.

## 3) Log in

1. On the login page, enter your email and password.
2. Click **Log In**.
3. After login, you will land inside the authenticated app layout.

## 4) Create a citizenship application

1. Open the **Applications** page.
2. In **Create New Application**, fill:
   - Applicant full name
   - Applicant nationality
   - Optional notes/context
3. Click **Create Application**.
4. The newly created case appears in the application list.

## 5) Upload supporting documents

1. Select your application from the list.
2. In **Upload Requirement Documents**:
   - Enter a `document_type` (examples: `passport`, `residence_permit`, `language_certificate`, `police_clearance`)
   - Choose a file (PDF/JPG/PNG/WEBP)
3. Click **Upload**.
4. Repeat until all required evidence is uploaded.

## 6) Trigger processing

1. With the application selected, click the processing button in the upload card.
2. The backend runs OCR/NLP and eligibility scoring.
3. Wait for status updates in the application and document sections.

## 7) Track status and outcomes

1. Monitor your application status (for example: `draft`, `processing`, `review_ready`, `approved`, `rejected`, `more_info_required`).
2. Review visible summaries and timeline updates.
3. If more evidence is requested, upload additional documents and reprocess.

## 8) Update profile/security (optional)

1. Open **Settings**.
2. Update profile information if needed.
3. Change your password if needed.

## 9) Log out

1. Use the user menu/sidebar logout action.
2. You can log in again anytime to continue your case.

---

## Practical tips for applicants

- Upload readable, complete documents to improve scoring quality.
- Use consistent document types so reviewers can quickly assess evidence.
- Add clear notes when your case has special context (residency timeline, language proof details, etc.).
- Check back after processing or reviewer actions for new requests.
