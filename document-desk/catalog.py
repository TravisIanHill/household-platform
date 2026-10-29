"""Catalog metadata review only. Never reads, moves, or deletes source files."""
import hashlib, json, re, os, uuid
from pathlib import PurePosixPath, Path
from flask import request, jsonify, render_template, session, send_file

FAMILIES = {
 'Documents': '.pdf .doc .docx .xls .xlsx .csv .tsv .txt .rtf .pages .numbers .ppt .pptx .eml .msg .odt .ods',
 'Images & photos': '.jpg .jpeg .png .gif .tif .tiff .webp .heic .heif .raw .cr2 .nef .dng .bmp .psd',
 'Videos': '.mov .mp4 .m4v .mkv .avi .wmv .mts .m2ts .webm .mpg .mpeg .3gp',
 'Audio': '.mp3 .m4a .aac .wav .flac .aiff .ogg .wma .m4b',
 'Links & bookmarks': '.webloc .url .html .htm',
 'Backups & archives': '.zip .tar .gz .7z .rar .sparsebundle .backup .bak .vhd .vhdx .qcow2',
 'Software & system files': '.exe .msi .dmg .pkg .iso .dll .app .deb .rpm',
}
def family(f):
    name=f['name'].lower()
    if name.startswith('._') or name in ('.ds_store','thumbs.db','desktop.ini'):
        return 'Metadata — review'
    ext=PurePosixPath(name).suffix
    return next((k for k,v in FAMILIES.items() if ext in v.split()), 'Unknown — keep for review')

