import os,tempfile,io,json,importlib.util
from pathlib import Path
from werkzeug.security import generate_password_hash

def run():
 with tempfile.TemporaryDirectory() as tmp:
  os.environ.update(DOCUMENT_ROOT=tmp+'/documents',STATE_ROOT=tmp+'/state',SESSION_SECRET='test-secret',PASSWORD_HASH=generate_password_hash('old-household-password'))
  spec=importlib.util.spec_from_file_location('desk_household_test',Path(__file__).with_name('app.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  app=m.app;admin=app.test_client();assert admin.post('/login',data={'password':'old-household-password'}).status_code==302
  def headers(c):
   with c.session_transaction() as s:return {'X-CSRF-Token':s['csrf']}
  ah=headers(admin)
  for name,role in [('owner','admin'),('member','member'),('other','member')]:
   r=admin.post('/api/users',headers=ah,json=dict(username=name,name=name,password='temporary-password',role=role));assert r.status_code==200,r.data
  assert app.test_client().post('/login',data={'password':'old-household-password'}).status_code==401
  assert admin.post('/login',data={'username':'owner','password':'temporary-password'}).status_code==302
  ah=headers(admin)
  member=app.test_client();other=app.test_client()
  for c,name in [(member,'member'),(other,'other')]:assert c.post('/login',data={'username':name,'password':'temporary-password'}).status_code==302
  mh=headers(member);oh=headers(other)
  assert member.get('/api/users').status_code==403
  assert member.get('/api/catalog/state').status_code==403
  assert member.put('/api/templates',headers=mh,json={}).status_code==403
  batch=member.post('/api/batches',headers=mh,json={'files':[{'name':'eob.txt','size':len(b'EOB member balance 42.00'),'path':'eob.txt'}]}).json
  r=member.post('/api/upload',headers=mh,data={'file':(io.BytesIO(b'EOB member balance 42.00'),'eob.txt'),'batch_id':batch['id'],'file_key':'0','relative_path':'eob.txt'});assert r.status_code==200,r.data
  d=r.json;id=d['id'];assert d['visibility']=='private'
  assert other.get('/api/state').json['docs']==[]
  assert other.get('/api/docs/'+id+'/original').status_code==404
  assert other.put('/api/docs/'+id+'/organization',headers=oh,json={}).status_code==404
  assert admin.get('/api/docs/'+id+'/original').status_code==200
  assert admin.post('/api/organization',headers=ah,json=dict(kind='folders',name='Medical/Insurance/EOBs')).status_code==200
  for invalid in ['../outside','Medical/../outside','/absolute','Medical//bad']:
   assert admin.post('/api/organization',headers=ah,json=dict(kind='folders',name=invalid)).status_code==400
  r=member.put('/api/docs/'+id+'/organization',headers=mh,json=dict(folder='Medical/Insurance/EOBs',tags=['2026 Taxes'],collections=['Camry Accident'],visibility='household'));assert r.status_code==200,r.data
  assert len(other.get('/api/state').json['docs'])==1
  assert other.put('/api/docs/'+id+'/organization',headers=oh,json=dict(visibility='private')).status_code==403
  # Unknown documents can be filed without creating a document type.
  r=member.post('/api/docs/'+id+'/approve',headers=mh,json={});assert r.status_code==200,r.data
  assert r.json['type']=='Unclassified' and r.json['status']=='archived'
  assert member.put('/api/docs/'+id+'/organization',headers=mh,json=dict(folder='Medical',tags=['2024 Taxes'],visibility='private')).status_code==200
  assert other.get('/api/docs/'+id+'/note').status_code==404
  assert member.get('/api/docs/'+id+'/original').data==b'EOB member balance 42.00'
  assert '2024 Taxes' in member.get('/api/state').json['docs'][0]['tags']
  # A disabled account loses an existing authenticated session.
  users=admin.get('/api/users').json['users'];uid=next(u['id'] for u in users if u['username']=='member')
  assert admin.put('/api/users/'+uid,headers=ah,json={'active':False}).status_code==200
  assert member.get('/api/state').status_code==401
  print('PASS: named accounts, legacy transition, role checks, private downloads/search, folder validation, tags/collections, unclassified filing, archived organization, disabled sessions')
if __name__=='__main__':run()
