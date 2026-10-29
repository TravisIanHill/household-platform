#!/bin/bash
set -euo pipefail
umask 077
root=/mnt/user/appdata/document-desk
icons="$root/app/static/icons"
# Persistent Docker image cache plus the active web GUI cache.
for target in /var/lib/docker/unraid/images /var/local/emhttp/plugins/dynamix.docker.manager/images; do
 mkdir -p "$target"
 for name in document-desk media-library-desk; do
  test -f "$icons/$name.png"
  if [[ -f "$target/$name-icon.png" ]]; then cp -n "$target/$name-icon.png" "$root/backups/$name-icon-before-release2.png" || true; fi
  cp "$icons/$name.png" "$target/$name-icon.png"
  chmod 644 "$target/$name-icon.png"
 done
done
echo 'Both Unraid icon caches updated. Refresh the Docker page.'