def register(app, db, stamp):
    snapshot_dir=Path(app.config['CATALOG_SNAPSHOT_DIR'])
    snapshot_dir.mkdir(parents=True,exist_ok=True)
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS catalog_snapshots (id TEXT PRIMARY KEY, name TEXT, source TEXT, created TEXT, entries INTEGER)')
        c.execute('CREATE TABLE IF NOT EXISTS catalog_sources (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS catalog_files (id TEXT PRIMARY KEY, source TEXT, path TEXT, family TEXT, hash TEXT, size INTEGER, error TEXT, decision TEXT, data TEXT)')
        c.execute('CREATE INDEX IF NOT EXISTS catalog_hash ON catalog_files(hash,size)')

    @app.get('/catalog')
    def page(): return render_template('catalog.html',csrf=session['csrf'])

    def import_bytes(raw,filename):
        try:
            payload=json.loads(raw.decode('utf-8-sig')) if raw else None
            if not isinstance(payload,dict): raise ValueError('Expected a catalog JSON object.')
            scan=payload.get('scan'); files=payload.get('files')
            if not isinstance(scan,dict) or not isinstance(files,list) or len(files)>500000:
                raise ValueError('Expected scan metadata and a files array (maximum 500,000 entries).')
            root=scan.get('root'); volume=scan.get('volume','')
            if not isinstance(root,str) or not root: raise ValueError('Catalog needs a source root.')
            source=hashlib.sha256(json.dumps([volume,root]).encode()).hexdigest()
            rows=[]; paths=set()
            for f in files:
                if not isinstance(f,dict): raise ValueError('Invalid file entry.')
                path=f.get('path'); size=f.get('size',0)
                if isinstance(path,str) and path.startswith(root.rstrip('/')+'/'):
                    path=path[len(root.rstrip('/'))+1:]
                if not isinstance(path,str) or not path or len(path)>8192 or path in paths:
                    raise ValueError('Invalid or repeated path in catalog.')
                if path.startswith('/') or '..' in PurePosixPath(path).parts:
                    raise ValueError('Paths must be relative to the catalog source.')
                if type(size)!=int or not 0<=size<=2**63-1: raise ValueError('Invalid file size.')
                paths.add(path); name=path.rsplit('/',1)[-1]
                error=str(f.get('error') or '')[:2000]
                digest=f.get('hash')
                valid=bool(isinstance(digest,str) and re.fullmatch('[a-fA-F0-9]{64}',digest) and not error and f.get('kind','file')=='file')
                item=dict(path=path,name=name,kind=str(f.get('kind','file')),modified=f.get('modified'),imported_category=str(f.get('category','')),imported_duplicate=str(f.get('duplicate','')))
                id=hashlib.sha256((source+'\0'+path).encode()).hexdigest()
                rows.append((id,source,path,family(item),digest.lower() if valid else '',size,error,'keep',json.dumps(item)))
            meta=dict(label=str(scan.get('label') or root)[:200],root=root,volume=volume,status=str(scan.get('status','unknown')),imported=stamp(),entries=len(rows))
            snapshot_id=hashlib.sha256(raw).hexdigest()
            snapshot_path=snapshot_dir/(snapshot_id+'.json')
            if not snapshot_path.exists():snapshot_path.write_bytes(raw)
            with db() as c:
                c.execute('INSERT OR IGNORE INTO catalog_snapshots VALUES (?,?,?,?,?)',(snapshot_id,str(filename or 'catalog.json')[:250],source,stamp(),len(rows)))
                # Reimport replaces inventory but preserves decisions only for unchanged content.
                previous={r['id']:(r['hash'],r['size'],r['decision']) for r in c.execute('SELECT id,hash,size,decision FROM catalog_files WHERE source=?',(source,))}
                rows=[r[:7]+((previous[r[0]][2] if r[4] and r[0] in previous and previous[r[0]][:2]==(r[4],r[5]) else 'keep'),)+r[8:] for r in rows]
                c.execute('DELETE FROM catalog_files WHERE source=?',(source,))
                c.executemany('INSERT INTO catalog_files VALUES (?,?,?,?,?,?,?,?,?)',rows)
                c.execute('INSERT OR REPLACE INTO catalog_sources VALUES (?,?)',(source,json.dumps(meta)))
                c.execute("UPDATE catalog_files SET decision='keep' WHERE decision='duplicate' AND NOT EXISTS (SELECT 1 FROM catalog_files AS other WHERE other.id!=catalog_files.id AND other.hash=catalog_files.hash AND other.size=catalog_files.size AND other.decision!='duplicate')")
            return jsonify(source=source,entries=len(rows))
        except (ValueError,TypeError,AttributeError,UnicodeError) as exc:
            return jsonify(error='Catalog could not be imported: '+str(exc)[:300]+'. No inventory changes made.'),400

    @app.post('/api/catalog/import')
    def ingest():
        upload=request.files.get('file')
        return import_bytes(upload.read() if upload else b'',upload.filename if upload else '')

    @app.get('/api/catalog/snapshots/<id>')
    def snapshot(id):
        if not re.fullmatch('[a-f0-9]{64}',id):return jsonify(error='Snapshot not found.'),404
        with db() as c:r=c.execute('SELECT name FROM catalog_snapshots WHERE id=?',(id,)).fetchone()
        if not r:return jsonify(error='Snapshot not found.'),404
        return send_file(snapshot_dir/(id+'.json'),as_attachment=True,download_name=r[0],mimetype='application/json')

    network_root=Path(os.getenv('NETWORK_MOUNT_ROOT','/sources')).resolve()
    jobs_dir=snapshot_dir.parent/'network-jobs'
    jobs_dir.mkdir(exist_ok=True)
    def network_path(relative):
        if not network_root.is_dir():raise ValueError('No network folder is mounted. Configure a read-only /sources mapping on Jupiter first.')
        path=(network_root/relative).resolve()
        if path!=network_root.resolve() and network_root.resolve() not in path.parents:raise ValueError('Folder is outside the configured source.')
        if not path.is_dir():raise ValueError('Folder not found.')
        return path

    @app.get('/api/network/folders')
    def folders():
        if not network_root.is_dir():return jsonify(configured=False,folders=[])
        try:
            relative=request.args.get('path','');path=network_path(relative)
            children=[str(p.relative_to(network_root)) for p in path.iterdir() if p.is_dir() and not p.is_symlink()][:1000]
            jobs=[]
            for file in jobs_dir.glob('*.json'):
                job=json.loads(file.read_text())
                if not job.get('complete'):jobs.append(dict(id=file.stem,folder=job['relative'],done=job['cursor'],total=len(job['paths'])))
            return jsonify(configured=True,path=relative,folders=sorted(children),jobs=jobs)
        except (ValueError,OSError) as exc:return jsonify(error=str(exc)),400

    @app.post('/api/network/start')
    def start_scan():
        try:
            relative=str((request.get_json(silent=True) or {}).get('path',''));root=network_path(relative)
            paths=[]
            def onerror(exc):paths.append(dict(path=str(Path(exc.filename).relative_to(root)),error=str(exc),kind='directory'))
            for directory,dirs,names in os.walk(root,followlinks=False,onerror=onerror):
                for name in dirs[:]:
                    p=Path(directory)/name
                    if p.is_symlink():paths.append(dict(path=str(p.relative_to(root)),error='Symbolic link retained for separate review.',kind='symlink'));dirs.remove(name)
                for name in names:paths.append(dict(path=str((Path(directory)/name).relative_to(root))))
                if len(paths)>100000:raise ValueError('Choose a smaller subfolder (maximum 100,000 entries per scan).')
            id=uuid.uuid4().hex
            job=dict(relative=relative,source_root=os.getenv('NETWORK_SOURCE_ROOT','/sources'),paths=paths,cursor=0,files=[],complete=False)
            (jobs_dir/(id+'.json')).write_text(json.dumps(job))
            return jsonify(id=id,total=len(paths))
        except (ValueError,OSError) as exc:return jsonify(error=str(exc)),400

    @app.post('/api/network/jobs/<id>/step')
    def scan_step(id):
        if not re.fullmatch('[a-f0-9]{32}',id) or not (jobs_dir/(id+'.json')).exists():return jsonify(error='Scan job not found.'),404
        file=jobs_dir/(id+'.json');job=json.loads(file.read_text())
        if job['complete']:return jsonify(done=job['cursor'],total=len(job['paths']),complete=True)
        try:root=network_path(job['relative'])
        except ValueError as exc:return jsonify(error=str(exc)),400
        read_bytes=0;processed=0
        while job['cursor']<len(job['paths']) and processed<500 and read_bytes<128*1024*1024:
            entry=job['paths'][job['cursor']];p=root/entry['path'];item=dict(entry,size=0,hash='',kind=entry.get('kind','file'))
            try:
                if entry.get('error'):raise ValueError(entry['error'])
                if p.is_symlink():raise ValueError('Symbolic link retained for separate review.')
                resolved=p.resolve()
                if root!=resolved and root not in resolved.parents:raise ValueError('Source path changed outside scan folder.')
                before=p.stat();item.update(size=before.st_size,modified=before.st_mtime_ns)
                if before.st_size>64*1024*1024:raise ValueError('Hash deferred: file exceeds 64 MB network first-pass limit. Keep for review.')
                digest=hashlib.sha256()
                with p.open('rb') as stream:
                    for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block);read_bytes+=len(block)
                after=p.stat()
                if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('File changed while hashing; keep for review.')
                item['hash']=digest.hexdigest()
            except (OSError,ValueError) as exc:item.update(error=str(exc),hash='')
            job['files'].append(item);job['cursor']+=1;processed+=1
        if job['cursor']==len(job['paths']):
            source_root=job['source_root'].rstrip('/')+('/'+job['relative'] if job['relative'] else '')
            payload=dict(scan=dict(root=source_root,volume=job['source_root'],label='Network: '+(job['relative'] or job['source_root']),status='complete'),files=job['files'])
            result=import_bytes(json.dumps(payload).encode(),'network-'+id+'.json')
            if isinstance(result,tuple):return result
            job['complete']=True
        file.write_text(json.dumps(job))
        return jsonify(done=job['cursor'],total=len(job['paths']),complete=job['complete'])

    def inventory():
        with db() as c:
            sources={r[0]:json.loads(r[1]) for r in c.execute('SELECT id,data FROM catalog_sources')}
            counts={(r[0],r[1]):r[2] for r in c.execute("SELECT hash,size,count(*) FROM catalog_files WHERE hash != '' GROUP BY hash,size HAVING count(*)>1")}
            rows=[]
            for r in c.execute('SELECT * FROM catalog_files'):
                item=dict(r); item.update(json.loads(item.pop('data')))
                item['copies']=counts.get((item['hash'],item['size']),1) if item['hash'] else 0
                item['assessment']='Exact duplicate candidate' if item['copies']>1 else ('Unique within imported catalogs' if item['hash'] else 'Unknown — keep for review')
                item['source_label']=sources[item['source']]['label']; rows.append(item)
            return sources,rows

    @app.get('/api/catalog')
    def listing():
        sources,rows=inventory(); stats={}
        for r in rows:
            s=stats.setdefault(r['family'],dict(count=0,bytes=0)); s['count']+=1;s['bytes']+=r['size']
        query=request.args.get('q','').lower(); group=request.args.get('family',''); assessment=request.args.get('assessment',''); source=request.args.get('source','')
        filtered=[r for r in rows if (not query or query in (r['path']+' '+r['source_label']).lower()) and (not group or group==r['family']) and (not assessment or assessment==r['assessment']) and (not source or source==r['source'])]
        offset=max(0,min(int(request.args.get('offset','0')) if request.args.get('offset','0').isdigit() else 0,len(filtered)))
        selected=request.args.get('selected',''); picked=next((r for r in rows if r['id']==selected),None)
        copies=[dict(id=r['id'],source_label=r['source_label'],root=sources[r['source']]['root'],path=r['path'],decision=r['decision']) for r in rows if picked and picked['hash'] and r['hash']==picked['hash'] and r['size']==picked['size']]
        with db() as c:snapshots=[dict(r) for r in c.execute('SELECT * FROM catalog_snapshots ORDER BY created DESC')]
        return jsonify(snapshots=snapshots,sources=sources,groups=stats,total=len(rows),matched=len(filtered),rows=filtered[offset:offset+100],offset=offset,selected=picked,copies=copies)

    @app.put('/api/catalog/files/<id>')
    def decision(id):
        value=(request.get_json(silent=True) or {}).get('decision')
        if value not in ['keep','intake','duplicate']:return jsonify(error='Invalid review decision.'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            item=c.execute('SELECT * FROM catalog_files WHERE id=?',(id,)).fetchone()
            if not item:return jsonify(error='Entry not found.'),404
            if value=='duplicate':
                retained=c.execute("SELECT count(*) FROM catalog_files WHERE id!=? AND hash=? AND size=? AND decision!='duplicate'",(id,item['hash'],item['size'])).fetchone()[0]
                if not item['hash'] or not retained:
                    return jsonify(error='A valid matching hash and size, with at least one retained copy, are required. Unknowns stay protected.'),400
            c.execute('UPDATE catalog_files SET decision=? WHERE id=?',(value,id))
        return jsonify(ok=True)

    @app.get('/api/catalog/export')
    def export():
        sources,rows=inventory()
        matches={}
        for item in rows:
            if item['hash']:matches.setdefault((item['hash'],item['size']),[]).append(item)
        for r in rows:
            r['source_root']=sources[r['source']]['root']
            r['retained_copy_locations']=[dict(root=sources[o['source']]['root'],path=o['path']) for o in (matches.get((r['hash'],r['size']),[]) if r['decision']=='duplicate' else []) if o['id']!=r['id'] and o['hash']==r['hash'] and o['size']==r['size'] and o['decision']!='duplicate']
        response=jsonify(version=1,created=stamp(),scope='Metadata recommendations only. Verify source bytes and retained copies before any deletion. Preserve backup sets until separately reviewed.',sources=sources,files=rows)
        response.headers['Content-Disposition']='attachment; filename=drive-review-plan.json'
        return response
