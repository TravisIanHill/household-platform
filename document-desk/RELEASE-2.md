# Document Desk release 2 — Family browser and permissions

## Install

Save Document-Desk-Release-2.zip in /mnt/user/appdata/document-desk, then run:

```bash
unzip -q /mnt/user/appdata/document-desk/Document-Desk-Release-2.zip -d /mnt/user/appdata/document-desk/release-2
bash /mnt/user/appdata/document-desk/release-2/update-jupiter.sh
```

Let any upload finish first. Use a fresh extraction directory, not the live app
folder. The installer takes an app/state rollback backup, retains runtime settings
and replaces only application files. Media transfers are unaffected. No Composer
installation is needed. The app briefly stops while the image is rebuilt.

Refresh http://<server-ip>:8092/ with Command-Shift-R.

## Included

- Finder-style Find Documents home: searchable file list, preview, lower detail
  pane. Desktop list and preview panes resize with their browser resize handles.
- Filed records can be edited by their owner, administrators or a matching edit
  grant. The stored original is preserved; edits have before/after history.
  Original download continues to use the upload's original name. The display
  filename may be edited without moving the archived original on disk.
- Typed Birth Certificate fields: person, date, city, county, country, US state /
  territory, issuing agency as printed, issue date and notes. Country choices are
  United States, Canada, Mexico, United Kingdom and Other; use Notes for a country
  not in this starting list. Existing combined fields and values remain visible
  as previous fields. Nothing is guessed into the state or issuing agency fields
  during migration. The built-in type is extended without deleting custom fields.
- Suggest details from document uses local, conservative OCR-text patterns for
  birth certificates. It proposes values with supporting text. Accept each value
  and save to confirm. It does not use a remote AI service, does not infer an agency
  from a state, and does not automatically change permissions. Other document
  types continue to use manual details. Suggestions are not guaranteed complete.
- Household Adult is independent of administrator. Adults do not get access to
  every Private record. Inherited grants cover folder descendants or a collection.
  Matching grants combine. Explicit Private overrides inherited access. Selected
  account sharing and All household sharing grant view-only access to nonowners.
- Person links are separate from text fields/tags and upload ownership. To enable
  access to one's own vital record, link the person to their login in Household
  settings and check the person on the record.
- Members can upload individual files in batches of 25 files / 100 MiB total
  (shown as 100 MB in UI). Existing per-file limits remain 40 MiB documents and
  512 MiB media, subject to the smaller member batch budget. Server manifests
  enforce count, byte budget, per-file declared size, ownership and relative paths.
  New batches are required for members; folders/admin intake/catalog are restricted
  to admins. Permissions are enforced on server routes, search data and downloads.
  A browser cannot prove where files originated if a client deliberately flattens
  folder names; no claim of that kind is made.
- Admin folder intake records a source name/location entered once for that batch,
  per-file paths, outcomes and dates. Sources & Import History shows new batches;
  members see My Uploads only. Old imports do not have retroactive batch receipts.
  The browser does not expose the full network address, so enter it with the source
  name if needed. An autonomous network scanner, resume/retry controls and watched
  folders are not included yet. Re-selecting a folder reuses duplicate checks.
- Approved blue Document Desk and indigo Media Library Desk icon PNGs included.
  Both Unraid icon caches are updated. Document Desk also has a persistent icon
  label on its container. If the Docker image store is replaced, rerun
  /mnt/user/appdata/document-desk/app/install-icons.sh to reseed both caches.
- Existing encrypted Mars backups and the daily User Scripts job are preserved.

## First check after installation

1. Confirm Find Documents opens. Select Sam's filed birth certificate.
2. Correct State or territory to Oregon and Country to United States.
   Hennepin belongs in County of birth. Review Issuing agency against the original;
   leave blank if not certain. The previous combined value remains available.
3. Save details. Check the preview/original and the change history.
4. Try Suggest details from document. Accept only supported values; save to confirm.
5. Household settings: create Parent as a member with Household Adult checked,
   or mark her existing account as Household Adult. Link each person's login under
   People and their logins. Add legal names/nicknames as aliases if useful.
6. A default view rule exists for Family_Records/Vital_Records: Household Adults
   plus people named on the document. On the certificate, check Sam under People
   and choose Use folder / collection rules. Save. EXISTING PRIVATE RECORDS REMAIN
   PRIVATE UNTIL YOU EXPLICITLY CHANGE THEIR ACCESS. Alternatively choose Named
   people and household adults for a per-document grant independent of folders.
7. Test Parent: record is readable; she cannot edit under a view rule. Test a
   different ordinary member: they cannot find or download it. Test Sam after
   linking her login: she can view her own record.
8. Check both icons on Unraid's Docker page. Refresh if needed. The approved icons
   are also available at /static/icons/document-desk.png and
   /static/icons/media-library-desk.png without document access.

## Limits and deferred work

This release does not encrypt live Jupiter originals/OCR/database, add password
reconfirmation, or audit every read/download. Change history covers edits and
sharing. Server administrators still have filesystem access. OCR suggestions need
review. Full replacement-server boot/recovery remains untested on Jupiter.
The type teaching screen still creates text fields for new custom types; the new
built-in Birth Certificate type has the typed controls. Do not recreate that type.

## Validation

Acceptance tests cover filed metadata edits/original checksums/sidecars/history,
legacy field retention, suggestions without writes, people/adult/selected access,
private overrides, read-only grants, denied downloads/search/resharing, manifests
and budgets, source receipts, OCR, existing catalog and backup behavior. A jsdom
interface test covers list selection, preview, typed inputs, accepting and saving
suggestions, household controls, and viewer controls. JavaScript and shell syntax
checks passed. Docker operations in backup tests are simulated. No visual browser
QA or live deployment can be performed from this workspace; verify on Jupiter.
