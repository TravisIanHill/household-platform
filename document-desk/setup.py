import getpass, secrets, hashlib, os
from pathlib import Path
p=Path('.env')
if p.exists():raise SystemExit('.env already exists; preserving credentials.')
a=getpass.getpass('Household password (12+ characters): ')
if len(a)<12:raise SystemExit('Use at least 12 characters.')
if a!=getpass.getpass('Repeat password: '):raise SystemExit('Passwords differ.')
salt=secrets.token_hex(16);key=hashlib.scrypt(a.encode(),salt=salt.encode(),n=32768,r=8,p=1,maxmem=128*1024*1024).hex()
# Compose interpolates dollar signs; double them to preserve Werkzeug hash separators.
value=f'scrypt:32768:8:1${salt}${key}'.replace('$','$$')
fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as f:f.write(f'SESSION_SECRET={secrets.token_hex(32)}\nPASSWORD_HASH={value}\n')
print('Credentials created. Start the container using the README instructions.')
