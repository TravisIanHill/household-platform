#!/usr/bin/env python3
import os, json, sqlite3, threading, hashlib, uuid, subprocess, sys, secrets, webbrowser
from pathlib import Path
from contextlib import contextmanager
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
ROOT=Path(os.getenv('CATALOG_HOME',str(Path.home()/'Library/Application Support/FamilyDriveCatalog')))
ROOT.mkdir(parents=True,exist_ok=True);os.chmod(ROOT,0o700)
TOKEN=secrets.token_urlsafe(32);LOCK=threading.Lock();JOB={'running':False};STOP=threading.Event()
@contextmanager
def db():
 c=sqlite3.connect(ROOT/'catalog.sqlite',timeout=30);c.row_factory=sqlite3.Row
 try:
  with c:
   yield c
 finally:
  c.close()
with db() as c:
 c.executescript('PRAGMA journal_mode=WAL; CREATE TABLE IF NOT EXISTS scans(id TEXT PRIMARY KEY,label TEXT,root TEXT,volume TEXT,started TEXT,status TEXT,hashed INTEGER); CREATE TABLE IF NOT EXISTS files(scan TEXT,path TEXT,name TEXT,ext TEXT,size INTEGER,modified INTEGER,category TEXT,hash TEXT,error TEXT,kind TEXT); CREATE INDEX IF NOT EXISTS hashes ON files(hash);')
 c.execute("UPDATE scans SET status='interrupted' WHERE status='running'")
def volumes():
 p=Path('/Volumes');out=[]
 if p.exists():
  for v in sorted(p.iterdir()):
   if v.is_dir() and not v.is_symlink():out.append(str(v))
 return out
def identity(p):
 if sys.platform=='darwin':
  try:
   import plistlib
   d=plistlib.loads(subprocess.check_output(['diskutil','info','-plist',str(p)],timeout=10));return d.get('VolumeUUID') or d.get('DiskUUID') or 'unavailable'
  except Exception:return 'unavailable'
 return 'unavailable'
def category(ext,name):
 if name=='.DS_Store':return 'macOS metadata'
 if name.startswith('._'):return 'Mac companion metadata — review'
 if ext in ['.exe','.msi','.iso','.dll']:return 'Software cleanup — review'
 if ext in ['.jpg','.jpeg','.png','.heic','.tif','.tiff','.raw','.cr2','.nef','.webp']:return 'Photo'
 if ext in ['.mov','.mp4','.m4v','.avi','.mkv']:return 'Video'
 if ext in ['.url','.webloc','.html','.htm']:return 'Saved link / HTML'
 if ext in ['.pdf','.docx','.doc','.xlsx','.xls','.txt','.eml','.msg','.csv']:return 'Document'
 return 'Other — review'
