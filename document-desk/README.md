# Sage interface update — staged, not deployed

Built October 14, 2026 on top of the latest Document Desk review package.

- Warm sage intake panel, ivory background and olive text; medium-weight rounded system font with platform fallbacks, no remote fonts.
- Readable display titles, full original filenames preserved in review details and hover text; no physical file renaming.
- Search and status combine with actual extension filters and sorting by added date, source file modification date, size, name, document category, or extension.
- Matching count and reset controls; unknown sizes/dates sort last in either direction.
- New browser uploads record size and browser-reported source modification date. Existing records obtain size from the retained file and leave unknown source dates unknown. File date means modification time, not capture date or document date.
- Existing folder intake, catalog review and filing behavior retained.

Validation: queue logic checks, upload metadata and existing-record checks, document workflow tests (including OCR/readers), catalog regression tests, and JavaScript syntax checks passed. Browser visual verification remains pending: the test environment could not obtain a Chromium executable. Apple rounded font appearance must be checked on the user's Mac/iPhone.

The Saturn-to-Jupiter copy plan is now approved and its separate host transfer is running. Deploy this update by extracting it into a separate folder and running update-jupiter.sh on Jupiter. The updater preserves the actual container configuration and WebUI labels, backs up code/state before replacement, restores the previous app on failure, and removes the stopped rollback container after success. The source code changes do not touch the media transfer. New individual accounts and scheduled backups are not included.

The installer has passed mocked Docker lifecycle checks for success and build-failure rollback. Actual on-device deployment and visual checks remain necessary. Backups are recovery snapshots, not scheduled backups and do not include document originals.

---

# Document Desk — Jupiter first version

One password-protected household workspace. Local extraction only: no documents are sent to cloud AI. Drag in PDFs, images, DOCX, XLSX, saved .eml email, CSV or text. Review the extracted text, choose a template, enter the filing fields, and approve. Classification, field entry and filenames are manual in this first version; OCR/text extraction is automatic. Teach new document types through the interface. A new file format requires a reader in app.py, not just an extension allowlist change.

## Install on Jupiter

Extract this package to `/mnt/user/appdata/document-desk/app`. Run the following from Jupiter's terminal (Docker Compose plugin is required):

```bash
mkdir -p /mnt/user/documents/document-desk /mnt/user/appdata/document-desk/state
chown 99:100 /mnt/user/documents/document-desk /mnt/user/appdata/document-desk/state
chmod 700 /mnt/user/documents/document-desk /mnt/user/appdata/document-desk/state
cd /mnt/user/appdata/document-desk/app
docker run --rm -it -v "$PWD:/setup" -w /setup python:3.12-slim python setup.py
docker compose up -d --build
```

Open `http://<server-ip>:8092` and use the household password you entered. Verify port 8092 is free before starting. If `docker compose` is unavailable, stop and request the Unraid template installation alternative. The app runs as Unraid nobody/users (99:100). Existing container mappings are unaffected.

Use on a trusted LAN. Password protection does not encrypt plain HTTP traffic. For confidential documents/passwords, use an HTTPS reverse proxy before regular use, set `HTTPS: "1"` in compose environment, and add rate limiting at that proxy. Do not forward port 8092 to the internet. No external URLs are fetched by the app. Originals are served as downloads except PDF/image previews. Executables, HTML, macros and unsupported formats are rejected. This is an initial household app, not a hardened public service.

## Files and backup

`/mnt/user/documents/document-desk/inbox` holds pending originals. Approval moves originals to `archive/<category>/<record-id>/`, alongside `record.json` and `extracted.txt`. UUID folders prevent filename collisions. SHA-256 checks block byte-identical repeat uploads. Files are not encrypted by this app; use your storage permissions/encryption and a suitable Google Drive destination. Google Drive backup is not configured by this package. Credentials and settings are in appdata: back up `/mnt/user/appdata/document-desk/state` and the app's `.env` too. Stop the app when making a consistent backup of both folders.

## Templates and RoboForm

Bills, statements, major purchases, insurance and email templates ship with the app. Use “Teach a type” to add fields, required fields and a destination category. Choose a record of an existing type before opening that dialog to edit its template. Updating a template affects later reviews, not archived records.

The RoboForm panel downloads a plain-text Safenote draft and provides temporary login fields for copying. It does not log into RoboForm, import directly, select a shared folder or produce a verified RoboForm login import format. Choose the family's destination in RoboForm yourself. Safenote drafts contain document text: handle them as sensitive files. Login passwords entered in the copy panel are not sent to the server or saved, but copied values remain on the clipboard until you clear it. Clipboard copying usually requires HTTPS; on LAN HTTP copy fields manually.

