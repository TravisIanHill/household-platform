"""Household accounts, people, inherited access and organization."""
import json,re,uuid
from flask import request,session,jsonify,abort
from werkzeug.security import generate_password_hash
from access import permission

def register(app,db,stamp,getdoc,save,folder_path):
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, username TEXT UNIQUE COLLATE NOCASE, name TEXT, password TEXT, role TEXT, active INTEGER DEFAULT 1)')
        if 'adult' not in [r[1] for r in c.execute('PRAGMA table_info(users)')]:c.execute('ALTER TABLE users ADD COLUMN adult INTEGER NOT NULL DEFAULT 0')
        c.execute('CREATE TABLE IF NOT EXISTS people (id TEXT PRIMARY KEY,data TEXT NOT NULL)')
        for name in ['Owner','Parent','Kid','Sam']:
            if not c.execute('SELECT 1 FROM people WHERE id=?',(name.lower(),)).fetchone():c.execute('INSERT INTO people VALUES (?,?)',(name.lower(),json.dumps(dict(id=name.lower(),name=name,aliases=[],user_id=None))))
        c.execute('INSERT OR IGNORE INTO settings VALUES (?,?)',('organization',json.dumps(dict(folders=['Medical','Media/Pictures','Media/Music'],tags=[],collections=[]))))
        c.execute('INSERT OR IGNORE INTO settings VALUES (?,?)',('access_policies','[]'))
        if not c.execute("SELECT 1 FROM settings WHERE key='release2_vital_policy'").fetchone():
            rules=json.loads(c.execute("SELECT data FROM settings WHERE key='access_policies'").fetchone()[0])
            rules.append(dict(kind='folder',target='Family_Records/Vital_Records',permission='view',adults=True,person_owners=True,user_ids=[]))
            c.execute("UPDATE settings SET data=? WHERE key='access_policies'",(json.dumps(rules),))
            c.execute('INSERT INTO settings VALUES (?,?)',('release2_vital_policy','true'))

    def user():
        if session.get('user_id'):
            with db() as c:r=c.execute('SELECT id,username,name,role,adult FROM users WHERE id=? AND active=1',(session['user_id'],)).fetchone()
            return dict(r) if r else None
        if session.get('signed_in'):return dict(id='legacy',username='household',name='Household administrator',role='admin',adult=True)
    def admin():
        u=user()
        if not u or u['role']!='admin':abort(403)
        return u
    def people():
        with db() as c:return [json.loads(r[0]) for r in c.execute('SELECT data FROM people')]
    def policies():
        with db() as c:return json.loads(c.execute("SELECT data FROM settings WHERE key='access_policies'").fetchone()[0])
    def allowed(d):return permission(d,user(),people(),policies())
    def visible(d):return bool(allowed(d))
    def organization():
        with db() as c:return json.loads(c.execute("SELECT data FROM settings WHERE key='organization'").fetchone()[0])
    def labels(values):
        if not isinstance(values,list) or len(values)>40 or any(not isinstance(x,str) or not x.strip() or len(x)>100 for x in values):abort(400)
        return list(dict.fromkeys(x.strip() for x in values))
    @app.before_request
    def access():
        if request.path=='/login' or request.path.startswith('/static/'):return
        u=user()
        if not u:session.clear();abort(401)
        if request.path.startswith('/api/docs/'):
            d=getdoc(request.path.split('/')[3]);right=allowed(d)
            if not right:abort(404)
            if request.method in ('PUT','POST','DELETE') and not request.path.endswith('/suggest') and right!='edit':abort(403)
        if request.path in ('/catalog','/intake','/api/templates') or request.path.startswith('/api/catalog'):admin()
    @app.route('/api/users',methods=['GET','POST'])
    def users():
        admin()
        if request.method=='GET':
            with db() as c:return jsonify(users=[dict(r) for r in c.execute('SELECT id,username,name,role,active,adult FROM users ORDER BY name')])
        v=request.get_json() or {};username=str(v.get('username','')).strip().lower();password=v.get('password','');role=v.get('role','member');name=str(v.get('name','')).strip()[:100]
        if not re.fullmatch(r'[a-z0-9._-]{2,40}',username) or not isinstance(password,str) or len(password)<12 or role not in ('admin','member'):return jsonify(error='Use a 2–40 character username and a password of at least 12 characters.'),400
        with db() as c:
            if c.execute('SELECT 1 FROM users WHERE username=?',(username,)).fetchone():return jsonify(error='That username exists.'),409
            id=uuid.uuid4().hex;c.execute('INSERT INTO users VALUES (?,?,?,?,?,1,?)',(id,username,name or username,generate_password_hash(password),role,int(bool(v.get('adult')))))
        return jsonify(id=id,username=username,name=name or username,role=role)
    @app.put('/api/users/<id>')
    def update_user(id):
        me=admin();v=request.get_json() or {}
        with db() as c:
            old=c.execute('SELECT * FROM users WHERE id=?',(id,)).fetchone()
            if not old:abort(404)
            active=int(bool(v.get('active',old['active'])));role=v.get('role',old['role'])
            if role not in ('member','admin'):abort(400)
            if id==me['id'] and (not active or role!='admin'):return jsonify(error='Keep your own administrator account active.'),400
            if old['role']=='admin' and (not active or role!='admin') and c.execute("SELECT count(*) FROM users WHERE role='admin' AND active=1").fetchone()[0]<=1:abort(400)
            if 'password' in v:
                if not isinstance(v['password'],str) or len(v['password'])<12:abort(400)
                c.execute('UPDATE users SET password=? WHERE id=?',(generate_password_hash(v['password']),id))
            c.execute('UPDATE users SET active=?,role=?,adult=? WHERE id=?',(active,role,int(bool(v.get('adult',old['adult']))),id))
        return jsonify(ok=True)
    @app.get('/api/people')
    def people_list():return jsonify(people=people())
    @app.put('/api/people/<id>')
    def update_person(id):
        admin();v=request.get_json() or {};name=str(v.get('name','')).strip()[:100];uid=v.get('user_id') or None
        if not name:abort(400)
        with db() as c:
            if uid and not c.execute('SELECT 1 FROM users WHERE id=?',(uid,)).fetchone():abort(400)
            p=dict(id=id,name=name,aliases=labels(v.get('aliases',[])),user_id=uid)
            c.execute('INSERT OR REPLACE INTO people VALUES (?,?)',(id,json.dumps(p)))
        return jsonify(p)
    @app.route('/api/policies',methods=['GET','PUT'])
    def access_rules():
        admin()
        if request.method=='GET':return jsonify(policies=policies())
        rows=(request.get_json() or {}).get('policies',[])
        if not isinstance(rows,list) or len(rows)>100:abort(400)
        clean=[]
        for r in rows:
            if r.get('kind') not in ('folder','collection') or r.get('permission') not in ('view','edit'):abort(400)
            target=folder_path(r.get('target','')) if r['kind']=='folder' else str(r.get('target','')).strip()[:100]
            if not target:abort(400)
            clean.append(dict(kind=r['kind'],target=target,permission=r['permission'],adults=bool(r.get('adults')),person_owners=bool(r.get('person_owners')),user_ids=labels(r.get('user_ids',[]))))
        with db() as c:c.execute("UPDATE settings SET data=? WHERE key='access_policies'",(json.dumps(clean),))
        return jsonify(policies=clean)
    @app.post('/api/organization')
    def organize():
        admin();v=request.get_json() or {};kind=v.get('kind');name=str(v.get('name','')).strip()
        if kind not in ('folders','tags','collections') or not name or len(name)>200:abort(400)
        if kind=='folders':name=folder_path(name)
        o=organization();o[kind]=sorted(set(o[kind]+[name]),key=str.casefold)
        with db() as c:c.execute("UPDATE settings SET data=? WHERE key='organization'",(json.dumps(o),))
        return jsonify(o)
    @app.put('/api/docs/<id>/organization')
    def organize_doc(id):
        d=getdoc(id);d['_expected_version']=d.get('version',0);v=request.get_json() or {};u=user();visibility=v.get('visibility',d.get('visibility','household'))
        if visibility not in ('private','household','inherit','personal_adults','selected'):abort(400)
        if u['role']!='admin' and d.get('owner_id')!=u['id']:return jsonify(error='Only the owner or administrator can change organization and sharing.'),403
        d.update(folder=folder_path(v.get('folder',d.get('folder','unclassified'))),tags=labels(v.get('tags',d.get('tags',[]))),collections=labels(v.get('collections',d.get('collections',[]))),visibility=visibility)
        if 'person_ids' in v:
            ids=labels(v['person_ids']);valid={p['id'] for p in people()}
            if not set(ids)<=valid:abort(400)
            d['person_ids']=ids
        if 'shared_user_ids' in v:
            # Administrator-only user picker; members cannot enumerate accounts.
            if u['role']!='admin':abort(403)
            ids=labels(v['shared_user_ids'])
            with db() as c:valid={r[0] for r in c.execute('SELECT id FROM users WHERE active=1')}
            if not set(ids)<=valid:abort(400)
            d['shared_user_ids']=ids
        d['history'].append({'at':stamp(),'action':'Organization and sharing updated by '+u['name']});save(d)
        return jsonify(d)
    app.extensions['household']=dict(user=user,admin=admin,visible=visible,organization=organization,permission=allowed,people=people,policies=policies)
