"""Exercise the actual backup/restore scripts with a Docker CLI stand-in, on fixtures."""
import tempfile,subprocess,sqlite3,json,hashlib,os,tarfile
from pathlib import Path

def run():
 with tempfile.TemporaryDirectory() as temp:
  root=Path(temp);app_root=root/'appdata';docs=root/'documents';backups=root/'backups';bin=root/'bin';bin.mkdir();(app_root/'app').mkdir(parents=True);(app_root/'state').mkdir();docs.mkdir()
  (app_root/'app/app.py').write_text('# fixture app');(app_root/'app/.env').write_text('SESSION_SECRET=fixture-only')
  content=b'fixture EOB balance 42';(docs/'original.txt').write_bytes(content)
  c=sqlite3.connect(app_root/'state/desk.sqlite');c.execute('CREATE TABLE docs (id TEXT,data TEXT)');c.execute('INSERT INTO docs VALUES (?,?)',('one',json.dumps(dict(id='one',path='original.txt',sha256=hashlib.sha256(content).hexdigest()))));c.commit();c.close()
  docker=bin/'docker';docker.write_text('''#!/usr/bin/env python3
import sys,os,subprocess,json
args=sys.argv[1:]
with open(os.environ['DOCKER_TEST_LOG'],'a') as log:log.write(args[0]+'\\n')
if args[0]=='inspect':print('true' if '--format' in args else '[{"Config":{"Env":["fixture-only"]}}]')
elif args[0] in ('stop','start'):pass
elif args[0]=='run':
 mounts=[args[i+1] for i,x in enumerate(args) if x=='-v'];mapping={v.split(':')[1]:v.split(':')[0] for v in mounts};code=sys.stdin.read()
 code=code.replace("Path('/restore')",'Path('+repr(mapping['/restore'])+')').replace("'/backup.tar.gz'",repr(mapping['/backup.tar.gz']))
 sys.exit(subprocess.run([sys.executable,'-c',code]).returncode)
else:sys.exit(2)
''');docker.chmod(0o755)
  env=dict(os.environ,PATH=str(bin)+':'+os.environ['PATH'],DOCKER_TEST_LOG=str(root/'docker.log'))
  source=Path(__file__).parent
  script=root/'backup.sh';script.write_text((source/'backup-jupiter.sh').read_text().replace('app_root=/mnt/user/appdata/document-desk','app_root='+str(app_root)).replace('documents=/mnt/user/documents/document-desk','documents='+str(docs)))
  result=subprocess.run(['bash',str(script),str(backups)],env=env,capture_output=True,text=True);assert result.returncode==0,result.stderr
  archive=next(backups.glob('household-*.tar.gz'))
  with tarfile.open(archive) as t:
   names=set(t.getnames());assert {'app/app.py','app/.env','state/desk.sqlite','documents/original.txt','runtime/container.json'}<=names,names
  result=subprocess.run(['bash',str(source/'restore-test.sh'),str(archive),str(root/'restore')],env=env,capture_output=True,text=True);assert result.returncode==0,result.stdout+result.stderr
  assert (root/'restore/documents/original.txt').read_bytes()==content
  assert 'start' in (root/'docker.log').read_text()
  archive.write_bytes(archive.read_bytes()+b'corruption')
  result=subprocess.run(['bash',str(source/'restore-test.sh'),str(archive),str(root/'badrestore')],env=env,capture_output=True,text=True);assert result.returncode!=0
  assert not (root/'badrestore').exists()
  print('PASS: full backup layout, app secrets/state/originals/config retained, restart, separate restore drill, original checksums, corrupt archive rejection. Docker operations simulated; filesystem/archive operations real.')
if __name__=='__main__':run()
