#!/usr/bin/env bash
# Full, consistent backup. Run from Unraid terminal or User Scripts.
set -euo pipefail
umask 077
app_root=/mnt/user/appdata/document-desk
documents=/mnt/user/documents/document-desk
backup_dir=${1:-/mnt/user/appdata/document-desk/backups}
mkdir -p "$backup_dir"
chmod 700 "$backup_dir"
exec 9>"$app_root/maintenance.lock"
flock -n 9 || { echo 'Document Desk maintenance is already running.'; exit 1; }
stamp=$(date +%Y%m%d-%H%M%S)
archive="$backup_dir/household-$stamp.tar.gz"
restart=0
cleanup(){ if [[ "$restart" == 1 ]]; then docker start document-desk >/dev/null; fi; }
trap cleanup EXIT
running=$(docker inspect --format '{{.State.Running}}' document-desk)
if [[ "$running" == true ]]; then docker stop document-desk >/dev/null; restart=1; fi
work=$(mktemp -d "$backup_dir/.backup-XXXXXX")
# Container configuration contains secrets. It is stored only inside the protected archive.
docker inspect document-desk > "$work/container.json"
if ! tar -czf "$archive.partial" -C "$app_root" app state -C "$documents" --transform='s,^\.$,documents,' --transform='s,^\./,documents/,' . -C "$work" --transform='s,^container.json$,runtime/container.json,' container.json; then
 rm -rf "$work"; rm -f "$archive.partial"; echo 'Backup failed.'; exit 1
fi
rm -rf "$work"
# Ensure it is readable before declaring success. Full restore drill is separate.
tar -tzf "$archive.partial" >/dev/null
mv "$archive.partial" "$archive"
sha256sum "$archive" > "$archive.sha256"
cleanup; restart=0
printf 'Backup created: %s\n' "$archive"
echo 'Keep a copy on a separate device. Backups contain private records and credentials.'
echo 'Restore drill: bash restore-test.sh /path/to/household-TIMESTAMP.tar.gz /empty/test-directory'
