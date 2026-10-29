# OCR update

Install this package in a fresh extraction directory using update-jupiter.sh.
It preserves the running container configuration and creates an app/state rollback
backup. Python file permissions include all new modules.

New PDF uploads use native text when a readability heuristic passes. Sparse or
punctuation-heavy text uses local Tesseract OCR at up to 300 dpi. This heuristic
cannot detect every kind of garbled text. OCR has a 120-second per-page limit and
retains the existing 30-page / 250000-character extraction caps.

After installation run:

    docker exec document-desk python /app/reprocess_eobs.py

The repair targets only <sample-eob>.pdf, <sample-eob>.pdf, <sample-eob>.pdf,
and <sample-eob>.pdf if present. It OCRs every page within the extraction cap,
retains prior records under /state/ocr-history, updates searchable text and archived
sidecars, and preserves original bytes, folder, tags, collections and visibility.
Do not edit these records while the repair runs. All OCR completes before database
updates begin. If OCR fails, the database remains unchanged. A later sidecar write
failure may require retrying to synchronize sidecars with the saved database.

Refresh Document Desk afterward and verify text and amounts against the PDF.
OCR improves search; it does not automatically classify, rename or total EOBs.

Validation: test_workflow.py, test_household.py and test_ocr.py pass. Tests cover
native/scanned PDFs and a mixed PDF with a deliberately corrupt text layer.
The actual Jupiter documents must be verified after the repair runs there.
