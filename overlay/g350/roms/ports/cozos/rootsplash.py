#!/usr/bin/env python3
"""Install the CozOS image into KNULLI's actual early system-splash path.

The BATLEXP G350 Scarab image does not consume the optional boot-partition
bootlogo.bmp convention.  Its early splash init script selects a PNG under
/usr/share/knulli/splash.  That directory lives in KNULLI's read-only rootfs,
so a verified change must be persisted with knulli-save-overlay.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

VERSION = '0.5.3'
ROOT = Path(os.environ.get('COZOS_ROOT', '/'))
STATE = ROOT / 'userdata/system/cozos'
STATE_FILE = STATE / 'rootfs-splash.json'
SOURCE = Path(__file__).with_name('assets') / 'cozos-splash-640x480.png'
INIT = ROOT / 'etc/init.d/S03system-splash'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic(path, data, mode=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.cozos-tmp')
    with temp.open('wb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)
    if mode is not None:
        path.chmod(mode)


def read_text(path):
    try:
        return path.read_text(errors='replace').replace('\x00', '').strip()
    except OSError:
        return ''


def png_size(payload):
    if not payload.startswith(b'\x89PNG\r\n\x1a\n') or len(payload) < 24:
        raise RuntimeError('Packaged CozOS artwork is not a valid PNG.')
    return (int.from_bytes(payload[16:20], 'big'),
            int.from_bytes(payload[20:24], 'big'))


def select_target():
    init_text = read_text(INIT)
    if not init_text:
        raise RuntimeError('/etc/init.d/S03system-splash is missing or unreadable.')
    if '/usr/share/knulli/splash/boot-logo' not in init_text:
        raise RuntimeError('S03system-splash does not use the supported KNULLI boot-logo path.')

    virtual = read_text(ROOT / 'sys/class/graphics/fb0/virtual_size')
    match = re.search(r'(\d+)\s*,\s*(\d+)', virtual)
    candidates = []
    if match:
        candidates.append(ROOT / 'usr/share/knulli/splash' /
                          ('boot-logo-' + match.group(1) + 'x' + match.group(2) + '.png'))
    candidates.append(ROOT / 'usr/share/knulli/splash/boot-logo.png')
    for path in candidates:
        if path.is_file() and not path.is_symlink():
            return path, virtual or '<unavailable>'
    raise RuntimeError('KNULLI system splash image was not found at: ' +
                       ', '.join(str(path) for path in candidates))


def load_state():
    if not STATE_FILE.exists():
        return None
    return json.loads(STATE_FILE.read_text())


def save_state(info):
    STATE.mkdir(parents=True, exist_ok=True)
    atomic(STATE_FILE, json.dumps(info, indent=2, sort_keys=True).encode())


def save_overlay():
    if ROOT != Path('/'):
        return 'test-mode'
    command = shutil.which('knulli-save-overlay')
    if not command:
        raise RuntimeError('knulli-save-overlay is missing; rootfs was not made persistent.')
    result = subprocess.run([command], capture_output=True, text=True,
                            timeout=600, check=False)
    output = (result.stdout + '\n' + result.stderr).strip()
    if result.returncode != 0:
        raise RuntimeError('knulli-save-overlay failed (' + str(result.returncode) + '): ' +
                           (output[-600:] if output else '<no output>'))
    return output[-600:] if output else 'completed successfully'


def install():
    payload = SOURCE.read_bytes()
    if png_size(payload) != (640, 480):
        raise RuntimeError('CozOS splash must be exactly 640x480.')
    target, virtual = select_target()
    installed_sha = digest(payload)
    prior = load_state()
    current = target.read_bytes()
    current_sha = digest(current)
    try:
        target_size = png_size(current)
    except RuntimeError:
        raise RuntimeError('KNULLI selected a system splash that is not a valid PNG.')
    if target_size != (640, 480):
        raise RuntimeError('KNULLI system splash is ' + str(target_size[0]) + 'x' +
                           str(target_size[1]) + '; refusing a 640x480 replacement.')

    if prior:
        if Path(prior.get('target', '')) != target:
            raise RuntimeError('KNULLI selected a different system splash; run CozOS Remove first.')
        if current_sha == installed_sha:
            overlay_output = save_overlay()
            prior.update({'version': VERSION, 'phase': 'installed',
                          'overlay_result': overlay_output})
            save_state(prior)
            return 'CozOS ' + VERSION + ' system boot splash is installed and persisted.'
        if current_sha != prior.get('original_sha256'):
            raise RuntimeError('System splash changed after CozOS prepared it; refusing to overwrite it.')
        info = prior
    else:
        backup = STATE / ('rootfs-splash-original-' + current_sha[:12] + '.png')
        if backup.exists() and digest(backup.read_bytes()) != current_sha:
            raise RuntimeError('Existing system-splash backup checksum mismatch.')
        if not backup.exists():
            atomic(backup, current, 0o600)
        info = {
            'version': VERSION,
            'phase': 'prepared',
            'target': str(target),
            'virtual_size': virtual,
            'backup': str(backup),
            'original_sha256': current_sha,
            'original_mode': target.stat().st_mode & 0o777,
            'installed_sha256': installed_sha,
        }
        save_state(info)

    atomic(target, payload, int(info.get('original_mode', 0o644)))
    if digest(target.read_bytes()) != installed_sha:
        raise RuntimeError('Installed system splash failed checksum verification.')
    try:
        overlay_output = save_overlay()
    except Exception as first_error:
        # Restore the live filesystem immediately. The failed overlay save may
        # have left an old overlay intact, but must never leave an untracked edit.
        original = Path(info['backup']).read_bytes()
        atomic(target, original, int(info.get('original_mode', 0o644)))
        try:
            save_overlay()
        except Exception as rollback_error:
            raise RuntimeError(str(first_error) + '; live image was restored, but '
                               'overlay rollback also failed: ' + str(rollback_error))
        raise RuntimeError(str(first_error) + '; original image was restored and persisted.')
    info.update({'phase': 'installed', 'overlay_result': overlay_output})
    save_state(info)
    return ('CozOS ' + VERSION + ' replaced ' + str(target) +
            ' and saved the KNULLI overlay. Reboot to see it.')


def remove():
    info = load_state()
    if not info:
        return 'No CozOS system-splash record found; rootfs was not changed by this module.'
    target = Path(info['target'])
    if not target.exists():
        raise RuntimeError('Managed system splash is missing; refusing an incomplete rollback.')
    current_sha = digest(target.read_bytes())
    if current_sha != info.get('installed_sha256'):
        raise RuntimeError('System splash was edited after CozOS; refusing to overwrite the newer file.')
    backup = Path(info['backup'])
    if not backup.exists():
        raise RuntimeError('Original system-splash backup is missing.')
    original = backup.read_bytes()
    if digest(original) != info.get('original_sha256'):
        raise RuntimeError('Original system-splash backup checksum mismatch.')
    atomic(target, original, int(info.get('original_mode', 0o644)))
    if digest(target.read_bytes()) != info.get('original_sha256'):
        raise RuntimeError('Restored system splash failed verification.')
    overlay_output = save_overlay()
    STATE_FILE.unlink()
    return 'Original KNULLI system splash restored, verified, and persisted. ' + overlay_output


def status():
    info = load_state()
    try:
        detected, virtual = select_target()
        detection_error = None
    except Exception as exc:
        detected, virtual, detection_error = None, '<unknown>', str(exc)
    target = Path(info['target']) if info and info.get('target') else detected
    lines = [f'CozOS {VERSION} KNULLI system-splash status',
             'virtual-size=' + virtual,
             'detected-target=' + (str(detected) if detected else '<none>')]
    if detection_error:
        lines.append('detection-error=' + detection_error)
    if target and target.exists():
        lines += ['managed-target=' + str(target),
                  'target-sha256=' + digest(target.read_bytes())]
    else:
        lines += ['managed-target=' + (str(target) if target else '<none>'),
                  'target-present=False']
    if info:
        backup = Path(info.get('backup', ''))
        lines += ['managed=True', 'phase=' + str(info.get('phase')),
                  'expected-cozos-sha256=' + str(info.get('installed_sha256')),
                  'original-sha256=' + str(info.get('original_sha256')),
                  'backup=' + str(backup), 'backup-present=' + str(backup.exists()),
                  'overlay-result=' + str(info.get('overlay_result', '<not recorded>'))]
    else:
        lines += ['managed=False', 'rollback-record=missing']
    output = '\n'.join(lines) + '\n'
    STATE.mkdir(parents=True, exist_ok=True)
    atomic(STATE / 'rootfs-splash-status.txt', output.encode())
    print(output, end='')
    return 0


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'status'
    try:
        if action == 'install':
            print(install())
            return 0
        if action == 'remove':
            print(remove())
            return 0
        if action == 'status':
            return status()
        raise RuntimeError('Unknown action: ' + action)
    except Exception as exc:
        message = 'CozOS system-splash stopped: ' + str(exc)
        STATE.mkdir(parents=True, exist_ok=True)
        atomic(STATE / 'rootfs-splash-last-action.txt', message.encode())
        print(message)
        return 1


if __name__ == '__main__':
    sys.exit(main())