def scan(path,hashed,label):
 import datetime
 sid=uuid.uuid4().hex;volume=identity(path);count=0;total=0;errors=0
 with db() as c:c.execute('INSERT INTO scans VALUES(?,?,?,?,?,?,?)',(sid,label,str(path),volume,datetime.datetime.now().isoformat(),'running',int(hashed)))
 JOB.update(id=sid,count=0,bytes=0,errors=0,current='',status='running')
 try:
  with db() as c:
   def walkerror(err):
    nonlocal errors
    errors+=1;c.execute('INSERT INTO files VALUES(?,?,?,?,?,?,?,?,?,?)',(sid,str(getattr(err,'filename','')), '', '',0,0,'Unreadable',None,str(err),'directory'))
   for base,dirs,names in os.walk(path,followlinks=False,onerror=walkerror):
    if STOP.is_set():break
    dirs[:]=[d for d in dirs if not (Path(base)/d).is_symlink() and d not in ['.Spotlight-V100','.fseventsd','.Trashes']]
    for name in names:
     if STOP.is_set():break
     p=Path(base)/name;digest=None;error='';size=0;mtime=0;kind='file'
     JOB['current']=str(p.relative_to(path))
     try:
      before=p.lstat();size=before.st_size;mtime=before.st_mtime_ns
      if p.is_symlink():kind='symlink';error='Symlink cataloged; target not followed'
      elif not p.is_file():kind='special';error='Special file not read'
      elif hashed:
       h=hashlib.sha256()
       with p.open('rb') as f:
        while True:
         if STOP.is_set():raise InterruptedError('Hash canceled')
         b=f.read(4*1024*1024)
         if not b:break
         h.update(b)
       after=p.stat()
       if (before.st_size,before.st_mtime_ns,before.st_ino)!=(after.st_size,after.st_mtime_ns,after.st_ino):error='File changed during scan; hash discarded'
       else:digest=h.hexdigest()
     except Exception as ex:error=str(ex)
     ext=p.suffix.lower();c.execute('INSERT INTO files VALUES(?,?,?,?,?,?,?,?,?,?)',(sid,str(p.relative_to(path)),name,ext,size,mtime,category(ext,name),digest,error,kind))
     count+=1;total+=size;errors+=bool(error);JOB.update(count=count,bytes=total,errors=errors)
     if count%100==0:c.commit()
   status='canceled' if STOP.is_set() else 'complete';c.execute('UPDATE scans SET status=? WHERE id=?',(status,sid));c.commit();JOB['status']=status
 except Exception as ex:
  JOB.update(status='failed',error=str(ex))
  with db() as c:c.execute("UPDATE scans SET status='failed' WHERE id=?",(sid,))
 finally:JOB['running']=False
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def reply(self,data,status=200,mime='application/json'):
  b=data.encode() if isinstance(data,str) else json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; base-uri 'none'; frame-ancestors 'none'");self.end_headers();self.wfile.write(b)
 def do_GET(self):
  if self.headers.get('Host') not in [f'127.0.0.1:{PORT}',f'localhost:{PORT}']:return self.reply({'error':'Invalid host'},403)
  u=urlparse(self.path);q=parse_qs(u.query)
  if u.path=='/':return self.reply((Path(__file__).parent/'index.html').read_text().replace('TOKEN_VALUE',TOKEN),mime='text/html; charset=utf-8')
  if u.path in ['/app.js','/style.css']:return self.reply((Path(__file__).parent/u.path[1:]).read_text(),mime='text/javascript' if u.path.endswith('.js') else 'text/css')
  if self.headers.get('X-Catalog-Token')!=TOKEN:return self.reply({'error':'Unauthorized'},403)
  with db() as c:
   if u.path=='/api/state':return self.reply({'volumes':volumes(),'job':JOB.copy(),'scans':[dict(r) for r in c.execute('SELECT * FROM scans ORDER BY started DESC')]})
   if u.path in ['/api/files','/api/export']:
    sid=q.get('scan',[''])[0];s=c.execute('SELECT * FROM scans WHERE id=?',(sid,)).fetchone()
    if not s:return self.reply({'error':'Scan not found'},404)
    # Use latest scan per known volume; unknown IDs remain separate sources. Same drive rescans are not independent copies.
    sql="""SELECT f.*, CASE WHEN f.hash IS NULL THEN 'Not verified' WHEN EXISTS(SELECT 1 FROM files g JOIN scans gs ON gs.id=g.scan JOIN scans fs ON fs.id=f.scan WHERE g.hash=f.hash AND g.kind='file' AND (g.scan!=f.scan OR g.path!=f.path) AND (g.scan=f.scan OR gs.volume='unavailable' OR fs.volume='unavailable' OR gs.volume!=fs.volume) AND gs.id=(SELECT s2.id FROM scans s2 WHERE (s2.volume=gs.volume AND gs.volume!='unavailable') OR (s2.id=gs.id AND gs.volume='unavailable') ORDER BY s2.started DESC LIMIT 1)) THEN 'Exact duplicate in catalog' ELSE 'Unique among hashed catalog entries' END AS duplicate FROM files f WHERE scan=?"""
    params=[sid]
    if u.path=='/api/files':
     sql+=' AND (name LIKE ? OR path LIKE ?)';term='%'+q.get('q',[''])[0]+'%';params.extend([term,term]);sql+=' ORDER BY size DESC LIMIT 500'
    rows=[dict(r) for r in c.execute(sql,params)]
    return self.reply({'scan':dict(s),'files':rows,'note':'Historical catalog only. Locations and retained copies must be verified before deletion.'})
  self.reply({'error':'Not found'},404)
 def do_POST(self):
  if self.headers.get('Host') not in [f'127.0.0.1:{PORT}',f'localhost:{PORT}'] or self.headers.get('X-Catalog-Token')!=TOKEN:return self.reply({'error':'Unauthorized'},403)
  try:
   n=int(self.headers.get('Content-Length',0))
   if n>8192:return self.reply({'error':'Too large'},400)
   v=json.loads(self.rfile.read(n) or '{}')
   if self.path=='/api/cancel':STOP.set();return self.reply({'ok':True})
   if self.path=='/api/scan':
    with LOCK:
     if JOB.get('running'):return self.reply({'error':'A scan is already running'},409)
     p=Path(v['path']).resolve()
     if str(p) not in volumes():return self.reply({'error':'Select a mounted drive from the list'},400)
     STOP.clear();JOB.clear();JOB.update(running=True,status='starting');threading.Thread(target=scan,args=(p,bool(v.get('hash')),str(v.get('label') or p.name)[:100]),daemon=True).start()
    return self.reply({'ok':True})
  except Exception as ex:return self.reply({'error':str(ex)},400)
  self.reply({'error':'Not found'},404)
PORT=int(os.getenv('CATALOG_PORT','8765'))
if __name__=='__main__':
 server=ThreadingHTTPServer(('127.0.0.1',PORT),Handler);print(f'Catalog: http://127.0.0.1:{PORT}');print(f'Saved inventory: {ROOT}');webbrowser.open(f'http://127.0.0.1:{PORT}')
 try:server.serve_forever()
 except KeyboardInterrupt:STOP.set();server.shutdown()
