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

VERSION = '0.4.4'
ROOT = Path('/')
STATE = Path('/userdata/system/cozos')

# Conservative G350/RK3326 defaults. These use KNULLI's own public option
# names, keep native resolutions for demanding systems, and avoid enhancements
# which trade compatibility or frame pacing for visual effects.
TUNING = {
    'splash.screen.enabled': '1',
    'splash.screen.length': '5',
    'global.powermode': 'balanced',
    'global.batterymode': 'balanced',
    'global.video_threaded': 'true',
    'global.audio_latency': '64',
    'global.ratio': 'core',
    'global.smooth': '0',
    'global.vsync': '1',
    'global.gpusync': '0',
    'psx.emulator': 'libretro',
    'psx.core': 'pcsx_rearmed',
    'psx.powermode': 'balanced',
    'psx.ratio': 'core',
    'psx.integerscale': '1',
    'n64.emulator': 'mupen64plus',
    'n64.core': 'glide64mk2',
    'n64.powermode': 'highperformance',
    'n64.mupen64plus_ratio': '4/3',
    'n64.mupen64plus_frameskip': '0',
    'n64.mupen64plus_AudioSync': 'False',
    'n64.mupen64plus_AudioBuffer': 'Medium',
    'dreamcast.emulator': 'libretro',
    'dreamcast.core': 'flycastvl',
    'dreamcast.powermode': 'highperformance',
    'dreamcast.reicast_internal_resolution': '640x480',
    'dreamcast.reicast_synchronous_rendering': 'disabled',
    'atomiswave.emulator': 'libretro',
    'atomiswave.core': 'flycastvl',
    'atomiswave.powermode': 'highperformance',
    'atomiswave.reicast_internal_resolution': '640x480',
    'naomi.emulator': 'libretro',
    'naomi.core': 'flycastvl',
    'naomi.powermode': 'highperformance',
    'naomi.reicast_internal_resolution': '640x480',
    'psp.emulator': 'ppsspp',
    'psp.core': 'ppsspp',
    'psp.powermode': 'highperformance',
    'psp.internal_resolution': '1',
    'psp.frameskip': '2',
    'psp.autoframeskip': '1',
    'psp.texture_scaling_level': '1',
    'nds.emulator': 'drastic',
    'nds.core': 'drastic',
    'nds.powermode': 'highperformance',
    'nds.drastic_hires': '0',
    'nds.drastic_frameskip_type': '0',
    'saturn.emulator': 'yabasanshiro',
    'saturn.core': 'yabasanshiro',
    'saturn.powermode': 'highperformance',
    'saturn.yaba_res': '0',
    'system.batterysaver.extendedmode': 'shutdown',
}

for _system in ('nes', 'snes', 'megadrive', 'mastersystem', 'gamegear',
                'gb', 'gbc', 'gba', 'pcengine', 'pcenginecd', 'neogeo'):
    TUNING[_system + '.ratio'] = 'core'
    TUNING[_system + '.smooth'] = '0'
    TUNING[_system + '.integerscale'] = '1'

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
    # The installed 2026-05-10 G350 build enters pm-suspend on a short press,
    # then boots again instead of resuming. Route only the plain power events
    # to the persistent CozOS handler; retain FN+power and every other binding.
    replacements = {
        '1': '/userdata/system/cozos/bin/power-button',
        '0': '/userdata/system/cozos/bin/power-button-release',
    }
    out = []
    seen = set()
    for line in result.splitlines():
        match = re.match(r'^KEY_POWER\s+([01])\s+(.+)$', line)
        if match:
            state = match.group(1)
            out.append(f'KEY_POWER {state} {replacements[state]}')
            seen.add(state)
        else:
            out.append(line)
    for state in ('1', '0'):
        if state not in seen:
            out.append(f'KEY_POWER {state} {replacements[state]}')
    result = '\n'.join(out) + '\n'
    return result

def config_values(text, key):
    pattern = re.compile(r'^\s*' + re.escape(key) + r'\s*=\s*(.*?)\s*$')
    return [match.group(1) for line in text.splitlines()
            if (match := pattern.match(line))]

