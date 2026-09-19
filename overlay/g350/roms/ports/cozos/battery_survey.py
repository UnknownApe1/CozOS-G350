#!/usr/bin/env python3
"""Read-only BATLEXP G350/RK817 battery survey logger for CozOS."""
import csv
import datetime
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import zipfile

VERSION = '0.6.3'
ROOT = Path(os.environ.get('COZOS_ROOT', os.environ.get('COZOS_TEST_ROOT', '/')))
STATE = ROOT / 'userdata/system/cozos'
SURVEYS = STATE / 'battery-survey'
PID_FILE = STATE / 'battery-survey.pid'
ACTIVE_FILE = STATE / 'battery-survey-active'
LATEST_ZIP = STATE / 'battery-survey-latest.zip'
INTERVAL = int(os.environ.get('COZOS_BATTERY_INTERVAL', '60'))

FIELDS = [
    'timestamp_utc', 'uptime_seconds', 'supply', 'status',
    'driver_capacity_percent', 'knulli_visible_percent',
    'voltage_now', 'voltage_avg', 'voltage_ocv',
    'current_now', 'current_avg', 'charge_now', 'charge_full',
    'charge_full_design', 'energy_now', 'energy_full',
    'power_now', 'temp', 'cycle_count', 'health', 'present', 'online',
]


def text(path):
    try:
        return path.read_text(errors='replace').replace('\x00', '').strip()
    except OSError:
        return ''


