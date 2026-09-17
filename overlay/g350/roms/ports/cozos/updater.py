#!/usr/bin/env python3
import hashlib, json, os, shutil, urllib.request, zipfile
from pathlib import Path, PurePosixPath

VERSION='0.6.0'
ROOT=Path(os.environ.get('COZOS_ROOT','/'))
STATE=ROOT/'userdata/system/cozos'
APPS=STATE/'apps'
ACTIVE=STATE/'active-version'
UPDATES=ROOT/'userdata/cozos-updates'
LOGS=STATE/'logs'
INDEX_URL=os.environ.get('COZOS_INDEX_URL','https://raw.githubusercontent.com/UnknownApe1/CozOS-G350/knulli-main/releases/index.json')
REQUIRED=('main.py','updater.py')

def version_key(value):
    try: return tuple(int(part) for part in value.split('.'))
    except ValueError: return (-1,)

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def log(message):
    LOGS.mkdir(parents=True, exist_ok=True)
    with (LOGS/'updates.log').open('a',encoding='utf-8') as f: f.write(message.rstrip()+'\n')

def progress(cb, pct, text):
    if cb: cb(pct,text)
    log(f'{pct:3d}% {text}')

def current_version():
    try:return ACTIVE.read_text().strip()
    except OSError:return ''

def _safe_members(z):
    for info in z.infolist():
        p=PurePosixPath(info.filename)
        if p.is_absolute() or '..' in p.parts: raise RuntimeError('Unsafe ZIP path: '+info.filename)
        yield info

def inspect_package(path):
    with zipfile.ZipFile(path,'r') as z:
        names={i.filename for i in _safe_members(z)}
        try: version=z.read('cozos-update/VERSION').decode().strip()
        except KeyError: raise RuntimeError('Missing cozos-update/VERSION')
        if not version or any(c not in '0123456789.' for c in version): raise RuntimeError('Invalid update version')
        base='cozos-update/app/'
        missing=[x for x in REQUIRED if base+x not in names]
        if missing: raise RuntimeError('Update is missing: '+', '.join(missing))
        try: manifest=json.loads(z.read('cozos-update/MANIFEST.json'))
        except Exception as exc: raise RuntimeError('Invalid update manifest: '+str(exc))
        if manifest.get('version')!=version: raise RuntimeError('Manifest version mismatch')
        files=manifest.get('files')
        if not isinstance(files,dict): raise RuntimeError('Manifest files table is invalid')
        for rel, expected in files.items():
            p=PurePosixPath(rel)
            if p.is_absolute() or '..' in p.parts or not rel.startswith('app/'):
                raise RuntimeError('Unsafe manifest path: '+repr(rel))
            try:data=z.read('cozos-update/'+rel)
            except KeyError: raise RuntimeError('Manifest file missing: '+rel)
            if hashlib.sha256(data).hexdigest()!=expected: raise RuntimeError('Checksum failed: '+rel)
        return version

def install_package(path, expected_sha256=None, cb=None):
    path=Path(path)
    progress(cb,5,'Reading update package')
    if expected_sha256 and sha256_file(path).lower()!=expected_sha256.lower(): raise RuntimeError('Package SHA-256 does not match release index')
    version=inspect_package(path)
    progress(cb,25,'Validated CozOS '+version)
    APPS.mkdir(parents=True, exist_ok=True)
    staging=APPS/(version+'.staging'); target=APPS/version
    shutil.rmtree(staging,ignore_errors=True)
    active=current_version(); active_dir=APPS/active if active else None
    if active_dir and active_dir.is_dir(): shutil.copytree(active_dir,staging)
    else: staging.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(path,'r') as z:
        for info in _safe_members(z):
            if not info.filename.startswith('cozos-update/app/') or info.is_dir(): continue
            rel=PurePosixPath(info.filename).relative_to('cozos-update/app')
            out=staging.joinpath(*rel.parts); out.parent.mkdir(parents=True,exist_ok=True)
            with z.open(info) as src, open(out,'wb') as dst: shutil.copyfileobj(src,dst)
    progress(cb,60,'Staged version '+version)
    for name in REQUIRED:
        if not (staging/name).is_file(): raise RuntimeError('Staging validation failed: '+name)
    (staging/'VERSION').write_text(version+'\n')
    if target.exists(): shutil.rmtree(target)
    os.replace(staging,target)
    progress(cb,80,'Installed versioned app files')
    previous=current_version()
    tmp=ACTIVE.with_suffix('.tmp'); tmp.write_text(version+'\n'); os.replace(tmp,ACTIVE)
    progress(cb,100,'Activated CozOS '+version)
    return version,previous

def rollback(cb=None):
    active=current_version()
    versions=sorted((p.name for p in APPS.iterdir() if p.is_dir() and not p.name.endswith('.staging')),key=version_key,reverse=True) if APPS.exists() else []
    choices=[v for v in versions if v!=active]
    if not choices: raise RuntimeError('No previous CozOS version is available for rollback')
    target=choices[0]
    tmp=ACTIVE.with_suffix('.tmp'); tmp.write_text(target+'\n'); os.replace(tmp,ACTIVE)
    progress(cb,100,'Rolled back to CozOS '+target)
    return target

def newest_local():
    if not UPDATES.exists(): return None
    candidates=[]
    for path in UPDATES.glob('CozOS-G350-Update-*.zip'):
        try: candidates.append((version_key(inspect_package(path)),path))
        except Exception: continue
    return max(candidates,key=lambda item:item[0])[1] if candidates else None

def install_local(cb=None):
    package=newest_local()
    if not package: raise RuntimeError('No valid update ZIP found in SHARE/cozos-updates')
    return install_package(package,cb=cb)

def fetch_online(cb=None):
    progress(cb,5,'Checking online release index')
    with urllib.request.urlopen(INDEX_URL,timeout=20) as r: index=json.loads(r.read().decode())
    version=index['latest']; url=index['url']; checksum=index['sha256']
    progress(cb,20,'Latest online version is '+version)
    UPDATES.mkdir(parents=True,exist_ok=True)
    destination=UPDATES/('CozOS-G350-Update-'+version+'.zip')
    with urllib.request.urlopen(url,timeout=60) as r, open(destination,'wb') as f: shutil.copyfileobj(r,f)
    progress(cb,60,'Downloaded update package')
    return install_package(destination,expected_sha256=checksum,cb=lambda p,t:progress(cb,60+int(p*.4),t))
