#!/usr/bin/env python3
"""CozOS 0.6.2 upgrade-aware KNULLI splash helper."""
import sys
from pathlib import Path
import rootsplash as legacy

VERSION='0.6.2'
legacy.VERSION=VERSION


def install():
    payload=legacy.SOURCE.read_bytes()
    if legacy.png_size(payload)!=(640,480):
        raise RuntimeError('CozOS splash must be exactly 640x480.')
    target,virtual=legacy.select_target()
    installed_sha=legacy.digest(payload)
    prior=legacy.load_state()
    current=target.read_bytes(); current_sha=legacy.digest(current)
    try: target_size=legacy.png_size(current)
    except RuntimeError: raise RuntimeError('KNULLI selected a system splash that is not a valid PNG.')
    if target_size!=(640,480):
        raise RuntimeError('KNULLI system splash is '+str(target_size[0])+'x'+str(target_size[1])+'; refusing a 640x480 replacement.')

    if prior:
        if Path(prior.get('target',''))!=target:
            raise RuntimeError('KNULLI selected a different system splash; run CozOS Remove first.')
        # Current release already installed.
        if current_sha==installed_sha:
            overlay_output=legacy.save_overlay()
            prior.update({'version':VERSION,'phase':'installed','installed_sha256':installed_sha,'overlay_result':overlay_output})
            legacy.save_state(prior)
            return 'CozOS '+VERSION+' system boot splash is installed and persisted.'
        # Upgrade path: accept either the untouched original image OR the
        # checksum-verified image previously installed by CozOS. This is what
        # allows 0.4.x/0.5.x artwork to be replaced by 0.6.0 without treating
        # CozOS itself as an outside/manual edit.
        allowed={prior.get('original_sha256'),prior.get('installed_sha256')}
        if current_sha not in allowed:
            raise RuntimeError('System splash changed outside CozOS; refusing to overwrite it.')
        info=prior
    else:
        backup=legacy.STATE/('rootfs-splash-original-'+current_sha[:12]+'.png')
        if backup.exists() and legacy.digest(backup.read_bytes())!=current_sha:
            raise RuntimeError('Existing system-splash backup checksum mismatch.')
        if not backup.exists(): legacy.atomic(backup,current,0o600)
        info={'version':VERSION,'phase':'prepared','target':str(target),'virtual_size':virtual,
              'backup':str(backup),'original_sha256':current_sha,
              'original_mode':target.stat().st_mode & 0o777,'installed_sha256':installed_sha}
        legacy.save_state(info)

    legacy.atomic(target,payload,int(info.get('original_mode',0o644)))
    if legacy.digest(target.read_bytes())!=installed_sha:
        raise RuntimeError('Installed system splash failed checksum verification.')
    try:
        overlay_output=legacy.save_overlay()
    except Exception as first_error:
        original=Path(info['backup']).read_bytes()
        legacy.atomic(target,original,int(info.get('original_mode',0o644)))
        try: legacy.save_overlay()
        except Exception as rollback_error:
            raise RuntimeError(str(first_error)+'; live image was restored, but overlay rollback also failed: '+str(rollback_error))
        raise RuntimeError(str(first_error)+'; original image was restored and persisted.')
    info.update({'version':VERSION,'phase':'installed','installed_sha256':installed_sha,'overlay_result':overlay_output})
    legacy.save_state(info)
    return 'CozOS '+VERSION+' replaced '+str(target)+' and saved the KNULLI overlay. Reboot to see it.'


def main():
    action=sys.argv[1] if len(sys.argv)>1 else 'status'
    try:
        if action=='install': print(install()); return 0
        if action=='remove': print(legacy.remove()); return 0
        if action=='status': return legacy.status()
        raise RuntimeError('Unknown action: '+action)
    except Exception as exc:
        message='CozOS system-splash stopped: '+str(exc)
        legacy.STATE.mkdir(parents=True,exist_ok=True)
        legacy.atomic(legacy.STATE/'rootfs-splash-last-action.txt',message.encode())
        print(message); return 1

if __name__=='__main__': sys.exit(main())
