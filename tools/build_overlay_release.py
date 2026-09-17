#!/usr/bin/env python3
"""Validate and package CozOS G350 overlay and versioned updater payload."""
import argparse, ast, hashlib, json, py_compile, re, subprocess, sys, zipfile
from pathlib import Path

REPO=Path(__file__).resolve().parents[1]
SOURCE=REPO/'overlay/g350'
APP=SOURCE/'roms/ports/cozos'


def version_from_python(path):
    tree=ast.parse(path.read_text(),filename=str(path))
    for node in tree.body:
        if (isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name)
                and node.targets[0].id=='VERSION' and isinstance(node.value,ast.Constant)
                and isinstance(node.value.value,str)):
            return node.value.value
    raise RuntimeError('VERSION string not found in '+str(path))


def validate(version):
    errors=[]
    expected={SOURCE/'roms/ports/CozOS Control Center.sh', APP/'control_center.py',
              APP/'control_center_060.py', APP/'updater.py', APP/'overlay.py', APP/'overlay_060.py',
              APP/'rootsplash.py', APP/'rootsplash_060.py', APP/'bootlogo.py',
              APP/'assets/cozos-splash-640x480.png'}
    for path in expected:
        if not path.is_file(): errors.append('missing required file: '+str(path.relative_to(REPO)))
    launchers=list((SOURCE/'roms/ports').glob('CozOS*.sh'))
    if [p.name for p in launchers]!=['CozOS Control Center.sh']:
        errors.append('expected exactly one stable Ports launcher, found: '+', '.join(p.name for p in launchers))
    for path in APP.glob('*.py'):
        try: py_compile.compile(str(path),doraise=True)
        except py_compile.PyCompileError as exc: errors.append(str(exc))
    for name in ('control_center_060.py','updater.py'):
        try:
            found=version_from_python(APP/name)
            if found!=version: errors.append(f'{name} VERSION={found}, expected {version}')
        except (RuntimeError,SyntaxError) as exc: errors.append(str(exc))
    for path in launchers+list((APP/'bin').glob('*')):
        result=subprocess.run(['bash','-n',str(path)],capture_output=True,text=True)
        if result.returncode: errors.append(path.name+': '+result.stderr.strip())
    splash=APP/'assets/cozos-splash-640x480.png'
    if splash.exists():
        data=splash.read_bytes()
        size=((int.from_bytes(data[16:20],'big'),int.from_bytes(data[20:24],'big'))
              if data.startswith(b'\x89PNG\r\n\x1a\n') and len(data)>=24 else None)
        if size!=(640,480): errors.append('splash must be a valid 640x480 PNG')
    if not re.fullmatch(r'\d+\.\d+\.\d+',version): errors.append('VERSION must use x.y.z format')
    if errors: raise RuntimeError('\n'.join(errors))


def write_zip(path, entries):
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for arcname,source,mode in entries:
            info=zipfile.ZipInfo(arcname,date_time=(2026,1,1,0,0,0))
            info.external_attr=(mode & 0xffff)<<16; info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,source.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(path) as archive:
        bad=archive.testzip()
        if bad: raise RuntimeError('ZIP integrity check failed at '+bad)


def checksum(path):
    value=hashlib.sha256(path.read_bytes()).hexdigest()
    sidecar=path.with_suffix(path.suffix+'.sha256')
    sidecar.write_text(value+'  '+path.name+'\n')
    return sidecar,value


def package_overlay(destination,version):
    path=destination/f'CozOS-G350-Overlay-{version}.zip'
    files=sorted(p for p in SOURCE.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    entries=[(p.relative_to(SOURCE).as_posix(),p,0o755 if p.suffix=='.sh' or p.parent.name=='bin' else 0o644) for p in files]
    write_zip(path,entries)
    sidecar,value=checksum(path)
    return path,sidecar,value


def package_update(destination,version):
    path=destination/f'CozOS-G350-Update-{version}.zip'
    files=sorted(p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    manifest={'version':version,'files':{}}
    for p in files:
        rel='app/'+p.relative_to(APP).as_posix()
        manifest['files'][rel]=hashlib.sha256(p.read_bytes()).hexdigest()
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        def put(name,data,mode=0o644):
            info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0)); info.external_attr=(mode&0xffff)<<16
            info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
        put('cozos-update/VERSION',(version+'\n').encode())
        put('cozos-update/MANIFEST.json',(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode())
        for p in files:
            put('cozos-update/app/'+p.relative_to(APP).as_posix(),p.read_bytes(),0o755 if p.suffix=='.sh' or p.parent.name=='bin' else 0o644)
    with zipfile.ZipFile(path) as archive:
        bad=archive.testzip()
        if bad: raise RuntimeError('Update ZIP integrity check failed at '+bad)
    sidecar,value=checksum(path)
    return path,sidecar,value


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--output-dir',type=Path,default=REPO/'dist'); parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args(); version=(REPO/'VERSION').read_text().strip(); validate(version)
    if args.check_only:
        print('CozOS overlay validation passed for '+version); return 0
    args.output_dir.mkdir(parents=True,exist_ok=True)
    overlay,overlay_sha,ov=package_overlay(args.output_dir,version)
    update,update_sha,uv=package_update(args.output_dir,version)
    index={'latest':version,'sha256':uv,'url':'https://raw.githubusercontent.com/UnknownApe1/CozOS-G350/knulli-main/releases/'+update.name}
    index_path=args.output_dir/'index.json'; index_path.write_text(json.dumps(index,indent=2,sort_keys=True)+'\n')
    for p in (overlay,overlay_sha,update,update_sha,index_path): print(p)
    print('Overlay SHA-256: '+ov); print('Update SHA-256: '+uv); return 0

if __name__=='__main__': sys.exit(main())