def set_config_value(text, key, value):
    """Replace one KNULLI setting while preserving every unrelated line."""
    pattern = re.compile(r'^\s*' + re.escape(key) + r'\s*=')
    lines = text.splitlines()
    out = []
    replaced = False
    for line in lines:
        if pattern.match(line):
            if not replaced:
                out.append(f'{key}={value}')
                replaced = True
            continue
        out.append(line)
    if not replaced:
        out.append(f'{key}={value}')
    return '\n'.join(out) + '\n'

def apply_managed_settings(prior):
    """Apply tuning while retaining the original value of every key."""
    path = ROOT / 'userdata/system/knulli.conf'
    text = path.read_text(errors='replace') if path.exists() else ''
    old_records = {(item['path'], item['key']): item
                   for item in (prior or {}).get('managed_settings', [])}
    # Convert the 0.3 idle rollback record so an upgrade still restores the
    # value that existed before CozOS first changed it.
    legacy = (prior or {}).get('idle_safety')
    if legacy and legacy.get('changed'):
        old_records[(legacy['path'], legacy['key'])] = {
            'path': legacy['path'], 'key': legacy['key'],
            'before_values': legacy.get('before_values', []),
            'installed_value': 'shutdown', 'changed': True,
        }
    records = []
    relative = str(path.relative_to(ROOT))
    for key, value in TUNING.items():
        old = old_records.get((relative, key))
        values = config_values(text, key)
        # Existing explicit emulator/scaling/audio choices are user choices,
        # not defaults. Leave them live. The two safety/branding switches are
        # intentionally managed when needed.
        force = key == 'splash.screen.enabled' or (
            key == 'system.batterysaver.extendedmode' and values and values[-1] == 'suspend')
        if old and not old.get('changed'):
            # This key was already an explicit user choice when CozOS first
            # saw it. A repeat install must never turn that choice into a
            # CozOS-managed default.
            records.append(old)
            continue
        if old and values and values[-1] != old.get('installed_value'):
            records.append(old)  # a later user edit wins, including during upgrade
            continue
        if not old and values and values[-1] != value and not force:
            records.append({'path': relative, 'key': key,
                            'before_values': values,
                            'installed_value': values[-1], 'changed': False})
            continue
        record = {
            'path': relative,
            'key': key,
            'before_values': old['before_values'] if old else values,
            'installed_value': value,
            'changed': old.get('changed', False) if old else (not values or values[-1] != value),
        }
        text = set_config_value(text, key, value)
        records.append(record)
    atomic(path, text.encode())
    return records

def restore_managed_settings(records):
    """Restore managed keys, while preserving any later user edits."""
    by_path = {}
    for item in records or []:
        by_path.setdefault(item['path'], []).append(item)
    for relative, items in by_path.items():
        path = ROOT / relative
        text = path.read_text(errors='replace') if path.exists() else ''
        for item in items:
            if not item.get('changed'):
                continue
            values = config_values(text, item['key'])
            if not values or values[-1] != item['installed_value']:
                continue
            pattern = re.compile(r'^\s*' + re.escape(item['key']) + r'\s*=')
            lines = [line for line in text.splitlines() if not pattern.match(line)]
            lines += [f"{item['key']}={value}" for value in item.get('before_values', [])]
            text = '\n'.join(lines) + '\n'
        atomic(path, text.encode())

def write_boot_config(path, text):
    """Safely update KNULLI's early-boot config, which is normally read-only."""
    real_boot = ROOT == Path('/')
    if real_boot:
        subprocess.run(['mount', '-o', 'remount,rw', '/boot'], check=True)
    try:
        atomic(path, text.encode())
    finally:
        if real_boot:
            subprocess.run(['mount', '-o', 'remount,ro', '/boot'], check=True)

