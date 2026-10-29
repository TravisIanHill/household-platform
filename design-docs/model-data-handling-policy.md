# Model-Assistance Data Handling Policy

Status: **Stated** by Travis on October 17, 2026, recorded here as a proposed enforceable policy. Provider choice is open.

## Statement
Travis is comfortable with a hosted model depending on whether it can be secured and the data protected, and strongly depending on data type: nothing financial, no PDFs or documents of that nature; media files are of little concern to him.

## Classes
**Class 0 — never leaves the server.** Financial, tax, medical and insurance records (including EOBs), identity documents, any PDF or document and its extracted text, Private records, credentials, API keys and tokens. Document Desk OCR stays local (it uses local Tesseract).
**Class 1 — conditional.** Personal photos and videos. Stated as low concern. Proposed safeguards (Travis may relax them): per-type opt-in, location and other embedded metadata stripped before sending, and a visible "what will be sent" preview. Note for consideration: media can show identifiable people, including children, and embedded location data.
**Class 2 — may leave.** Software-need briefs, public GitHub content, public documentation, sanitized examples. Briefs are checked for household specifics (names, addresses) before sending.
Development Discovery Phase 1 uses Class 2 only. It never touches Class 0 or Class 1 data.

## Enforcement (Proposed)
1. A server-side gate decides what may be sent; hiding a button is not enough.
2. A per-type setting "may use hosted model" defaults to **off** for every new type, including types created by a future wizard.
3. Show Travis the exact payload before the first use of any new data type with a hosted model.
4. Log what was sent (class, size, time, destination), not the content.
5. Tokens never appear in logs, exports or the browser.
6. Development and tests use sanitized or synthetic data.
7. A local-only mode remains available and the application works with model assistance off.

## About "encrypted and protected"
Transport encryption (TLS) protects data in transit, but a model that must read the data cannot be given data it cannot decrypt. The practical protections are: sending less, classifying what is sent, and choosing a provider whose current terms on retention, use of data for training, deletion and region are acceptable. Review those terms at the time a provider is chosen; this document does not describe any provider's terms.
