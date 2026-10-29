"""Release acceptance tests against Flask and temporary files; no live records."""
import tempfile,os,json,io,importlib.util,hashlib,sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash

def run():
 with tempfile.TemporaryDirectory() as tmp:
  os.environ.update(DOCUMENT_ROOT=tmp+'/docs',STATE_ROOT=tmp+'/state',SESSION_SECRET='fixture',PASSWORD_HASH=generate_password_hash('fixture-password'))
  Path(tmp+'/state').mkdir()
  with sqlite3.connect(tmp+'/state/desk.sqlite') as seed:
   seed.execute('CREATE TABLE settings (key TEXT PRIMARY KEY,data TEXT NOT NULL)')
   seed.execute('INSERT INTO settings VALUES (?,?)',('templates',json.dumps([dict(name='Birth Certificate',fields=['Person','Date of birth','Place of birth','Issuing state or country','Issuing authority','Date issued','Notes','Custom legacy detail'],required=['Person'],folder='Family_Records/Vital_Records/Birth_Certificates')])))
  spec=importlib.util.spec_from_file_location('release_app',Path(__file__).with_name('app.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  assert 'Custom legacy detail' in next(t for t in m.templates() if t['name']=='Birth Certificate')['fields']
  app=m.app;a=app.test_client();assert a.post('/login',data={'password':'fixture-password'}).status_code==302
  def h(c):
   with c.session_transaction() as s:return {'X-CSRF-Token':s['csrf']}
  ah=h(a);ids={}
  for username,role,adult in [('owner','admin',True),('parent','member',True),('kid','member',False),('sam','member',False)]:
   r=a.post('/api/users',headers=ah,json=dict(username=username,name=username,password='fixture-password',role=role,adult=adult));assert r.status_code==200,r.data;ids[username]=r.json['id']
  clients={}
  for name in ids:
   c=app.test_client();assert c.post('/login',data={'username':name,'password':'fixture-password'}).status_code==302;clients[name]=c
  a=clients['owner'];ah=h(a);sh=clients['parent'];lh=h(clients['kid'])
  for name in ids:assert a.put('/api/people/'+name,headers=ah,json=dict(name=name.title(),user_id=ids[name],aliases=['Sam Example'] if name=='sam' else [])).status_code==200
  assert sh.get('/intake').status_code==403
  assert sh.get('/api/users').status_code==403
  assert sh.get('/').status_code==200
  assert b'finder.js' in sh.get('/').data
  assert sh.post('/api/batches',headers=h(sh),json=dict(kind='folder',files=[dict(name='a.txt',size=1,path='folder/a.txt')])).status_code==403
  assert sh.post('/api/batches',headers=h(sh),json=dict(files=[dict(name='a.txt',size=1)]*26)).status_code==400
  assert sh.post('/api/batches',headers=h(sh),json=dict(files=[dict(name='a.txt',size=101*1024*1024)])).status_code==413
  assert sh.post('/api/upload',headers=h(sh),data={'file':(io.BytesIO(b'hello'),'a.txt')}).status_code==400
  def upload(c,name,payload):
   batch=c.post('/api/batches',headers=h(c),json=dict(files=[dict(name=name,size=len(payload),path=name)])).json
   r=c.post('/api/upload',headers=h(c),data=dict(file=(io.BytesIO(payload),name),batch_id=batch['id'],file_key='0',relative_path=name));assert r.status_code==200,r.data
   assert c.post('/api/batches/'+batch['id']+'/finish',headers=h(c),json={}).json['status']=='completed'
   return r.json
  d=upload(a,'birth.txt',b'BIRTH CERTIFICATE\nFULL NAME\nSAM EXAMPLE SAMPLE\nSTATE OF OREGON\nDATE OF BIRTH JANUARY 01, 2010\nDATE ISSUED JANUARY 15, 2010')
  did=d['id'];url='/api/docs/'+did
  r=a.post(url+'/suggest',headers=ah,json={});assert r.status_code==200;r=r.json
  assert r['fields']['State or territory']['value']=='Oregon',r
  assert r['fields']['Date of birth']['value']=='2010-01-01',r
  assert r['person_ids']==['sam']
  assert 'Issuing agency—as printed' not in r['fields']
  # Suggestions never save or overwrite metadata.
  assert m.getdoc(did)['type']=='Unclassified'
  assert a.put(url,headers=ah,json=dict(type='Birth Certificate',fields={'Person':'Sam','Issuing state or country':'HENNEPIN','Date of birth':'2010-01-01'},folder='Family_Records/Vital_Records/Birth_Certificates')).status_code==200
  assert a.put(url+'/organization',headers=ah,json=dict(person_ids=['sam'],visibility='inherit')).status_code==200
  rule=dict(kind='folder',target='Family_Records/Vital_Records',permission='view',adults=True,person_owners=True,user_ids=[])
  assert a.put('/api/policies',headers=ah,json={'policies':[rule]}).status_code==200
  assert a.post(url+'/approve',headers=ah,json={}).status_code==200
  orig=Path(tmp)/'docs'/m.getdoc(did)['path'];digest=hashlib.sha256(orig.read_bytes()).hexdigest()
  # Adult can view all linked vital records; ordinary member only their own.
  assert sh.get(url+'/original').status_code==200
  assert clients['sam'].get(url+'/original').status_code==200
  assert clients['kid'].get(url+'/original').status_code==404
  assert not clients['kid'].get('/api/state').json['docs']
  assert sh.put(url,headers=h(sh),json=dict(fields={'Person':'Wrong'})).status_code==403
  assert sh.put(url+'/organization',headers=h(sh),json=dict(visibility='household')).status_code==403
  assert clients['kid'].get(url+'/note').status_code==404
  # Edit filed details and retain legacy values; sync portable sidecars and audit.
  current=m.getdoc(did);fields=dict(current['fields'],**{'State or territory':'Oregon','Country':'United States'})
  r=a.put(url,headers=ah,json=dict(version=current['version'],fields=fields));assert r.status_code==200,r.data
  assert r.json['fields']['Issuing state or country']=='HENNEPIN'
  assert r.json['history'][-1]['changes']['fields']['after']['Country']=='United States'
  assert json.loads((orig.parent/'record.json').read_text())['fields']['Country']=='United States'
  assert hashlib.sha256(orig.read_bytes()).hexdigest()==digest
  assert a.put(url,headers=ah,json=dict(version=current['version'],fields=fields)).status_code==409
  assert a.put(url,headers=ah,json=dict(fields=dict(fields,**{'State or territory':'Hennepin'}))).status_code==400
  # Private beats inherited rules. Explicit selected sharing grants view only.
  assert a.put(url+'/organization',headers=ah,json=dict(visibility='private')).status_code==200
  assert sh.get(url+'/original').status_code==404
  assert clients['sam'].get(url+'/original').status_code==404
  assert a.put(url+'/organization',headers=ah,json=dict(visibility='selected',shared_user_ids=[ids['parent']])).status_code==200
  assert sh.get(url+'/note').status_code==200
  assert clients['sam'].get(url+'/note').status_code==404
  # Household documents are view-only for nonowners. Inherited edit grants cannot reshare.
  assert a.put(url+'/organization',headers=ah,json=dict(visibility='inherit')).status_code==200
  rule['permission']='edit';a.put('/api/policies',headers=ah,json={'policies':[rule]})
  assert sh.put(url,headers=h(sh),json=dict(fields=fields)).status_code==200
  assert sh.put(url,headers=h(sh),json=dict(folder='other')).status_code==403
  assert sh.put(url+'/organization',headers=h(sh),json=dict(visibility='household')).status_code==403
  # Actual bytes must match manifest; another account cannot use a batch.
  b=sh.post('/api/batches',headers=h(sh),json=dict(files=[dict(name='manifest.txt',size=1,path='manifest.txt')])).json
  assert sh.post('/api/upload',headers=h(sh),data=dict(file=(io.BytesIO(b'too long'),'manifest.txt'),batch_id=b['id'],file_key='0',relative_path='manifest.txt')).status_code==400
  assert clients['kid'].post('/api/upload',headers=lh,data=dict(file=(io.BytesIO(b'x'),'manifest.txt'),batch_id=b['id'],file_key='0',relative_path='manifest.txt')).status_code==403
  assert len(sh.get('/api/batches').json['batches'])==1
  assert a.get('/api/batches').json['batches'][0]['items']
  print('PASS: typed birth fields, conservative suggestions, legacy retention, archived edits/audit/original preservation, adult/person inheritance, private override, view-only and selected sharing, forbidden edit/reshare/download/search, admin-only intake, batch size/count/path/ownership/byte enforcement, persistent import history, Finder page')
if __name__=='__main__':run()