def apply_boot_splash(prior):
    """Enable the splash where S28splash actually reads it at boot."""
    path = ROOT / 'boot/knulli-boot.conf'
    if not path.exists():
        raise RuntimeError('/boot/knulli-boot.conf is missing; splash was not changed.')
    key = 'splash.screen.enabled'
    text = path.read_text(errors='replace')
    values = config_values(text, key)
    old = (prior or {}).get('boot_splash')
    if old and values and values[-1] != old.get('installed_value'):
        return old  # preserve a later user edit
    record = {
        'path': str(path.relative_to(ROOT)), 'key': key,
        'before_values': old['before_values'] if old else values,
        'installed_value': '1',
        'changed': old.get('changed', False) if old else (not values or values[-1] != '1'),
    }
    if not values or values[-1] != '1':
        write_boot_config(path, set_config_value(text, key, '1'))
    return record

def restore_boot_splash(record):
    if not record or not record.get('changed'):
        return
    path = ROOT / record['path']
    if not path.exists():
        return
    text = path.read_text(errors='replace')
    values = config_values(text, record['key'])
    if not values or values[-1] != record['installed_value']:
        return  # a later user edit wins
    pattern = re.compile(r'^\s*' + re.escape(record['key']) + r'\s*=')
    lines = [line for line in text.splitlines() if not pattern.match(line)]
    lines += [f"{record['key']}={value}" for value in record.get('before_values', [])]
    write_boot_config(path, '\n'.join(lines) + '\n')

def install_splash(prior):
    package = Path(__file__).with_name('assets') / 'cozos-splash-640x480.png'
    payload = package.read_bytes()
    if not payload.startswith(b'\x89PNG\r\n\x1a\n'):
        raise RuntimeError('CozOS splash asset is not a valid PNG.')
    if len(payload) < 24 or tuple(int.from_bytes(payload[i:i + 4], 'big')
                                  for i in (16, 20)) != (640, 480):
        raise RuntimeError('CozOS splash asset must be exactly 640x480.')
    splash_dir = ROOT / 'userdata/splash'
    previous = (prior or {}).get('splash')
    backup_dir = ROOT / previous['backup_dir'] if previous else STATE / 'splash-backup-0.4'
    splash_dir.mkdir(parents=True, exist_ok=True)
    backup_dir.mkdir(parents=True, exist_ok=True)
    eligible = {'.png', '.jpg', '.jpeg', '.mp4'}
    originals = previous.get('originals', []) if previous else []
    if previous:
        old_target = ROOT / previous['target']
        if (old_target.exists() and
                digest(old_target.read_bytes()) == previous.get('installed_sha256')):
            old_target.unlink()
    else:
        for source in sorted(splash_dir.iterdir()):
            if not source.is_file() or source.suffix.lower() not in eligible:
                continue
            data = source.read_bytes()
            backup = backup_dir / source.name
            atomic(backup, data)
            originals.append({'name': source.name, 'sha256': digest(data),
                              'mode': source.stat().st_mode & 0o777})
        for item in originals:
            (splash_dir / item['name']).unlink()
    target = splash_dir / 'CozOS-G350-v0.4.4.png'
    atomic(target, payload)
    return {'target': str(target.relative_to(ROOT)),
            'installed_sha256': digest(payload), 'originals': originals,
            'backup_dir': str(backup_dir.relative_to(ROOT))}