def atomic(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.cozos-tmp')
    with temporary.open('wb') as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def logger_process(pid):
    """Avoid signalling an unrelated process after a stale PID is reused."""
    if not alive(pid):
        return False
    cmdline = ROOT / 'proc' / str(pid) / 'cmdline'
    try:
        command = cmdline.read_bytes().replace(b'\0', b' ').decode(errors='replace')
    except OSError:
        return False
    return 'battery_survey.py' in command and ' run ' in (' ' + command + ' ')


def battery_supply():
    base = ROOT / 'sys/class/power_supply'
    candidates = []
    for path in sorted(base.glob('*')):
        kind = text(path / 'type').lower()
        name = text(path / 'name') or path.name
        if kind == 'battery':
            candidates.insert(0, (path, name))
        elif 'bat' in path.name.lower() or 'battery' in name.lower():
            candidates.append((path, name))
    if not candidates:
        raise RuntimeError('No battery power-supply directory was found.')
    return candidates[0]


def sample():
    path, name = battery_supply()
    values = {key: text(path / key) for key in (
        'status', 'capacity', 'voltage_now', 'voltage_avg', 'voltage_ocv',
        'current_now', 'current_avg', 'charge_now', 'charge_full',
        'charge_full_design', 'energy_now', 'energy_full', 'power_now',
        'temp', 'cycle_count', 'health', 'present', 'online')}
    uptime = text(ROOT / 'proc/uptime').split()
    return {
        'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'uptime_seconds': uptime[0] if uptime else '',
        'supply': name,
        'status': values['status'],
        'driver_capacity_percent': values['capacity'],
        'knulli_visible_percent': text(ROOT / 'tmp/battery.percent'),
        'voltage_now': values['voltage_now'],
        'voltage_avg': values['voltage_avg'],
        'voltage_ocv': values['voltage_ocv'],
        'current_now': values['current_now'],
        'current_avg': values['current_avg'],
        'charge_now': values['charge_now'],
        'charge_full': values['charge_full'],
        'charge_full_design': values['charge_full_design'],
        'energy_now': values['energy_now'],
        'energy_full': values['energy_full'],
        'power_now': values['power_now'],
        'temp': values['temp'],
        'cycle_count': values['cycle_count'],
        'health': values['health'],
        'present': values['present'],
        'online': values['online'],
    }


def device_tree_battery():
    base = ROOT / 'sys/firmware/devicetree/base'
    output = []
    if not base.exists():
        return output
    wanted = ('compatible', 'ocv_table', 'design_capacity', 'design_qmax',
              'bat_res', 'power_off_thresd', 'sample_res', 'max_chrg_voltage',
              'max_chrg_current', 'min_input_voltage', 'max_input_current')
    for directory, _, files in os.walk(base):
        path = Path(directory)
        compatible = text(path / 'compatible')
        if not any(word in (compatible + ' ' + path.name).lower()
                   for word in ('battery', 'charger', 'rk817')):
            continue
        props = {}
        for name in wanted:
            prop = path / name
            if name not in files:
                continue
            data = prop.read_bytes()
            if name == 'compatible':
                props[name] = data.rstrip(b'\0').decode(errors='replace').replace('\0', ', ')
            elif len(data) % 4 == 0:
                props[name] = [int.from_bytes(data[i:i + 4], 'big')
                               for i in range(0, len(data), 4)]
        output.append({'path': str(path.relative_to(base)), 'properties': props})
    return output


def metadata():
    path, name = battery_supply()
    uevent = {}
    for line in text(path / 'uevent').splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            uevent[key] = value
    return {
        'survey_version': VERSION,
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'device_model': text(ROOT / 'sys/firmware/devicetree/base/model'),
        'os_release': text(ROOT / 'etc/os-release'),
        'kernel': text(ROOT / 'proc/version'),
        'battery_supply_path': str(path),
        'battery_supply_name': name,
        'battery_uevent_at_start': uevent,
        'device_tree_battery': device_tree_battery(),
        'batteryplus_config': text(ROOT / 'etc/batteryplus/batteryplus.conf'),
        'batteryplus_map_at_start': text(
            ROOT / 'userdata/system/configs/batteryplus/batteryplus-voltage.map'),
        'batteryplus_restore_at_start': text(
            ROOT / 'userdata/system/configs/batteryplus/batteryplus-restore.state'),
        'batteryplus_calibrated_at_start': (
            ROOT / 'userdata/system/configs/batteryplus/batteryplus-calibrated').exists(),
        'sample_interval_seconds': INTERVAL,
    }


def append_sample(csv_path, row):
    new = not csv_path.exists()
    with csv_path.open('a', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if new:
            writer.writeheader()
        writer.writerow(row)
        handle.flush()
        os.fsync(handle.fileno())


def start():
    if PID_FILE.exists():
        try:
            pid = int(text(PID_FILE))
        except ValueError:
            pid = 0
        if pid and logger_process(pid):
            return 'Battery survey is already running (PID ' + str(pid) + ').'
        PID_FILE.unlink(missing_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    session = SURVEYS / stamp
    session.mkdir(parents=True, exist_ok=False)
    atomic(session / 'metadata.json', json.dumps(metadata(), indent=2).encode())
    atomic(ACTIVE_FILE, str(session).encode())
    command = [sys.executable, str(Path(__file__).resolve()), 'run', str(session)]
    error_log = (session / 'logger-errors.txt').open('ab')
    try:
        proc = subprocess.Popen(command, stdout=subprocess.DEVNULL,
                                stderr=error_log, start_new_session=True)
    finally:
        error_log.close()
    for _ in range(20):
        if PID_FILE.exists() and logger_process(proc.pid):
            return ('Battery survey started. Charge/unplug and use normally; '
                    'run Stop and Package after the discharge test.')
        time.sleep(0.1)
    raise RuntimeError('Battery survey logger did not start.')


def run(session):
    running = True
    def stop_signal(_signum, _frame):
        nonlocal running
        running = False
    signal.signal(signal.SIGTERM, stop_signal)
    signal.signal(signal.SIGINT, stop_signal)
    atomic(PID_FILE, str(os.getpid()).encode())
    csv_path = session / 'battery.csv'
    try:
        while running:
            append_sample(csv_path, sample())
            deadline = time.monotonic() + INTERVAL
            while running and time.monotonic() < deadline:
                time.sleep(min(1, max(0, deadline - time.monotonic())))
    finally:
        if text(PID_FILE) == str(os.getpid()):
            PID_FILE.unlink(missing_ok=True)


def stop_logger():
    if not PID_FILE.exists():
        return False
    try:
        pid = int(text(PID_FILE))
    except ValueError:
        PID_FILE.unlink(missing_ok=True)
        return False
    if logger_process(pid):
        os.kill(pid, signal.SIGTERM)
        for _ in range(50):
            if not alive(pid):
                break
            time.sleep(0.1)
    PID_FILE.unlink(missing_ok=True)
    return True


def validated_session(value):
    if not value:
        return None
    session = Path(value)
    try:
        if session.resolve().parent != SURVEYS.resolve():
            raise RuntimeError('Active battery survey path is outside CozOS state.')
    except OSError as exc:
        raise RuntimeError('Battery survey path cannot be resolved: ' + str(exc))
    return session


def package():
    STATE.mkdir(parents=True, exist_ok=True)
    session_name = text(ACTIVE_FILE)
    session = validated_session(session_name)
    if not session or not session.is_dir():
        sessions = sorted(path for path in SURVEYS.glob('*') if path.is_dir())
        if not sessions:
            raise RuntimeError('No battery survey session exists.')
        session = sessions[-1]
    snapshot_path = session / 'final-snapshot.json'
    final = metadata()
    final['sample_at_package'] = sample()
    atomic(snapshot_path, json.dumps(final, indent=2).encode())
    temporary = LATEST_ZIP.with_name(LATEST_ZIP.name + '.cozos-tmp')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(session.rglob('*')):
            if path.is_file():
                archive.write(path, 'battery-survey/' + path.name)
    os.replace(temporary, LATEST_ZIP)
    ACTIVE_FILE.unlink(missing_ok=True)
    return str(LATEST_ZIP)


def survey_status():
    running = False
    pid = 0
    try:
        pid = int(text(PID_FILE))
        running = logger_process(pid)
    except ValueError:
        pass
    session = validated_session(text(ACTIVE_FILE))
    if not session or not session.is_dir():
        sessions = sorted(path for path in SURVEYS.glob('*') if path.is_dir())
        session = sessions[-1] if sessions else None
    samples = 0
    if session:
        csv_path = session / 'battery.csv'
        try:
            with csv_path.open(newline='') as handle:
                samples = max(0, sum(1 for _ in handle) - 1)
        except OSError:
            pass
    lines = [
        'Battery survey logger: ' + (('RUNNING (PID ' + str(pid) + ')') if running else 'STOPPED'),
        'Latest session: ' + (str(session) if session else 'none'),
        'Recorded samples: ' + str(samples),
        'Packaged survey: ' + (str(LATEST_ZIP) if LATEST_ZIP.is_file() else 'none'),
        '',
        'This tool is read-only for battery hardware and KNULLI configuration.',
    ]
    return '\n'.join(lines)


def snapshot():
    STATE.mkdir(parents=True, exist_ok=True)
    report = metadata()
    report['sample'] = sample()
    target = STATE / 'battery-snapshot.json'
    atomic(target, json.dumps(report, indent=2).encode())
    return 'Battery snapshot saved: ' + str(target)


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'snapshot'
    try:
        if action == 'start':
            message = start()
        elif action == 'run':
            run(Path(sys.argv[2]))
            return 0
        elif action == 'stop-package':
            stopped = stop_logger()
            target = package()
            message = ('Battery survey stopped. ' if stopped else 'Logger was not running. ') + \
                      'Upload this file: ' + target
        elif action == 'stop':
            message = ('Battery survey stopped.' if stop_logger()
                       else 'Battery survey logger was not running.')
        elif action == 'snapshot':
            message = snapshot()
        elif action == 'status':
            message = survey_status()
        else:
            raise RuntimeError('Unknown action: ' + action)
        print(message)
        return 0
    except Exception as exc:
        message = 'CozOS battery survey stopped: ' + str(exc)
        STATE.mkdir(parents=True, exist_ok=True)
        atomic(STATE / 'battery-survey-last-action.txt', message.encode())
        print(message)
        return 1


if __name__ == '__main__':
    sys.exit(main())
