#!/usr/bin/env python3
"""CozOS G350 boot-logo manager for KNULLI RK3326 images.

The G350 RK3326 build removes KNULLI's normal userdata splash services, while
its early boot progress path reads /boot/bootlogo.bmp.  This helper converts
the packaged 640x480 PNG to a conservative 24-bit BMP, backs up the original
boot logo by checksum, installs the CozOS image, and restores the exact original
on removal.  It intentionally does not touch ROMs, saves, DTBs, kernels, or
bootloader binaries.
"""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import zlib

VERSION = '0.4.1'
ROOT = Path('/')
STATE = ROOT / 'userdata/system/cozos'
STATE_FILE = STATE / 'bootlogo.json'
TARGET = ROOT / 'boot/bootlogo.bmp'
SOURCE = Path(__file__).with_name('assets') / 'cozos-splash-640x480.png'


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


def paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def png_to_bmp24(payload):
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
    if (width, height) != (640, 480):
        raise RuntimeError('CozOS boot artwork must be exactly 640x480.')
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
                result = value
            elif filter_type == 1:
                result = value + left
            elif filter_type == 2:
                result = value + up
            elif filter_type == 3:
                result = value + ((left + up) >> 1)
            elif filter_type == 4:
                result = value + paeth(left, up, upper_left)
            else:
                raise RuntimeError('Unsupported PNG filter type: ' + str(filter_type))
            recon[x] = result & 0xff
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


def write_boot_target(data, mode=0o644):
    remount_boot(True)
    try:
        atomic(TARGET, data)
        TARGET.chmod(mode)
    finally:
        remount_boot(False)


def remove_boot_target():
    remount_boot(True)
    try:
        TARGET.unlink(missing_ok=True)
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
    bmp = png_to_bmp24(SOURCE.read_bytes())
    installed_sha = digest(bmp)
    prior = load_state()
    if prior:
        current_sha = digest(TARGET.read_bytes()) if TARGET.exists() else None
        if current_sha == installed_sha:
            if prior.get('phase') != 'installed':
                prior['phase'] = 'installed'
                save_state(prior)
            return 'CozOS 0.4.1 boot logo is already installed.'
        if prior.get('phase') == 'prepared' and current_sha == prior.get('original_sha256'):
            mode = int(prior.get('original_mode', 0o644))
            write_boot_target(bmp, mode)
            prior['installed_sha256'] = installed_sha
            prior['phase'] = 'installed'
            save_state(prior)
            return 'CozOS 0.4.1 boot logo installed; reboot to test it.'
        raise RuntimeError('bootlogo.bmp changed after CozOS prepared it; refusing to overwrite that newer edit.')
    if not TARGET.exists():
        raise RuntimeError('/boot/bootlogo.bmp is missing; no boot files were changed.')
    original = TARGET.read_bytes()
    original_sha = digest(original)
    original_mode = TARGET.stat().st_mode & 0o777
    backup = STATE / ('bootlogo-original-' + original_sha[:12] + '.bmp')
    if backup.exists():
        if digest(backup.read_bytes()) != original_sha:
            raise RuntimeError('Existing boot-logo backup has an unexpected checksum.')
    else:
        atomic(backup, original)
        backup.chmod(0o600)
    info = {
        'version': VERSION,
        'phase': 'prepared',
        'target': str(TARGET),
        'backup': str(backup),
        'original_exists': True,
        'original_sha256': original_sha,
        'original_mode': original_mode,
        'source_png_sha256': digest(SOURCE.read_bytes()),
        'installed_sha256': installed_sha,
        'format': 'BMP 640x480 24-bit',
    }
    # Persist rollback information before changing /boot, so an interrupted
    # install can still distinguish the original from the CozOS replacement.
    save_state(info)
    write_boot_target(bmp, original_mode)
    if digest(TARGET.read_bytes()) != installed_sha:
        raise RuntimeError('Installed bootlogo.bmp failed checksum verification.')
    info['phase'] = 'installed'
    save_state(info)
    return 'CozOS 0.4.1 boot logo installed; reboot to test the real RK3326 boot path.'


def remove():
    info = load_state()
    if not info:
        return 'No CozOS boot-logo installation record found; bootlogo.bmp was not changed.'
    backup = Path(info['backup'])
    if not backup.exists():
        raise RuntimeError('Original boot-logo backup is missing; refusing to alter /boot.')
    original = backup.read_bytes()
    if digest(original) != info.get('original_sha256'):
        raise RuntimeError('Original boot-logo backup checksum mismatch; refusing to alter /boot.')
    if TARGET.exists():
        current_sha = digest(TARGET.read_bytes())
        installed_sha = info.get('installed_sha256')
        if current_sha != installed_sha:
            # If installation stopped before replacement, the original is
            # already live and there is nothing destructive to undo.
            if info.get('phase') == 'prepared' and current_sha == info.get('original_sha256'):
                STATE_FILE.unlink()
                return 'Original G350 boot logo is already active.'
            raise RuntimeError('bootlogo.bmp was edited after CozOS; refusing to overwrite that newer file.')
    write_boot_target(original, int(info.get('original_mode', 0o644)))
    if digest(TARGET.read_bytes()) != info.get('original_sha256'):
        raise RuntimeError('Restored bootlogo.bmp failed checksum verification.')
    STATE_FILE.unlink()
    return 'Original G350 bootlogo.bmp restored and verified.'


def status():
    info = load_state()
    lines = ['CozOS 0.4.1 boot-logo status', 'target=' + str(TARGET)]
    if TARGET.exists():
        data = TARGET.read_bytes()
        lines += ['target-present=True', 'target-sha256=' + digest(data),
                  'target-size=' + str(len(data))]
    else:
        lines += ['target-present=False']
    if not info:
        lines += ['managed=False', 'rollback-record=missing']
    else:
        backup = Path(info['backup'])
        lines += ['managed=True', 'phase=' + str(info.get('phase')),
                  'expected-cozos-sha256=' + str(info.get('installed_sha256')),
                  'original-sha256=' + str(info.get('original_sha256')),
                  'backup=' + str(backup), 'backup-present=' + str(backup.exists())]
        if backup.exists():
            lines += ['backup-sha256=' + digest(backup.read_bytes()),
                      'backup-verified=' + str(digest(backup.read_bytes()) == info.get('original_sha256'))]
    text = '\n'.join(lines) + '\n'
    STATE.mkdir(parents=True, exist_ok=True)
    atomic(STATE / 'bootlogo-status.txt', text.encode())
    print(text, end='')
    return 0


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'status'
    try:
        if action == 'install':
            message = install()
            print(message)
            return 0
        if action == 'remove':
            message = remove()
            print(message)
            return 0
        if action == 'status':
            return status()
        raise RuntimeError('Unknown action: ' + action)
    except Exception as exc:
        message = 'CozOS boot-logo stopped: ' + str(exc)
        STATE.mkdir(parents=True, exist_ok=True)
        atomic(STATE / 'bootlogo-last-action.txt', message.encode())
        print(message)
        return 1


if __name__ == '__main__':
    sys.exit(main())
