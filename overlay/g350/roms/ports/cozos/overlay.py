#!/usr/bin/env python3
"""CozOS G350 overlay: user configuration only, no root filesystem edits."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

VERSION = '0.1.0'
ROOT = Path('/')
STATE = Path('/userdata/system/cozos')

def read(path):
    try:
        return Path(path).read_text(errors='replace').replace('\x00', '').strip()
    except OSError:
        return ''

def digest(data):
    return hashlib.sha256(data).hexdigest()

def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.cozos-tmp')
    with temp.open('wb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)

def mapping(text):
    # Change only known stock brightness chords; retain power and volume actions.
    lines = text.splitlines()
    changed = 0
    for i, line in enumerate(lines):
        if line.lstrip().startswith('#'):
            continue
        if re.search(r'/usr/bin/volume-button(?:-release)?(?:\s|$)', line):
            new = re.sub(r'(KEY_VOLUME(?:UP|DOWN)\+)BTN_TRIGGER_HAPPY[0-9]+',
                         r'\1BTN_TRIGGER_HAPPY5', line)
            changed += new != line
            lines[i] = new
    result = '\n'.join(lines) + '\n'
    for key, action in [('KEY_VOLUMEUP', 'briup'), ('KEY_VOLUMEDOWN', 'bridown')]:
        for state, command in [('1', '/usr/bin/volume-button ' + action),
                               ('0', '/usr/bin/volume-button-release')]:
            pattern = r'^' + re.escape(key + '+BTN_TRIGGER_HAPPY5') + r'\s+' + state + r'\s+'
            matches = [l for l in lines if re.match(pattern, l)]
            if matches and not all(l.split(None, 2)[2].strip() == command for l in matches):
                raise RuntimeError('Existing FN mapping conflicts with the stock handler; no changes made.')
            if not matches:
                result += f'{key}+BTN_TRIGGER_HAPPY5 {state} {command}\n'
    return result

def check_device():
    model = read(ROOT / 'sys/firmware/devicetree/base/model')
    if not re.search(r'g350|batlexp', model, re.I):
        raise RuntimeError('Device is not identified as G350/BATLEXP: ' + repr(model))
    init = read(ROOT / 'etc/init.d/S50triggerhappy')
    if '/userdata/system/configs/multimedia_keys.conf' not in init:
        raise RuntimeError('Installed firmware lacks the verified user hotkey override hook.')
    handler = read(ROOT / 'usr/bin/volume-button')
    if 'briup)' not in handler or 'bridown)' not in handler:
        raise RuntimeError('Installed volume handler differs from the supported interface.')
    if not (ROOT / 'usr/bin/knulli-brightness').exists():
        raise RuntimeError('KNULLI brightness command is missing.')
    return re.sub('[^A-Za-z0-9]', '', model)

def install():
    model = check_device()
    target = ROOT / 'userdata/system/configs/multimedia_keys.conf'
    manifest = STATE / 'installed.json'
    if manifest.exists():
        saved = json.loads(manifest.read_text())
        if target.exists() and digest(target.read_bytes()) == saved['installed_sha256']:
            return 'CozOS ' + VERSION + ' is already installed. Reboot if you have not yet.'
        raise RuntimeError('Hotkey config changed after installation. Remove/review it before reinstalling.')
    stock = ROOT / ('etc/triggerhappy/triggers.d/multimedia_keys_' + model + '.conf')
    if not stock.exists():
        stock = ROOT / 'etc/triggerhappy/triggers.d/multimedia_keys.conf'
    source = target if target.exists() else stock
    original = source.read_bytes()
    updated = mapping(original.decode('utf-8')).encode()
    # Save rollback data before changing the user configuration.
    STATE.mkdir(parents=True, exist_ok=True)
    atomic(STATE / 'original-multimedia.conf', original)
    info = {'version': VERSION, 'had_override': target.exists(),
            'installed_sha256': digest(updated), 'original_sha256': digest(original),
            'source': str(source)}
    atomic(manifest, json.dumps(info, indent=2).encode())
    atomic(target, updated)
    diagnose()
    return 'CozOS ' + VERSION + ' installed. Reboot, then hold FN and tap Volume + or -. Power behavior is unchanged.'

def uninstall():
    manifest = STATE / 'installed.json'
    if not manifest.exists():
        return 'No CozOS installation record found; nothing changed.'
    saved = json.loads(manifest.read_text())
    target = ROOT / 'userdata/system/configs/multimedia_keys.conf'
    if not target.exists() or digest(target.read_bytes()) != saved['installed_sha256']:
        raise RuntimeError('Config was edited after installation. Refusing to overwrite it; original backup is in system/cozos.')
    original = (STATE / 'original-multimedia.conf').read_bytes()
    if digest(original) != saved['original_sha256']:
        raise RuntimeError('Original backup checksum mismatch; no changes made.')
    if saved['had_override']:
        atomic(target, original)
    else:
        target.unlink()
    manifest.unlink()
    return 'CozOS hotkey overlay removed. Reboot to restore previous behavior. Reports and backup retained.'

def diagnose():
    STATE.mkdir(parents=True, exist_ok=True)
    current = read(ROOT / 'proc/sys/kernel/random/boot_id')
    previous = read(STATE / 'last-boot-id')
    if previous and current:
        verdict = ('Same kernel boot as the previous check: no full reboot between checks.' if previous == current
                   else 'Boot ID changed: the device rebooted between checks. This alone does not identify the cause.')
    else:
        verdict = 'Baseline recorded. Run this again after testing the power button.'
    lines = ['CozOS overlay ' + VERSION, 'Installed: ' + str((STATE / 'installed.json').exists()),
             'UTC: ' + datetime.datetime.now(datetime.timezone.utc).isoformat(), verdict]
    for path in ['sys/firmware/devicetree/base/model', 'etc/os-release',
                 'proc/uptime', 'sys/power/state', 'sys/power/mem_sleep',
                 'boot/boot/knulli.board.capability']:
        lines += ['\n[' + path + ']', read(ROOT / path)]
    conf = read(ROOT / 'userdata/system/batocera.conf') + '\n' + read(ROOT / 'userdata/system/knulli.conf')
    lines += ['\n[Power settings only]'] + [l for l in conf.splitlines()
        if re.match(r'system\.(suspend|batterysaver|idlewatcher|multimediakeys)', l)]
    for path in ['userdata/system/configs/multimedia_keys.conf', 'usr/bin/power-button',
                 'usr/bin/power-button-release', 'usr/bin/knulli-suspend']:
        lines += ['\n[' + path + ']', read(ROOT / path)]
    lines += ['\n[Input device names/key capabilities]']
    for event in sorted((ROOT / 'sys/class/input').glob('event*')):
        lines += [event.name + ': ' + read(event / 'device/name'), read(event / 'device/capabilities/key')]
    text = '\n'.join(lines) + '\n'
    atomic(STATE / 'report.txt', text.encode())
    if current:
        atomic(STATE / 'last-boot-id', current.encode())
    return 'CozOS ' + VERSION + '\n' + verdict + '\nReport saved: /userdata/system/cozos/report.txt'

def main():
    try:
        action = sys.argv[1] if len(sys.argv) > 1 else 'status'
        message = {'install': install, 'remove': uninstall, 'status': diagnose}[action]()
        rc = 0
    except Exception as e:
        message, rc = 'CozOS stopped: ' + str(e), 1
    STATE.mkdir(parents=True, exist_ok=True)
    atomic(STATE / 'last-action.txt', message.encode())
    print(message)
    # Ports launches on firmware with a usable terminal can display dialog.
    if sys.stdout.isatty():
        import shutil
        if shutil.which('dialog'):
            subprocess.run(['dialog', '--title', 'CozOS ' + VERSION, '--msgbox', message, '15', '65'])
    return rc

if __name__ == '__main__':
    sys.exit(main())
