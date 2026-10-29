# Document Desk — Household phase

This updates the local Jupiter app, not a hosted replacement. Current readers,
originals, drive review, sort controls, runtime settings and WebUI are preserved.

## Install on Jupiter

1. Save `Document-Desk-Household-Update.zip` in `/mnt/user/appdata/document-desk/`.
2. In Jupiter's terminal run:

```bash
unzip -q /mnt/user/appdata/document-desk/Document-Desk-Household-Update.zip -d /mnt/user/appdata/document-desk/household-update
bash /mnt/user/appdata/document-desk/household-update/update-jupiter.sh
```

Use a fresh extraction directory for each install. Do not extract over `app`.
The installer briefly stops Document Desk, saves an app/state rollback archive,
and retains the existing Docker runtime configuration. It restarts the previous
container and restores app/state if installation fails. This installation backup
is not a full document backup. No media transfer containers are stopped.

Open http://<server-ip>:8092/ and refresh the browser.

## First household setup

- Sign in using the existing household password and leave Username blank.
- Open Household and create YOUR administrator account first. Choose Administrator.
- Sign out and sign in with your new username/password. Then add family accounts.
- Once an active named administrator exists, new shared-password sign-ins stop.
  Existing sessions expire normally. Keep credentials in your password manager.
- Members can see shared records and their own private records. Administrators
  can see all records and manage users and drive review. New uploads start private.
- Existing records stay household shared to preserve prior behavior. Review Medical
  records and explicitly change visibility where needed. This is application access
  control: an Unraid administrator with disk access can still read local files.
- A member can organize/edit shared records; only an owner or administrator can
  change a record's visibility. Household shows account enable/disable and password
  reset controls. Disabling an account ends its existing access on the next request.
- Use HTTPS/VPN for remote access; this release does not create remote access.

## EOB acceptance workflow

1. Upload one EOB. Unknown is allowed; the original remains in the inbox.
2. Select it and choose New folder. Enter `Medical/Insurance/EOBs`.
3. Add a collection `Camry Accident` and the appropriate tag, such as `2026 Taxes`.
   Tags are organizational labels, not a determination of tax eligibility.
4. Keep Private or explicitly select Household. Click Save review or Approve & file.
5. Unclassified records can now be filed without teaching a type first.
6. Search extracted text and filter by folder, tag or collection. All document data
   is filtered by access before reaching the browser, including original downloads.
7. Archived records support organization changes. Changing an archived folder updates
   its organizational location without moving the stored original. Type/text edits
   on archived records are still locked. Original bytes are preserved.
8. Confirm an authorized second account can find it and an unauthorized account cannot.

Collections associate records across folders without duplicating files. For example,
a Camry Accident collection can contain Medical EOBs and Insurance correspondence.
Tags and collections accept comma-separated names. QR scanning, reminders, full item
records, Paperless, Uppy, and external search engines are subsequent work, not included.
No extra containers or cloud document processing are required for this release.

## Full backup and restore drill

The full backup stops only Document Desk while capturing originals, application,
SQLite state (including accounts and tags), and actual Docker container configuration.
The archive includes private documents and credentials. Restrict access to its folder.
It is not encrypted: use an encrypted destination or add encryption before offsite use.

```bash
bash /mnt/user/appdata/document-desk/app/backup-jupiter.sh
```

Pass a pre-existing backup destination on a separate disk/device as the first
argument. For a remote mount, verify it is mounted before invoking the script;
do not use an unavailable remote path because it could write onto Jupiter instead.
The default local backup is a recovery point, not independent disaster protection.
The script prints the archive path and creates a matching `.sha256` file.
No pruning occurs; choose retention after assessing available space and backup size.

Perform the recovery drill (replace TIMESTAMP; use an empty target with enough space):

```bash
bash /mnt/user/appdata/document-desk/app/restore-test.sh \
  /mnt/user/appdata/document-desk/backups/household-TIMESTAMP.tar.gz \
  /mnt/user/appdata/document-desk/restore-check-TIMESTAMP
```

The drill verifies the archive checksum, safely extracts a separate recovery copy,
checks SQLite integrity, and compares every recorded document SHA-256. It does not
change live files or run another server. Restoring to a replacement machine and
verifying sign-in remains the final operational recovery test. Keep `.env` and
container configuration confidential during recovery.

For nightly automation, if Unraid User Scripts is installed, add an entry containing:

```bash
#!/bin/bash
bash /mnt/user/appdata/document-desk/app/backup-jupiter.sh
```

Set its schedule to Daily after the first successful backup and recovery drill.
This package provides the utility; no schedule has been installed remotely.
Choose the independent destination before enabling regular backups. Success/failure
appears in User Scripts logs. A dashboard backup timestamp and push alerts are not
implemented in this release.

## Validation and limits

Run `python test_household.py`, `python test_workflow.py`, and `python test_catalog.py`
and `python test_backup.py` inside a matching environment with `requirements.txt` and Tesseract installed.
No family accounts are pre-created, no live documents are migrated here, and no
Jupiter backup has run until you execute these steps on the server.
