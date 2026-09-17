#!/usr/bin/env python3
"""Validate and package the CozOS G350 overlay (never a firmware image)."""
import argparse
import ast
import hashlib
from pathlib import Path
import py_compile
import re
import subprocess
import sys
import tempfile
import zipfile

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / 'overlay/g350'


def version_from_python(path):
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1 and
                isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'VERSION' and
                isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
            return node.value.value
    raise RuntimeError('VERSION string not found in ' + str(path))


def validate(version):
    errors = []
    expected = {
        SOURCE / 'roms/ports/CozOS Control Center.sh',
        SOURCE / 'roms/ports/cozos/control_center.py',
        SOURCE / 'roms/ports/cozos/overlay.py',
        SOURCE / 'roms/ports/cozos/rootsplash.py',
        SOURCE / 'roms/ports/cozos/bootlogo.py',
        SOURCE / 'roms/ports/cozos/assets/cozos-splash-640x480.png',
    }
    for path in expected:
        if not path.is_file():
            errors.append('missing required file: ' + str(path.relative_to(REPO)))
    launchers = list((SOURCE / 'roms/ports').glob('CozOS*.sh'))
    if [path.name for path in launchers] != ['CozOS Control Center.sh']:
        errors.append('expected exactly one stable Ports launcher, found: ' +
                      ', '.join(path.name for path in launchers))
    for path in (SOURCE / 'roms/ports/cozos').glob('*.py'):
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(str(exc))
        if path.name in ('control_center.py', 'overlay.py', 'rootsplash.py'):
            try:
                found = version_from_python(path)
                if found != version:
                    errors.append(f'{path.name} VERSION={found}, expected {version}')
            except (RuntimeError, SyntaxError) as exc:
                errors.append(str(exc))
    shell_files = launchers + list((SOURCE / 'roms/ports/cozos/bin').glob('*'))
    for path in shell_files:
        result = subprocess.run(['bash', '-n', str(path)], capture_output=True, text=True)
        if result.returncode:
            errors.append(path.name + ': ' + result.stderr.strip())
    splash = SOURCE / 'roms/ports/cozos/assets/cozos-splash-640x480.png'
    if splash.exists():
        data = splash.read_bytes()
        size = ((int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big'))
                if data.startswith(b'\x89PNG\r\n\x1a\n') and len(data) >= 24 else None)
        if size != (640, 480):
            errors.append('splash must be a valid 640x480 PNG')
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        errors.append('VERSION must use x.y.z format')
    if errors:
        raise RuntimeError('\n'.join(errors))


def package(destination, version):
    destination.mkdir(parents=True, exist_ok=True)
    archive_path = destination / f'CozOS-G350-Overlay-{version}.zip'
    files = sorted(path for path in SOURCE.rglob('*') if path.is_file() and
                   '__pycache__' not in path.parts)
    with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(SOURCE).as_posix(),
                                   date_time=(2026, 1, 1, 0, 0, 0))
            mode = 0o755 if path.suffix == '.sh' or path.parent.name == 'bin' else 0o644
            info.external_attr = (mode & 0xFFFF) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED,
                             compresslevel=9)
    payload = archive_path.read_bytes()
    checksum = hashlib.sha256(payload).hexdigest()
    checksum_path = archive_path.with_suffix(archive_path.suffix + '.sha256')
    checksum_path.write_text(checksum + '  ' + archive_path.name + '\n')
    with zipfile.ZipFile(archive_path) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError('ZIP integrity check failed at ' + bad)
    return archive_path, checksum_path, checksum


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, default=REPO / 'dist')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    version = (REPO / 'VERSION').read_text().strip()
    validate(version)
    if args.check_only:
        print('CozOS overlay validation passed for ' + version)
        return 0
    archive, checksum_file, checksum = package(args.output_dir, version)
    print(archive)
    print(checksum_file)
    print('SHA-256: ' + checksum)
    return 0


if __name__ == '__main__':
    sys.exit(main())
