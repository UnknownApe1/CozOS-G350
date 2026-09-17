#!/usr/bin/env python3
"""CozOS G350 Rockchip boot-image manager.

KNULLI's Rockchip progress-bar code loads /boot/logo_<width>x<height>.bmp,
where width/height come from /dev/fb0. On the G350 this is normally
/boot/logo_640x480.bmp. This helper installs the packaged CozOS artwork there,
backs up an existing image when present, and safely restores/removes it.
"""
import hashlib
import fcntl
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import zlib

VERSION = '0.4.3'
ROOT = Path(os.environ.get('COZOS_ROOT', '/'))
STATE = ROOT / 'userdata/system/cozos'
STATE_FILE = STATE / 'bootlogo.json'
SOURCE = Path(__file__).with_name('assets') / 'cozos-splash-640x480.png'
DEFAULT_SIZE = (640, 480)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.cozos-tmp')
    with temp.open('wb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def read_text(path):
    try:
        return path.read_text(errors='replace').strip()
    except OSError:
        return ''


def framebuffer_size():
    """Return active xres/yres, matching KNULLI progressbar_rk.cpp."""
    # FBIOGET_VSCREENINFO is exactly what KNULLI's Rockchip progressbar uses.
    # The first four uint32 fields are xres, yres, xres_virtual, yres_virtual.
    if ROOT == Path('/'):
        try:
            with open('/dev/fb0', 'rb', buffering=0) as fb:
                buf = bytearray(160)
                fcntl.ioctl(fb.fileno(), 0x4600, buf, True)
                xres, yres, _, _ = struct.unpack_from('=IIII', buf, 0)
                if xres > 0 and yres > 0:
                    return (xres, yres), 'FBIOGET_VSCREENINFO'
        except OSError:
            pass

        # fbset is a secondary source for active geometry when installed.
        try:
            result = subprocess.run(['fbset', '-fb', '/dev/fb0'], capture_output=True,
                                    text=True, timeout=3, check=False)
            match = re.search(r'geometry\s+(\d+)\s+(\d+)\s+', result.stdout)
            if match:
                size = (int(match.group(1)), int(match.group(2)))
                if size[0] > 0 and size[1] > 0:
                    return size, 'fbset'
        except (OSError, subprocess.SubprocessError):
            pass

    # virtual_size can be taller than the visible panel on double-buffered
    # framebuffers, so use it only if it is the known G350 640x480 geometry.
    text = read_text(ROOT / 'sys/class/graphics/fb0/virtual_size')
    match = re.search(r'(\d+)\s*,\s*(\d+)', text)
    if match:
        size = (int(match.group(1)), int(match.group(2)))
        if size == DEFAULT_SIZE:
            return size, 'sysfs virtual_size'

    # overlay.py hardware-gates this package to G350/BATLEXP. Its panel and the
    # packaged artwork are 640x480, so this is a safe final device fallback.
    return DEFAULT_SIZE, 'G350 fallback'


def target_for_size(size):
    return ROOT / 'boot' / f'logo_{size[0]}x{size[1]}.bmp'


def paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def png_to_bmp24(payload, expected_size):
    """Decode a normal non-interlaced 8-bit PNG and return a 24-bit BMP."""
    if not payload.startswith(b'\x89PNG\r\n\x1a\n'):
        raise RuntimeError('Packaged CozOS artwork is not a PNG.')
    pos = 8
    width = height = bit_depth = color_type = interlace = None
    palette = None
    compressed = bytearray()
    while pos + 12 <= len(payload):
        length = int.from_bytes(payload[pos:pos + 4], 'big')
        kind = payload[pos + 4:pos + 8]
        data = payload[pos + 8:pos + 8 + length]
        if pos + 12 + length > len(payload):
            raise RuntimeError('Packaged CozOS PNG is truncated.')
        if kind == b'IHDR':
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(
                '>IIBBBBB', data)
            if compression != 0 or filtering != 0:
                raise RuntimeError('Unsupported PNG compression/filter method.')
        elif kind == b'PLTE':
            if len(data) % 3:
                raise RuntimeError('Invalid PNG palette.')
            palette = [tuple(data[i:i + 3]) for i in range(0, len(data), 3)]
        elif kind == b'IDAT':
            compressed.extend(data)
        elif kind == b'IEND':
            break
        pos += 12 + length
    if (width, height) != tuple(expected_size):
        raise RuntimeError(
            f'CozOS boot artwork is {width}x{height}, but framebuffer is '
            f'{expected_size[0]}x{expected_size[1]}; refusing to stretch it.')
    if bit_depth != 8 or interlace != 0:
        raise RuntimeError('CozOS boot artwork must be 8-bit and non-interlaced.')
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type)
    if channels is None:
        raise RuntimeError('Unsupported CozOS PNG color type: ' + str(color_type))
    if color_type == 3 and not palette:
        raise RuntimeError('Indexed CozOS PNG has no palette.')
    raw = zlib.decompress(bytes(compressed))
    row_bytes = width * channels
    expected = height * (row_bytes + 1)
    if len(raw) != expected:
        raise RuntimeError('Unexpected CozOS PNG scanline size.')
    rows = []
    prior = bytearray(row_bytes)
    offset = 0
    for _ in range(height):
        filter_type = raw[offset]
        offset += 1
        scan = bytearray(raw[offset:offset + row_bytes])
        offset += row_bytes
        recon = bytearray(row_bytes)
        for x, value in enumerate(scan):
            left = recon[x - channels] if x >= channels else 0
            up = prior[x]
            upper_left = prior[x - channels] if x >= channels else 0
            if filter_type == 0:
                value += 0
            elif filter_type == 1:
                value += left
            elif filter_type == 2:
                value += up
            elif filter_type == 3:
                value += (left + up) >> 1
            elif filter_type == 4:
                value += paeth(left, up, upper_left)
            else:
                raise RuntimeError('Unsupported PNG filter type: ' + str(filter_type))
            recon[x] = value & 0xff
        prior = recon
        rgb = bytearray()
        if color_type == 0:
            for value in recon:
                rgb.extend((value, value, value))
        elif color_type == 2:
            rgb.extend(recon)
        elif color_type == 3:
            for index in recon:
                if index >= len(palette):
                    raise RuntimeError('PNG palette index is out of range.')
                rgb.extend(palette[index])
        elif color_type == 4:
            for i in range(0, len(recon), 2):
                value = recon[i]
                rgb.extend((value, value, value))
        elif color_type == 6:
            for i in range(0, len(recon), 4):
                rgb.extend(recon[i:i + 3])
        rows.append(bytes(rgb))

    stride = ((width * 3 + 3) // 4) * 4
    pixel_size = stride * height
    header = (
        b'BM' + struct.pack('<IHHI', 54 + pixel_size, 0, 0, 54) +
        struct.pack('<IIIHHIIIIII', 40, width, height, 1, 24, 0,
                    pixel_size, 2835, 2835, 0, 0)
    )
    pad = b'\x00' * (stride - width * 3)
    pixels = bytearray()
    for row in reversed(rows):
        for i in range(0, len(row), 3):
            r, g, b = row[i:i + 3]
            pixels.extend((b, g, r))
        pixels.extend(pad)
    return header + bytes(pixels)


def remount_boot(writable):
    if ROOT != Path('/'):
        return
    mode = 'rw' if writable else 'ro'
    subprocess.run(['mount', '-o', 'remount,' + mode, '/boot'], check=True)


def write_boot_target(target, data, mode=0o644):
    remount_boot(True)
    try:
        atomic(target, data)
        target.chmod(mode)
    finally:
        remount_boot(False)


def delete_boot_target(target):
    remount_boot(True)
    try:
        target.unlink(missing_ok=True)
    finally:
        remount_boot(False)


def load_state():
    if not STATE_FILE.exists():
        return None
    return json.loads(STATE_FILE.read_text())


def save_state(info):
    STATE.mkdir(parents=True, exist_ok=True)
    atomic(STATE_FILE, json.dumps(info, indent=2, sort_keys=True).encode())


def install():
    if not SOURCE.exists():
        raise RuntimeError('Packaged CozOS boot artwork is missing: ' + str(SOURCE))
    size, size_source = framebuffer_size()
    target = target_for_size(size)
    payload = SOURCE.read_bytes()
    bmp = png_to_bmp24(payload, size)
    installed_sha = digest(bmp)
    prior = load_state()

    # Migrate a stale failed 0.4.2 record only if it never changed its old target.
    if prior and prior.get('target') == '/boot/bootlogo.bmp':
        old_target = ROOT / 'boot/bootlogo.bmp'
        old_installed = prior.get('installed_sha256')
        if old_target.exists() and old_installed and digest(old_target.read_bytes()) == old_installed:
            raise RuntimeError('A previous CozOS build actually modified /boot/bootlogo.bmp; run its Remove first.')
        STATE_FILE.unlink()
        prior = None

    if prior:
        prior_target = Path(prior['target'])
        current_sha = digest(prior_target.read_bytes()) if prior_target.exists() else None
        if (prior_target == target and current_sha == installed_sha):
            prior['version'] = VERSION
            prior['phase'] = 'installed'
            prior['resolution_source'] = size_source
            save_state(prior)
            return f'CozOS {VERSION} boot image is already installed at {target}.'
        if prior_target != target:
            raise RuntimeError('Framebuffer/boot-logo target changed since the previous install; run Remove before reinstalling.')
        if prior.get('phase') == 'prepared':
            original_sha = prior.get('original_sha256')
            if (prior.get('original_exists') and current_sha == original_sha) or (
                    not prior.get('original_exists') and current_sha is None):
                mode = int(prior.get('original_mode', 0o644))
                write_boot_target(target, bmp, mode)
                prior.update({'version': VERSION, 'installed_sha256': installed_sha,
                              'phase': 'installed', 'resolution_source': size_source})
                save_state(prior)
                return f'CozOS {VERSION} boot image installed at {target}; reboot to test it.'
        raise RuntimeError(target.name + ' changed after CozOS prepared it; refusing to overwrite that newer edit.')

    original_exists = target.exists()
    original_sha = None
    original_mode = 0o644
    backup = None
    if original_exists:
        original = target.read_bytes()
        original_sha = digest(original)
        original_mode = target.stat().st_mode & 0o777
        backup = STATE / ('boot-logo-original-' + original_sha[:12] + '.bmp')
        if backup.exists():
            if digest(backup.read_bytes()) != original_sha:
                raise RuntimeError('Existing boot-image backup has an unexpected checksum.')
        else:
            atomic(backup, original)
            backup.chmod(0o600)

    info = {
        'version': VERSION,
        'phase': 'prepared',
        'target': str(target),
        'width': size[0],
        'height': size[1],
        'resolution_source': size_source,
        'backup': str(backup) if backup else None,
        'original_exists': original_exists,
        'original_sha256': original_sha,
        'original_mode': original_mode,
        'source_png_sha256': digest(payload),
        'installed_sha256': installed_sha,
        'format': f'BMP {size[0]}x{size[1]} 24-bit uncompressed',
    }
    # Store rollback metadata first. If power is lost during /boot write, Remove
    # can still determine whether it should restore or delete the target.
    save_state(info)
    write_boot_target(target, bmp, original_mode)
    if not target.exists() or digest(target.read_bytes()) != installed_sha:
        raise RuntimeError('Installed ' + target.name + ' failed checksum verification.')
    info['phase'] = 'installed'
    save_state(info)
    action = 'replaced' if original_exists else 'created'
    return f'CozOS {VERSION} boot image {action} {target}; reboot to test it.'


def remove():
    info = load_state()
    if not info:
        return 'No CozOS boot-image installation record found; /boot was not changed by this module.'
    target = Path(info['target'])
    installed_sha = info.get('installed_sha256')
    current_sha = digest(target.read_bytes()) if target.exists() else None

    if info.get('phase') == 'prepared':
        # Installation may have stopped before /boot changed.
        if info.get('original_exists') and current_sha == info.get('original_sha256'):
            STATE_FILE.unlink()
            return 'Original G350 boot image is already active.'
        if not info.get('original_exists') and current_sha is None:
            STATE_FILE.unlink()
            return 'No pre-existing boot image and CozOS target was never created.'

    if current_sha != installed_sha:
        raise RuntimeError(target.name + ' was edited after CozOS; refusing to overwrite/delete that newer file.')

    if info.get('original_exists'):
        backup_name = info.get('backup')
        if not backup_name:
            raise RuntimeError('Original boot-image backup path is missing; refusing to alter /boot.')
        backup = Path(backup_name)
        if not backup.exists():
            raise RuntimeError('Original boot-image backup is missing; refusing to alter /boot.')
        original = backup.read_bytes()
        if digest(original) != info.get('original_sha256'):
            raise RuntimeError('Original boot-image backup checksum mismatch; refusing to alter /boot.')
        write_boot_target(target, original, int(info.get('original_mode', 0o644)))
        if digest(target.read_bytes()) != info.get('original_sha256'):
            raise RuntimeError('Restored boot image failed checksum verification.')
        result = 'Original G350 boot image restored and verified.'
    else:
        delete_boot_target(target)
        if target.exists():
            raise RuntimeError('Could not remove CozOS-created boot image.')
        result = 'CozOS-created G350 boot image removed; no original file existed.'

    STATE_FILE.unlink()
    return result


def status():
    size, size_source = framebuffer_size()
    detected_target = target_for_size(size)
    info = load_state()
    target = Path(info['target']) if info and info.get('target') else detected_target
    candidates = sorted((ROOT / 'boot').glob('logo_*x*.bmp')) if (ROOT / 'boot').exists() else []
    lines = [f'CozOS {VERSION} Rockchip boot-image status',
             f'framebuffer={size[0]}x{size[1]}',
             'resolution-source=' + size_source,
             'detected-target=' + str(detected_target),
             'managed-target=' + str(target),
             'logo-candidates=' + (', '.join(str(p) for p in candidates) if candidates else '<none>')]
    if target.exists():
        data = target.read_bytes()
        lines += ['target-present=True', 'target-sha256=' + digest(data),
                  'target-size=' + str(len(data))]
    else:
        lines += ['target-present=False']
    if not info:
        lines += ['managed=False', 'rollback-record=missing']
    else:
        lines += ['managed=True', 'version=' + str(info.get('version')),
                  'phase=' + str(info.get('phase')),
                  'expected-cozos-sha256=' + str(info.get('installed_sha256')),
                  'original-existed=' + str(info.get('original_exists')),
                  'original-sha256=' + str(info.get('original_sha256'))]
        backup_name = info.get('backup')
        if backup_name:
            backup = Path(backup_name)
            lines += ['backup=' + str(backup), 'backup-present=' + str(backup.exists())]
            if backup.exists():
                backup_sha = digest(backup.read_bytes())
                lines += ['backup-sha256=' + backup_sha,
                          'backup-verified=' + str(backup_sha == info.get('original_sha256'))]
        else:
            lines += ['backup=<not-needed>']
    text = '\n'.join(lines) + '\n'
    STATE.mkdir(parents=True, exist_ok=True)
    atomic(STATE / 'bootlogo-status.txt', text.encode())
    print(text, end='')
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
        message = 'CozOS boot-image stopped: ' + str(exc)
        STATE.mkdir(parents=True, exist_ok=True)
        atomic(STATE / 'bootlogo-last-action.txt', message.encode())
        print(message)
        return 1


if __name__ == '__main__':
    sys.exit(main())