## Limits

40 MB per upload, first 30 PDF pages, first 2,000 rows per Excel sheet, first 40 columns, up to 250,000 extracted characters. English OCR. No .msg, .xls, HEIC, PDF password entry, automatic field inference, mailbox scanning, cloud AI, bulk archive editing, document deletion or direct Google Drive sync. Failed extraction preserves the original for manual review. Extraction is synchronous; large scans take time. Required fields can be defined in a template. Archived records are read-only. Session expires after 30 minutes. Shared password means activity cannot identify individual family members.

## First check

Upload a harmless PDF or receipt photo, choose a type, fill fields and approve. Check the new archive folder and its sidecar files. Upload the same file again to check duplicate detection. Create a type with a required field and confirm approval blocks when it is blank. Then introduce real documents.

## Drive review update

Use `bash update-jupiter.sh` from the extracted update package on Jupiter. The updater backs up existing appdata, preserves the household password and documents, and keeps the previous container stopped for rollback. Open `/catalog` from the new Drive review link. Import the full catalog JSON exports from the Mac, rather than uploading source files.

Catalogs are metadata only. The app does not access source drives, copy intake candidates, unpack backup formats, or delete files. Duplicate groups are recomputed across imported sources from usable SHA-256 hashes and sizes. Error entries and entries without hashes remain unknown. "Unique" means no matching hash in the imported inventory; it does not establish value or exclude copies elsewhere. Matching source identities and paths prevent repeated imports from creating false copies. Backup sets and companion metadata still need contextual review, even when individual bytes match.

Review decisions: keep for review, intake candidate, duplicate recommendation. At least one matching copy must remain retained. Download review-plan JSON with source paths and retained-copy locations. Revalidate actual files before any cleanup; catalog evidence may be stale. No deletion or copying is implemented in this update.

Year organization: current calendar year plus six previous years remain named; earlier documents use `category/older/YYYY`. In 2026 this means 2020–2026, with 2019 and earlier under older. Use the optional Year for filing field and Use year folder button to apply a suggestion, then approve. No existing records move automatically and no document expires. Original year remains available in the older archive. Tax and 1098-T starter templates are added only when that exact type name does not already exist.

Nested archive paths now preserve folder hierarchy and reject traversal. Same-origin document previews are permitted; other sites cannot frame the app. Backend tests: `python test_catalog.py` covers imports, duplicate safeguards, source refresh, protected unknowns/errors, exports, and nested document filing. Existing extraction readers are unchanged.

## Catalog records, folder batches and media intake

Full catalog JSON can be dropped into the catalog intake area. Browser navigation is prevented when files are dropped on this page. Distinct exports are retained under state/catalog-snapshots and offered for download. The latest inventory and decisions persist in SQLite. Different sources accumulate; reimporting the same source refreshes only that source, with unchanged-content decisions retained. Reimport previously imported catalogs once to retain their original export files. Originals are content-deduplicated, so identical exports do not create extra snapshots.

Document intake accepts MOV, MP4, M4V, MKV, AVI and WebM video, plus MP3, M4A, WAV, FLAC and M4B audio. This retains originals for manual review, without transcription or video metadata extraction. Media limit: 512 MB per file. Documents: 40 MB per file. Catalog JSON: 256 MB per file. The folder picker selects supported files recursively, up to 500 total selected files per batch. Unsupported/oversized files are skipped; counts are reported. Each file uploads separately to avoid a single huge request. Stop pauses after the current file. Completed files persist, and resubmitting detects byte-identical duplicates. Browser relative paths are retained as provenance. Source folder structure is not automatically used as archive destinations.

For network scanning, first mount the share through Unraid using its credentials. The app stores no share passwords. Run the updater with NETWORK_SOURCE_PATH set to one specific mounted directory to expose it as /sources read-only. Existing /sources mappings survive subsequent updates. Source must be readable by UID 99/GID 100. The browser lists subfolders and starts or resumes a scan. Requests process up to 500 entries, with a 128 MiB read budget per request. Files over 64 MiB are inventoried with hashes deferred, and stay protected. Symbolic links and unreadable entries stay protected. Completed scans join the catalog and retain a JSON export. No copying into document intake or deletion is performed by network scans. Jobs are retained under state/network-jobs; a paused scan can resume while the mounted source is still available. Source inventory may change during a multi-request scan; recheck source files before acting on results.
