#!/usr/bin/env bash
set -euo pipefail
umask 077
package_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
app_dir=/mnt/user/appdata/document-desk/app
root_dir=/mnt/user/appdata/document-desk
backup_dir="$root_dir/backups"
stamp=$(date +%Y%m%d-%H%M%S)
old_name="document-desk-before-$stamp"
mkdir -p "$backup_dir"
chmod 700 "$backup_dir"
exec 9>"$root_dir/maintenance.lock"
flock -n 9 || { echo 'An update is already running.'; exit 1; }
[[ "$package_dir" != "$app_dir" ]] || { echo 'Extract the update into a separate folder, not over the installed app.'; exit 1; }
for item in app.py household.py access.py details.py intake.py ocr_reader.py reprocess_eobs.py catalog.py Dockerfile requirements.txt templates static update-jupiter.sh backup-jupiter.sh restore-test.sh install-icons.sh; do
 test -e "$package_dir/$item" || { echo "Package file missing: $item"; exit 1; }
done
docker inspect --format '{{.State.Running}}' document-desk | grep -qx true || { echo 'Document Desk is not running. Stopping for review.'; exit 1; }
docker image inspect python:3.12-slim >/dev/null 2>&1 || docker pull python:3.12-slim
config_backup="$backup_dir/container-$stamp.json"
docker inspect document-desk > "$config_backup"
chmod 600 "$config_backup"
docker stop document-desk >/dev/null
if ! tar -czf "$backup_dir/document-desk-$stamp.tar.gz" -C "$root_dir" app state; then
 docker start document-desk >/dev/null
 echo 'Backup failed; the current app was restarted.'
 exit 1
fi
if ! docker rename document-desk "$old_name"; then docker start document-desk >/dev/null; exit 1; fi
rollback() {
 trap - ERR INT TERM
 echo 'Update failed. Restoring the previous app and settings.'
 docker rm -f document-desk >/dev/null 2>&1 || true
 tar -xzf "$backup_dir/document-desk-$stamp.tar.gz" -C "$root_dir"
 docker rename "$old_name" document-desk
 docker start document-desk >/dev/null
}
trap rollback ERR
trap 'rollback; exit 130' INT TERM
for item in app.py household.py access.py details.py intake.py ocr_reader.py reprocess_eobs.py catalog.py Dockerfile requirements.txt templates static test_catalog.py test_workflow.py test_household.py test_backup.py update-jupiter.sh backup-jupiter.sh restore-test.sh install-icons.sh PHASE-HOUSEHOLD.md RELEASE-2.md test_release.py test_ocr.py; do
 cp -R "$package_dir/$item" "$app_dir/"
done
printf '\n.env\n.env.*\n.git\n__pycache__\n' >> "$app_dir/.dockerignore"
cd "$app_dir"
chmod 644 ./*.py Dockerfile requirements.txt update-jupiter.sh
find templates static -type d -exec chmod 755 {} +
find templates static -type f -exec chmod 644 {} +
docker build -t document-desk:local .
# Preserve the actual running configuration, including credentials, paths,
# security options, ports and the WebUI label; do not reconstruct it from .env.
docker run --rm -i \
 -v /var/run/docker.sock:/var/run/docker.sock \
 -v "$config_backup:/previous.json:ro" \
 python:3.12-slim python - <<'PY'
import socket,http.client,json
from copy import deepcopy
class Docker(http.client.HTTPConnection):
 def __init__(self):super().__init__('localhost',timeout=60)
 def connect(self):
  self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
  self.sock.connect('/var/run/docker.sock')
def request(method,path,body=None):
 c=Docker()
 try:
  payload=json.dumps(body).encode() if body is not None else None
  c.request(method,path,payload,{'Content-Type':'application/json'} if payload else {})
  r=c.getresponse();r.read()
  if r.status not in [200,201,204]:raise RuntimeError('Docker '+method+' failed: HTTP '+str(r.status))
 finally:c.close()
with open('/previous.json') as f:old=json.load(f)[0]
if old['HostConfig']['NetworkMode']!='bridge':raise RuntimeError('Unexpected network; stopping for review')
config=deepcopy(old['Config']);config['Image']='document-desk:local'
config['Labels']=dict(config.get('Labels') or {})
config['Labels'].update({'net.unraid.docker.managed':'dockerman','net.unraid.docker.webui':'http://[IP]:[PORT:8080]/','net.unraid.docker.icon':'http://<server-ip>:8092/static/icons/document-desk.png'})
config['HostConfig']=deepcopy(old['HostConfig'])
request('POST','/containers/create?name=document-desk',config)
request('POST','/containers/document-desk/start')
PY
ready=0
for attempt in {1..30}; do
 if curl -fsS --max-time 2 http://127.0.0.1:8092/ >/dev/null; then ready=1; break; fi
 sleep 1
done
if [[ "$ready" != 1 ]]; then echo 'The updated app did not answer.'; false; fi
trap - ERR INT TERM
docker rm "$old_name" >/dev/null
bash "$app_dir/install-icons.sh" || echo "App updated, but Docker icons need another attempt: bash $app_dir/install-icons.sh"
echo 'Release 2 installed: http://<server-ip>:8092/'
echo "Configuration and state backup: $backup_dir/document-desk-$stamp.tar.gz"
echo 'WebUI link and runtime settings preserved. Refresh the browser to load the new controls.'
