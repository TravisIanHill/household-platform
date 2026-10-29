#!/usr/bin/env bash
# Extract to an EMPTY directory and verify the database and every tracked original.
# Does not touch the live app or start a second server.
set -euo pipefail
umask 077
archive=${1:?Pass backup archive}
destination=${2:?Pass an empty restore-test directory}
[[ -f "$archive.sha256" ]] || { echo 'Checksum file missing.'; exit 1; }
sha256sum -c "$archive.sha256"
mkdir -p "$destination"
[[ -z "$(ls -A "$destination")" ]] || { echo 'Restore directory must be empty.'; exit 1; }
# Python validates archive members before extraction and verifies restored contents.
docker run --rm -i -v "$archive:/backup.tar.gz:ro" -v "$destination:/restore" python:3.12-slim python - <<'PY'
import tarfile,sqlite3,json,hashlib
from pathlib import Path
root=Path('/restore')
with tarfile.open('/backup.tar.gz') as t:
 for m in t.getmembers():
  p=Path(m.name)
  if p.is_absolute() or '..' in p.parts or m.issym() or m.islnk() or not (m.isfile() or m.isdir()):raise ValueError('Unsafe archive member')
 t.extractall(root,filter='data')
c=sqlite3.connect(root/'state/desk.sqlite')
assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
count=0
for row in c.execute('SELECT data FROM docs'):
 d=json.loads(row[0]);p=(root/'documents'/d['path']).resolve()
 assert (root/'documents').resolve() in p.parents,'Invalid document path'
 assert p.is_file(),'Missing original: '+d['id']
 if d.get('sha256'):
  h=hashlib.sha256()
  with p.open('rb') as f:
   for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
  assert h.hexdigest()==d['sha256'],'Original checksum mismatch: '+d['id']
 count+=1
assert (root/'app/app.py').is_file()
assert (root/'runtime/container.json').is_file()
print('PASS: database integrity and',count,'original document checksums. Extracted recovery copy is ready.')
print('This verifies data recovery; boot and sign-in on a replacement server remain a separate test.')
PY
