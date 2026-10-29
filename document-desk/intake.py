"""Persistent batch manifests, byte budgets and source history."""
import json,uuid
from pathlib import Path
from flask import request,jsonify,abort,g

def register(app,db,stamp):
    hh=app.extensions['household']
    with db() as c:c.execute('CREATE TABLE IF NOT EXISTS batches (id TEXT PRIMARY KEY,data TEXT NOT NULL)')
    @app.post('/api/batches')
    def create():
        u=hh['user']();v=request.get_json() or {};files=v.get('files',[]);kind=v.get('kind','files');is_admin=u['role']=='admin'
        if kind not in ('files','folder') or (kind=='folder' and not is_admin):abort(403)
        if not isinstance(files,list) or not 1<=len(files)<=(500 if is_admin else 25):return jsonify(error='Household uploads allow up to 25 files per batch; admins allow 500.'),400
        total=0;items=[]
        for i,f in enumerate(files):
            name=f.get('name');size=f.get('size');path=f.get('path',name)
            if not isinstance(name,str) or len(name)>500 or not isinstance(path,str) or len(path)>8192 or type(size)!=int or size<0:abort(400)
            if not is_admin and ('/' in path or '\\' in path or '/' in name or '\\' in name):return jsonify(error='Folder imports are administrator-only.'),403
            total+=size
            ext=Path(name).suffix.lower();limit=(512 if ext in app.config['MEDIA_EXTS'] else 40)*1024*1024
            reason='Unsupported format' if ext not in app.config['READERS'] else 'Over per-file limit' if size>limit else None
            items.append(dict(key=str(i),name=name,size=size,path=path,status='skipped' if reason else 'pending',error=reason))
        if not is_admin and total>100*1024*1024:return jsonify(error='Batch exceeds 100 MB.'),413
        source=str(v.get('source','')).strip()[:500] if is_admin else 'Individual files'
        b=dict(id=uuid.uuid4().hex,user_id=u['id'],user_name=u['name'],kind=kind,source=source or 'Unnamed source',created=stamp(),status='running',total_bytes=total,items=items)
        with db() as c:c.execute('INSERT INTO batches VALUES (?,?)',(b['id'],json.dumps(b)))
        return jsonify(b)
    def reserve(path,name,size):
        u=hh['user']();bid=request.form.get('batch_id');key=request.form.get('file_key')
        if not bid:
            if u['role']=='admin':return None
            return ('Start a batch before uploading.',400)
        with db() as c:
            c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT data FROM batches WHERE id=?',(bid,)).fetchone()
            if not r:return ('Batch not found.',404)
            b=json.loads(r[0])
            if b['user_id']!=u['id'] or b['status']!='running':return ('Batch is unavailable.',403)
            item=next((x for x in b['items'] if x['key']==key),None)
            if not item or item['status']!='pending' or size!=item['size'] or name!=item['name'] or path!=item['path']:return ('File does not match the batch manifest.',400)
            if u['role']!='admin' and ('/' in path or '\\' in path):return ('Folder imports are administrator-only.',403)
            item['status']='processing';c.execute('UPDATE batches SET data=? WHERE id=?',(json.dumps(b),bid))
        g.batch=(bid,key);return None
    @app.after_request
    def receipt(response):
        if not getattr(g,'batch',None):return response
        bid,key=g.batch
        with db() as c:
            c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT data FROM batches WHERE id=?',(bid,)).fetchone()
            b=json.loads(r[0]);item=next(x for x in b['items'] if x['key']==key)
            item['status']='added' if response.status_code==200 else 'duplicate' if response.status_code==409 else 'failed'
            if response.is_json:
                data=response.get_json();item['document_id']=data.get('id');item['error']=data.get('error') if response.status_code!=409 else 'Already present'
            c.execute('UPDATE batches SET data=? WHERE id=?',(json.dumps(b),bid))
        return response
    @app.post('/api/batches/<id>/finish')
    def finish(id):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT data FROM batches WHERE id=?',(id,)).fetchone()
            if not r:abort(404)
            b=json.loads(r[0])
            if b['user_id']!=hh['user']()['id']:abort(403)
            b['status']='stopped' if any(x['status'] in ('pending','processing') for x in b['items']) else 'completed';b['finished']=stamp()
            c.execute('UPDATE batches SET data=? WHERE id=?',(json.dumps(b),id))
        return jsonify(b)
    @app.get('/api/batches')
    def history():
        u=hh['user']()
        with db() as c:rows=[json.loads(r[0]) for r in c.execute('SELECT data FROM batches')]
        return jsonify(batches=sorted([b for b in rows if u['role']=='admin' or b['user_id']==u['id']],key=lambda b:b['created'],reverse=True))
    app.extensions['intake_reserve']=reserve
