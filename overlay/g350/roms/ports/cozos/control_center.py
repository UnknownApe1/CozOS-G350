#!/usr/bin/env python3
"""CozOS G350 Control Center.

This is deliberately self-contained and uses only Python's standard library.
It never downloads or flashes a firmware image.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import termios
import textwrap
import time
import traceback
import tty
import zipfile

VERSION = '0.5.3'
ROOT = Path(os.environ.get('COZOS_ROOT', '/'))
PORTS = Path(__file__).resolve().parent.parent
COZOS = Path(__file__).resolve().parent
STATE = ROOT / 'userdata/system/cozos'
BACKUPS = STATE / 'backups'
REPO = 'https://github.com/UnknownApe1/CozOS-G350'

# Settings users commonly customize and which are safe to restore without
# touching ROMs, BIOS, saves, scraped media, or the rootfs overlay.
BACKUP_PATHS = (
    'userdata/system/knulli.conf',
    'userdata/system/batocera.conf',
    'userdata/system/configs/emulationstation/es_settings.cfg',
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic(path, data, mode=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.cozos-tmp')
    with temporary.open('wb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    if mode is not None:
        path.chmod(mode)


def read(path):
    try:
        return path.read_text(errors='replace').replace('\x00', '').strip()
    except OSError:
        return ''


def run_helper(name, action):
    command = [sys.executable, str(COZOS / name), action]
    result = subprocess.run(command, capture_output=True, text=True, timeout=900,
                            check=False, env=os.environ.copy())
    output = (result.stdout + '\n' + result.stderr).strip()
    return result.returncode, output or (name + ' returned no message.')


def installed_version():
    manifest = STATE / 'installed.json'
    try:
        return json.loads(manifest.read_text()).get('version', '<unknown>')
    except (OSError, ValueError, TypeError):
        return 'not installed'


def status():
    overlay_rc, overlay_text = run_helper('overlay.py', 'status')
    splash_rc, splash_text = run_helper('rootsplash.py', 'status')
    model = read(ROOT / 'sys/firmware/devicetree/base/model') or '<unavailable>'
    os_release = read(ROOT / 'etc/os-release')
    pretty = next((line.split('=', 1)[1].strip('"') for line in os_release.splitlines()
                   if line.startswith('PRETTY_NAME=')), '<unavailable>')
    lines = [
        'CozOS G350 Control Center ' + VERSION,
        'Installed version: ' + installed_version(),
        'Device: ' + model,
        'Base OS: ' + pretty,
        '',
        'Overlay diagnostics: ' + ('PASS' if overlay_rc == 0 else 'FAILED'),
        overlay_text,
        '',
        'Boot splash: ' + ('PASS' if splash_rc == 0 else 'FAILED'),
        splash_text,
    ]
    report = '\n'.join(lines).rstrip() + '\n'
    STATE.mkdir(parents=True, exist_ok=True)
    atomic(STATE / 'control-center-report.txt', report.encode())
    return max(overlay_rc, splash_rc), report


def install_or_repair():
    steps = [('CozOS settings and controls', 'overlay.py', 'install'),
             ('Legacy logo cleanup', 'bootlogo.py', 'remove'),
             ('KNULLI boot splash', 'rootsplash.py', 'install')]
    messages = []
    for label, helper, action in steps:
        rc, output = run_helper(helper, action)
        messages.append(label + ':\n' + output)
        if rc:
            return rc, '\n\n'.join(messages) + '\n\nStopped safely at the failed step.'
    return 0, '\n\n'.join(messages) + '\n\nReboot normally to finish applying CozOS.'


def remove_cozos():
    steps = [('KNULLI boot splash', 'rootsplash.py', 'remove'),
             ('Legacy logo cleanup', 'bootlogo.py', 'remove'),
             ('CozOS settings and controls', 'overlay.py', 'remove')]
    messages = []
    result = 0
    for label, helper, action in steps:
        rc, output = run_helper(helper, action)
        messages.append(label + ':\n' + output)
        result = result or rc
    ending = ('Reboot normally to finish rollback.' if result == 0 else
              'One or more rollback checks stopped. Nothing unverified was overwritten.')
    return result, '\n\n'.join(messages) + '\n\n' + ending


def create_backup(label='settings'):
    BACKUPS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%SZ')
    destination = BACKUPS / ('CozOS-G350-' + label + '-' + stamp + '.zip')
    entries = []
    for relative in BACKUP_PATHS:
        source = ROOT / relative
        if source.is_file() and not source.is_symlink():
            payload = source.read_bytes()
            entries.append({'path': relative, 'sha256': digest(payload),
                            'mode': source.stat().st_mode & 0o777,
                            'size': len(payload)})
    manifest = {
        'format': 1,
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'cozos_version': VERSION,
        'device': read(ROOT / 'sys/firmware/devicetree/base/model'),
        'files': entries,
    }
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('manifest.json', json.dumps(manifest, indent=2, sort_keys=True) + '\n')
        for entry in entries:
            archive.write(ROOT / entry['path'], 'files/' + entry['path'])
    if not entries:
        destination.unlink(missing_ok=True)
        return 1, 'No supported KNULLI settings files were found; no empty backup was created.'
    return 0, ('Settings backup created and checksum-indexed:\n' + str(destination) +
               '\n\nROMs, BIOS, saves, and media were not copied or changed.')


def backups():
    if not BACKUPS.exists():
        return []
    return sorted(BACKUPS.glob('CozOS-G350-settings-*.zip'), reverse=True)


def validate_backup(path):
    allowed = set(BACKUP_PATHS)
    with zipfile.ZipFile(path, 'r') as archive:
        manifest = json.loads(archive.read('manifest.json'))
        if manifest.get('format') != 1 or not isinstance(manifest.get('files'), list):
            raise RuntimeError('Unsupported or invalid CozOS backup manifest.')
        checked = []
        for entry in manifest['files']:
            relative = entry.get('path', '')
            pure = PurePosixPath(relative)
            if relative not in allowed or pure.is_absolute() or '..' in pure.parts:
                raise RuntimeError('Backup contains an unsafe path: ' + repr(relative))
            payload = archive.read('files/' + relative)
            if digest(payload) != entry.get('sha256'):
                raise RuntimeError('Backup checksum failed: ' + relative)
            checked.append((relative, payload, int(entry.get('mode', 0o644))))
    return checked


def restore_latest():
    available = backups()
    if not available:
        return 1, 'No CozOS settings backup is available to restore.'
    source = available[0]
    try:
        checked = validate_backup(source)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, RuntimeError) as exc:
        return 1, 'Restore stopped before writing anything: ' + str(exc)
    rc, safety = create_backup('pre-restore')
    if rc:
        return rc, 'Restore stopped because the pre-restore safety backup failed:\n' + safety
    for relative, payload, mode in checked:
        atomic(ROOT / relative, payload, mode)
    return 0, ('Restored ' + str(len(checked)) + ' verified settings file(s) from:\n' +
               str(source) + '\n\nA pre-restore safety backup was created first. Reboot normally.')


def update_info():
    return 0, ('Package version: ' + VERSION + '\nInstalled version: ' + installed_version() +
               '\n\nUpdates: ' + REPO + '/tree/knulli-main/releases\n\nCozOS updates are small overlay ZIPs. '
               'They are copied to SHARE/roms/ports; they are never flashed as firmware images.')


class UI:
    def __init__(self):
        self.interactive = sys.stdin.isatty() and sys.stdout.isatty()
        self.saved_terminal = None

    def start(self):
        if self.interactive:
            self.saved_terminal = termios.tcgetattr(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())
            sys.stdout.write('\x1b[?25l')
            sys.stdout.flush()

    def close(self):
        if self.saved_terminal is not None:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN,
                              self.saved_terminal)
            self.saved_terminal = None
        if self.interactive:
            sys.stdout.write('\x1b[0m\x1b[?25h\x1b[2J\x1b[H')
            sys.stdout.flush()

    @staticmethod
    def _screen(title, body, footer='D-pad: move   A/START: select   B: back'):
        # VaixTerm renders ordinary ANSI output more consistently than the
        # alternate-screen ncurses sequences emitted by dialog.
        lines = ['COZOS G350  |  CONTROL CENTER ' + VERSION,
                 '=' * 62, title, '-' * 62]
        lines.extend(body)
        lines.extend(['', '-' * 62, footer])
        sys.stdout.write('\x1b[2J\x1b[H' + '\n'.join(lines) + '\n')
        sys.stdout.flush()

    @staticmethod
    def _key():
        first = os.read(sys.stdin.fileno(), 1)
        if not first:
            return 'back'
        if first == b'\x1b':
            sequence = first
            # Arrow keys arrive as a short escape sequence. Give the PTY a
            # moment to deliver the remaining bytes without ever blocking.
            import select
            deadline = time.monotonic() + 0.08
            while time.monotonic() < deadline:
                ready, _, _ = select.select([sys.stdin], [], [], 0.01)
                if not ready:
                    continue
                sequence += os.read(sys.stdin.fileno(), 1)
                if len(sequence) >= 3:
                    break
            return {b'\x1b[A': 'up', b'\x1b[B': 'down',
                    b'\x1b[C': 'right', b'\x1b[D': 'left'}.get(sequence, 'back')
        if first in (b'\r', b'\n', b' '):
            return 'select'
        if first in (b'\x08', b'\x7f', b'q', b'Q'):
            return 'back'
        return first.decode(errors='ignore').lower()

    @staticmethod
    def _wrapped(message, width=70):
        lines = []
        for line in message.splitlines() or ['']:
            lines.extend(textwrap.wrap(line, width=width,
                                       replace_whitespace=False,
                                       drop_whitespace=False) or [''])
        return lines

    def message(self, title, message):
        if not self.interactive:
            print('\n== ' + title + ' ==\n' + message)
            return
        lines = self._wrapped(message)
        offset = 0
        page_size = 18
        while True:
            page = lines[offset:offset + page_size]
            if offset:
                page.insert(0, '^ more above ^')
            if offset + page_size < len(lines):
                page.append('v more below v')
            self._screen(title, page, 'D-pad: scroll   A/START/B: return')
            key = self._key()
            if key == 'up':
                offset = max(0, offset - page_size)
            elif key == 'down':
                offset = min(max(0, len(lines) - page_size), offset + page_size)
            elif key in ('select', 'back'):
                return

    def confirm(self, title, message):
        if not self.interactive:
            answer = input(message + ' [y/N] ').strip().lower()
            return answer in ('y', 'yes')
        yes = False
        while True:
            choices = ('  YES  ' if yes else '> NO   ')
            if yes:
                choices = '> YES     NO   '
            else:
                choices = '  YES   > NO  '
            self._screen(title, self._wrapped(message) + ['', choices],
                         'D-pad: choose   A/START: confirm   B: cancel')
            key = self._key()
            if key in ('left', 'right', 'up', 'down'):
                yes = not yes
            elif key == 'select':
                return yes
            elif key == 'back':
                return False

    def menu(self):
        items = [
            ('1', 'Install or repair CozOS ' + VERSION),
            ('2', 'Status and diagnostics'),
            ('3', 'Back up KNULLI settings'),
            ('4', 'Restore latest settings backup'),
            ('5', 'Update and version information'),
            ('6', 'Remove CozOS / complete rollback'),
            ('0', 'Exit'),
        ]
        if not self.interactive:
            print('\nCozOS G350 Control Center ' + VERSION)
            for key, description in items:
                print('  ' + key + '. ' + description)
            return input('Selection: ').strip()
        selected = 0
        while True:
            body = []
            for index, (_, description) in enumerate(items):
                body.append(('> ' if index == selected else '  ') + description)
            self._screen('Choose an action', body)
            key = self._key()
            if key == 'up':
                selected = (selected - 1) % len(items)
            elif key == 'down':
                selected = (selected + 1) % len(items)
            elif key == 'select':
                return items[selected][0]
            elif key == 'back':
                return '0'
            elif key in {item[0] for item in items}:
                return key


def main():
    ui = UI()
    ui.start()
    try:
        while True:
            choice = ui.menu()
            if choice == '0' or not choice:
                return 0
            if choice == '1':
                rc, message = install_or_repair()
                ui.message('Install / repair' if rc == 0 else 'Install stopped', message)
            elif choice == '2':
                rc, message = status()
                ui.message('Status' if rc == 0 else 'Diagnostics found a problem', message)
            elif choice == '3':
                rc, message = create_backup()
                ui.message('Settings backup' if rc == 0 else 'Backup stopped', message)
            elif choice == '4':
                available = backups()
                if not available:
                    ui.message('Restore', 'No CozOS settings backup is available to restore.')
                elif ui.confirm('Restore settings', 'Restore the newest verified settings backup?\n\n' +
                                str(available[0]) + '\n\nA safety backup will be created first.'):
                    rc, message = restore_latest()
                    ui.message('Restore complete' if rc == 0 else 'Restore stopped', message)
            elif choice == '5':
                _, message = update_info()
                ui.message('Version and updates', message)
            elif choice == '6':
                if ui.confirm('Complete rollback', 'Remove CozOS and restore its verified backups?\n\n'
                              'ROMs, BIOS, saves, save states, and media are not deleted.'):
                    rc, message = remove_cozos()
                    ui.message('Rollback complete' if rc == 0 else 'Rollback stopped', message)
            else:
                ui.message('CozOS', 'Unknown selection: ' + choice)
    finally:
        ui.close()


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        STATE.mkdir(parents=True, exist_ok=True)
        report = traceback.format_exc()
        atomic(STATE / 'control-center-error.txt', report.encode())
        sys.stderr.write('\nCozOS Control Center stopped unexpectedly.\n' + report +
                         '\nError log: ' + str(STATE / 'control-center-error.txt') + '\n')
        sys.stderr.flush()
        time.sleep(8)
        raise