def restore_splash(info):
    if not info:
        return
    target = ROOT / info['target']
    if target.exists() and digest(target.read_bytes()) == info['installed_sha256']:
        target.unlink()
    splash_dir = target.parent
    backup_dir = ROOT / info['backup_dir']
    for item in info.get('originals', []):
        source = backup_dir / item['name']
        destination = splash_dir / item['name']
        if source.exists() and not destination.exists():
            data = source.read_bytes()
            if digest(data) != item['sha256']:
                raise RuntimeError('Splash backup checksum mismatch: ' + item['name'])
            atomic(destination, data)
            destination.chmod(item.get('mode', 0o644))

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
    prior = None
    if manifest.exists():
        saved = json.loads(manifest.read_text())
        if not target.exists() or digest(target.read_bytes()) != saved['installed_sha256']:
            raise RuntimeError('Hotkey config changed after installation. Remove/review it before upgrading.')
        if saved.get('version') == VERSION:
            return 'CozOS ' + VERSION + ' is already installed. Reboot if you have not yet.'
        prior = saved
    stock = ROOT / ('etc/triggerhappy/triggers.d/multimedia_keys_' + model + '.conf')
    if not stock.exists():
        stock = ROOT / 'etc/triggerhappy/triggers.d/multimedia_keys.conf'
    source = target if target.exists() else stock
    current = source.read_bytes()
    if prior:
        original = (STATE / 'original-multimedia.conf').read_bytes()
        if digest(original) != prior['original_sha256']:
            raise RuntimeError('Original backup checksum mismatch; no changes made.')
    else:
        original = current
    updated = mapping(current.decode('utf-8')).encode()
    package_bin = Path(__file__).with_name('bin')
    bin_payloads = {name: (package_bin / name).read_bytes()
                    for name in ('power-button', 'power-button-release', 'fake-suspend')}
    # Save rollback data before changing the user configuration.
    STATE.mkdir(parents=True, exist_ok=True)
    atomic(STATE / 'original-multimedia.conf', original)
    boot_splash = apply_boot_splash(prior)
    managed_settings = apply_managed_settings(prior)
    splash = install_splash(prior)
    info = {'version': VERSION, 'had_override': prior['had_override'] if prior else target.exists(),
            'installed_sha256': digest(updated), 'original_sha256': digest(original),
            'source': str(source), 'boot_splash': boot_splash,
            'managed_settings': managed_settings, 'splash': splash}
    for name, data in bin_payloads.items():
        destination = STATE / 'bin' / name
        atomic(destination, data)
        destination.chmod(0o755)
    atomic(target, updated)
    atomic(manifest, json.dumps(info, indent=2).encode())
    ports = Path(__file__).parent.parent
    for old_name in (
        'CozOS 0.1 - Install.sh', 'CozOS 0.1 - Status and Power Check.sh', 'CozOS 0.1 - Remove.sh',
        'CozOS 0.2 - Install.sh', 'CozOS 0.2 - Status and Power Check.sh', 'CozOS 0.2 - Remove.sh',
        'CozOS 0.3 - Install.sh', 'CozOS 0.3 - Status.sh', 'CozOS 0.3 - Remove.sh',
        'CozOS 0.4 - Install.sh', 'CozOS 0.4 - Status.sh', 'CozOS 0.4 - Remove.sh',
        'CozOS 0.4.1 - Install.sh', 'CozOS 0.4.1 - Status.sh', 'CozOS 0.4.1 - Remove.sh',
        'CozOS 0.4.2 - Install.sh', 'CozOS 0.4.2 - Status.sh', 'CozOS 0.4.2 - Remove.sh',
        'CozOS 0.4.3 - Install.sh', 'CozOS 0.4.3 - Status.sh', 'CozOS 0.4.3 - Remove.sh',
    ):
        try:
            (ports / old_name).unlink()
        except FileNotFoundError:
            pass
    diagnose()
    return ('CozOS ' + VERSION + ' installed. Reboot; FN+Volume adjusts brightness. '
            'CozOS splash and G350 performance profiles are active. Short power toggles '
            'screen-off sleep; hold power 2 seconds to shut down.')

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
    restore_splash(saved.get('splash'))
    restore_managed_settings(saved.get('managed_settings'))
    restore_boot_splash(saved.get('boot_splash'))
    manifest.unlink()
    return ('CozOS overlay, splash and managed tuning removed. Reboot to restore '
            'previous behavior. Reports and verified backups are retained.')

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
    extended = config_values(read(ROOT / 'userdata/system/knulli.conf'),
                             'system.batterysaver.extendedmode')
    lines += ['Idle safety: ' + ('PASS (automatic hardware suspend disabled)'
             if extended and extended[-1] != 'suspend' else 'WARNING (automatic hardware suspend remains enabled)')]
    lines += ['\n[CozOS managed tuning]']
    user_conf = read(ROOT / 'userdata/system/knulli.conf')
    for key in TUNING:
        values = config_values(user_conf, key)
        lines.append(key + '=' + (values[-1] if values else '<missing>'))
    lines += ['\n[CozOS splash]',
              'present=' + str((ROOT / 'userdata/splash/CozOS-G350-v0.4.4.png').exists()),
              'boot-enabled=' + str(config_values(read(ROOT / 'boot/knulli-boot.conf'),
                                                   'splash.screen.enabled'))]
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
