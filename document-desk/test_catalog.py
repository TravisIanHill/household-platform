import tempfile,os,io,json,sys,importlib.util
from pathlib import Path
from werkzeug.security import generate_password_hash
sys.path.insert(0,str(Path(__file__).resolve().parent))
with tempfile.TemporaryDirectory() as tmp:
 os.environ.update(DOCUMENT_ROOT=tmp+'/docs',STATE_ROOT=tmp+'/state',SESSION_SECRET='test',PASSWORD_HASH=generate_password_hash('test'))
 os.environ['NETWORK_MOUNT_ROOT']=tmp+'/source'
 Path(tmp+'/source').mkdir()
 import app as m
 c=m.app.test_client();assert c.get('/api/catalog').status_code==401
 c.post('/login',data={'password':'test'})
 with c.session_transaction() as s:h={'X-CSRF-Token':s['csrf']}
 def ingest(root,files):
  return c.post('/api/catalog/import',headers=h,data={'file':(io.BytesIO(json.dumps({'scan':{'root':root,'label':root,'volume':root,'status':'complete'},'files':files}).encode()),'catalog.json')})
 def f(path,hash='a'*64,error=''):return dict(path=path,size=30,hash=hash,error=error,kind='file')
 assert ingest('/drive1',[f('photo.jpg'),f('unknown.blob',''),f('failed.pdf','a'*64,'read error')]).status_code==200
 assert ingest('/drive2',[f('copy.jpg')]).status_code==200
 state=c.get('/api/catalog').json;assert state['total']==4
 photo=next(r for r in state['rows'] if r['path']=='photo.jpg');copy=next(r for r in state['rows'] if r['path']=='copy.jpg');unknown=next(r for r in state['rows'] if r['path']=='unknown.blob')
 assert photo['copies']==2 and photo['family']=='Images & photos'
 def decision(id,value):return c.put('/api/catalog/files/'+id,headers=h,json={'decision':value})
 assert decision(unknown['id'],'duplicate').status_code==400
 assert decision(photo['id'],'duplicate').status_code==200
 assert decision(copy['id'],'duplicate').status_code==400
 selected=c.get('/api/catalog?selected='+photo['id']).json;assert len(selected['copies'])==2
 assert ingest('/drive1',[f('photo.jpg'),f('unknown.blob',''),f('failed.pdf','a'*64,'read error')]).status_code==200
 assert c.get('/api/catalog').json['total']==4
 assert next(r for r in c.get('/api/catalog').json['rows'] if r['id']==photo['id'])['decision']=='duplicate'
 plan=c.get('/api/catalog/export').json;assert next(r for r in plan['files'] if r['id']==photo['id'])['retained_copy_locations'][0]['path']=='copy.jpg'
 assert ingest('/bad',[f('../escape.jpg')]).status_code==400
 assert c.get('/api/catalog').json['total']==4
 assert ingest('/drive2',[f('copy.jpg','b'*64)]).status_code==200
 assert next(r for r in c.get('/api/catalog').json['rows'] if r['id']==photo['id'])['decision']=='keep'
 assert c.get('/catalog').status_code==200
 assert m.archive_folder('taxes/2024')=='taxes/2024'
 assert c.get('/').headers['X-Frame-Options']=='SAMEORIGIN'
 d=c.post('/api/upload',headers=h,data={'file':(io.BytesIO(b'test tax'),'tax.txt')}).json
 c.put('/api/templates',headers=h,json={'name':'Tax','fields':['Year'],'folder':'taxes/2024','required':['Year']})
 c.put('/api/docs/'+d['id'],headers=h,json={'type':'Tax','fields':{'Year':'2024'},'folder':'taxes/2024'})
 r=c.post('/api/docs/'+d['id']+'/approve',headers=h,json={});assert r.status_code==200,r.data
 assert '/taxes/2024/' in r.json['path']
 # Original catalog snapshots persist separately from refreshed inventory.
 snapshots=c.get('/api/catalog').json['snapshots'];assert snapshots
 raw=c.get('/api/catalog/snapshots/'+snapshots[0]['id']);assert raw.status_code==200
 assert 'scan' in json.loads(raw.data)
 assert c.get('/api/catalog/snapshots/../../etc/passwd').status_code==404
 # MOV is retained as media, rather than rejected or sent through OCR.
 movie=b'\x00\x00\x00\x18ftypqt  '+b'media-test'
 r=c.post('/api/upload',headers=h,data={'file':(io.BytesIO(movie),'test.mov'),'relative_path':'Family/test.mov'})
 assert r.status_code==200,r.data
 assert r.json['source_relative_path']=='Family/test.mov'
 assert c.get('/api/docs/'+r.json['id']+'/original').data==movie
 assert 'transcription' in r.json['text']
 # More than 500 network entries use multiple resumable steps without source writes.
 source=Path(tmp+'/source');(source/'photos').mkdir()
 for i in range(501):(source/'photos'/f'{i}.txt').write_text('source '+str(i))
 large=source/'photos'/'large.mov'
 with large.open('wb') as f:f.truncate(65*1024*1024)
 assert c.get('/api/network/folders').json['configured']
 assert c.post('/api/network/start',headers=h,json={'path':'../docs'}).status_code==400
 job=c.post('/api/network/start',headers=h,json={'path':'photos'}).json
 first=c.post('/api/network/jobs/'+job['id']+'/step',headers=h,json={})
 assert first.status_code==200,first.data
 assert first.json['done']==500 and not first.json['complete']
 pending=c.get('/api/network/folders').json['jobs'];assert pending[0]['done']==500
 second=c.post('/api/network/jobs/'+job['id']+'/step',headers=h,json={})
 assert second.json['complete'] and second.json['done']==502
 row=c.get('/api/catalog?q=large.mov').json['rows'][0]
 assert row['hash']=='' and row['decision']=='keep' and row['size']==65*1024*1024
 assert len(list((source/'photos').iterdir()))==502 and (source/'photos'/'0.txt').read_text()=='source 0'
 print('PASS: snapshots, media intake, source provenance, network confinement, 500-entry batches, resumable progress, deferred hashes, originals unchanged')
 print('PASS: authenticated import, classification, protected unknown/errors, duplicate evidence, retained-copy protection, reimport identity, invalid paths, stale recommendation reset, export, nested filing, preview frame policy')
