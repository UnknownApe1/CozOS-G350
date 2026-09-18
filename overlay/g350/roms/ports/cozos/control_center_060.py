#!/usr/bin/env python3
"""CozOS 0.6.3 Control Center management layer."""
import hashlib, json, os, shutil, subprocess, sys, traceback
from pathlib import Path
import control_center as legacy
import updater

VERSION='0.6.3'
legacy.VERSION=VERSION

TOOLS_LAUNCHER=legacy.ROOT/'userdata/roms/tools/CozOS Control Center.sh'
PORTS_LAUNCHER=legacy.ROOT/'userdata/roms/ports/CozOS Control Center.sh'
TOOLS_STATE=legacy.STATE/'tools-launcher.json'
TOOLS_MARKER='# CozOS managed Tools launcher v1'
PORTS_MARKER='# Stable Ports bootstrap/launcher for CozOS.'


def tools_launcher_payload():
    return f'''#!/bin/bash
{TOOLS_MARKER}
STATE="${{COZOS_STATE:-/userdata/system/cozos}}"
ACTIVE="${{STATE}}/active-version"

if ! command -v python3 >/dev/null 2>&1; then
    echo "CozOS requires Python 3 from KNULLI."
    sleep 8
    exit 1
fi
if [ ! -s "${{ACTIVE}}" ]; then
    echo "No active CozOS version is installed."
    sleep 8
    exit 1
fi

VERSION="$(tr -d '\\r\\n' < "${{ACTIVE}}")"
APP="${{STATE}}/apps/${{VERSION}}"
ENTRY="${{APP}}/main.py"
if [ ! -f "${{ENTRY}}" ]; then
    echo "CozOS active version ${{VERSION}} is incomplete."
    sleep 8
    exit 1
fi

export SDL_GAMECONTROLLER_USE_BUTTON_LABELS=1
if {{ [ ! -t 0 ] || [ ! -t 1 ]; }} && command -v vaixterm >/dev/null 2>&1; then
    exec vaixterm -w 640 -h 480 --no-credit --force-full-render \\
        -e "cd \\\"${{APP}}\\\" && python3 \\\"${{ENTRY}}\\\""
fi

cd "${{APP}}" || exit 1
python3 "${{ENTRY}}"
result=$?
sleep 3
exit "$result"
'''.encode()


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def install_tools_launcher():
    """Atomically create Tools first, then remove only our Ports bootstrap."""
    payload=tools_launcher_payload()
    if TOOLS_LAUNCHER.exists():
        current=TOOLS_LAUNCHER.read_bytes()
        if current!=payload:
            try: prior=json.loads(TOOLS_STATE.read_text())
            except (OSError,ValueError,TypeError): prior={}
            if (TOOLS_MARKER.encode() not in current or
                    prior.get('installed_sha256')!=digest(current)):
                raise RuntimeError('The Tools launcher was created or edited outside CozOS; refusing to overwrite it.')
    legacy.atomic(TOOLS_LAUNCHER,payload,0o755)
    if digest(TOOLS_LAUNCHER.read_bytes())!=digest(payload):
        raise RuntimeError('Tools launcher failed checksum verification.')
    legacy.atomic(TOOLS_STATE,(json.dumps({'version':VERSION,
        'path':str(TOOLS_LAUNCHER),'installed_sha256':digest(payload)},
        indent=2,sort_keys=True)+'\n').encode(),0o600)

    # Never remove an unknown or user-edited Ports file.  The bootstrap is
    # hidden only after the verified Tools launcher exists.
    if PORTS_LAUNCHER.is_file():
        current=PORTS_LAUNCHER.read_text(errors='replace')
        if PORTS_MARKER in current:
            PORTS_LAUNCHER.unlink()
    return 'Installed '+str(TOOLS_LAUNCHER)+' and verified its checksum.'


def remove_control_center_launchers():
    try: state=json.loads(TOOLS_STATE.read_text())
    except (OSError,ValueError,TypeError): state={}
    for path,marker in ((TOOLS_LAUNCHER,TOOLS_MARKER),(PORTS_LAUNCHER,PORTS_MARKER)):
        if not path.exists():
            continue
        payload=path.read_bytes(); current=payload.decode(errors='replace')
        verified=(path==TOOLS_LAUNCHER and
                  state.get('installed_sha256')==digest(payload))
        if marker not in current or (path==TOOLS_LAUNCHER and not verified):
            raise RuntimeError('Refusing to remove a launcher edited outside CozOS: '+str(path))
        path.unlink()
    TOOLS_STATE.unlink(missing_ok=True)
    updater.ACTIVE.unlink(missing_ok=True)
    if updater.APPS.exists():
        shutil.rmtree(updater.APPS)


def run_helper(name, action):
    result=subprocess.run([sys.executable,name,action],capture_output=True,text=True,timeout=900,check=False)
    text=(result.stdout+'\n'+result.stderr).strip()
    return result.returncode,text or (name+' returned no message.')


def install_or_repair():
    steps=[('CozOS settings and controls','overlay_060.py','install'),
           ('Legacy logo cleanup','bootlogo.py','remove'),
           ('KNULLI boot splash','rootsplash_060.py','install')]
    messages=[]
    for label,helper,action in steps:
        rc,out=run_helper(helper,action); messages.append(label+':\n'+out)
        if rc: return rc,'\n\n'.join(messages)+'\n\nStopped safely at the failed step.'
    try:
        messages.append('Tools Control Center:\n'+install_tools_launcher())
    except Exception as exc:
        return 1,'\n\n'.join(messages)+'\n\nTools migration stopped safely: '+str(exc)
    return 0,'\n\n'.join(messages)+'\n\nCozOS 0.6.3 is installed. Refresh the game list or reboot, then open Control Center from Tools.'


def status():
    overlay_rc,overlay_text=run_helper('overlay_060.py','status')
    splash_rc,splash_text=run_helper('rootsplash_060.py','status')
    battery_rc,battery_text=battery_action('status')
    model=legacy.read(legacy.ROOT/'sys/firmware/devicetree/base/model') or '<unavailable>'
    lines=['CozOS G350 Control Center '+VERSION,
           'Active managed version: '+(updater.current_version() or 'bootstrap copy'),
           'Installed overlay version: '+legacy.installed_version(),
           'Device: '+model,
           'Tools launcher: '+('PASS' if TOOLS_LAUNCHER.is_file() else 'MISSING'),
           'Ports bootstrap: '+('HIDDEN' if not PORTS_LAUNCHER.exists() else 'PRESENT'),'',
           'Overlay diagnostics: '+('PASS' if overlay_rc==0 else 'FAILED'),overlay_text,'',
           'Boot splash: '+('PASS' if splash_rc==0 else 'FAILED'),splash_text,'',
           'Battery survey: '+('PASS' if battery_rc==0 else 'FAILED'),battery_text,'',
           updater.local_scan_report()]
    report='\n'.join(lines).rstrip()+'\n'
    legacy.STATE.mkdir(parents=True,exist_ok=True)
    legacy.atomic(legacy.STATE/'control-center-report.txt',report.encode())
    return max(overlay_rc,splash_rc,battery_rc),report


def remove_cozos():
    steps=[('KNULLI boot splash','rootsplash_060.py','remove'),
           ('Legacy logo cleanup','bootlogo.py','remove'),
           ('CozOS settings and controls','overlay_060.py','remove')]
    messages=[]; result=0
    battery_rc,battery_text=run_helper('battery_survey.py','stop')
    messages.append('Battery survey logger:\n'+battery_text); result=result or battery_rc
    for label,helper,action in steps:
        rc,out=run_helper(helper,action); messages.append(label+':\n'+out); result=result or rc
    if result==0:
        try:
            remove_control_center_launchers()
            messages.append('Control Center launchers:\nRemoved verified CozOS launchers and versioned application files.')
        except Exception as exc:
            result=1; messages.append('Control Center launchers:\nRemoval stopped safely: '+str(exc))
    ending='Reboot normally to finish rollback.' if result==0 else 'One or more rollback checks stopped. Nothing unverified was overwritten.'
    return result,'\n\n'.join(messages)+'\n\n'+ending


def update_local():
    messages=[]
    try:
        version,previous=updater.install_local(lambda p,t:messages.append(f'{p:3d}%  {t}'))
        return 0,'\n'.join(messages)+f'\n\nInstalled CozOS {version}.'+(f' Previous version {previous} was retained.' if previous else '')+'\nRestart the Control Center to use the new version.'
    except Exception as exc:
        return 1,'\n'.join(messages)+('\n\n' if messages else '')+'Update stopped safely: '+str(exc)+'\nThe active version was not changed.'


def update_online():
    messages=[]
    try:
        version,previous=updater.fetch_online(lambda p,t:messages.append(f'{p:3d}%  {t}'))
        return 0,'\n'.join(messages)+f'\n\nInstalled CozOS {version}.'+(f' Previous version {previous} was retained.' if previous else '')+'\nRestart the Control Center to use the new version.'
    except Exception as exc:
        return 1,'\n'.join(messages)+('\n\n' if messages else '')+'Online update stopped safely: '+str(exc)+'\nThe active version was not changed.'


def rollback_version():
    messages=[]
    try:
        version=updater.rollback(lambda p,t:messages.append(f'{p:3d}%  {t}'))
        return 0,'\n'.join(messages)+f'\n\nActive version is now CozOS {version}.\nRestart the Control Center to load it.'
    except Exception as exc: return 1,'Rollback stopped safely: '+str(exc)


def battery_action(action):
    return run_helper('battery_survey.py',action)


class UI(legacy.UI):
    def menu(self):
        items=[('1','Install or repair CozOS '+VERSION),('2','Status and diagnostics'),
               ('3','Back up KNULLI settings'),('4','Restore latest settings backup'),
               ('5','Find and install/repair a local update'),
               ('6','Check and install online update'),('7','Roll back to previous CozOS version'),
               ('8','Battery accuracy survey'),('9','Version and update information'),
               ('r','Remove CozOS / complete rollback'),('0','Exit')]
        if not self.interactive:
            print('\nCozOS G350 Control Center '+VERSION)
            for key,desc in items: print('  '+key+'. '+desc)
            return input('Selection: ').strip()
        selected=0
        while True:
            self._screen('Choose an action',[('> ' if i==selected else '  ')+desc for i,(_,desc) in enumerate(items)])
            key=self._key()
            if key=='up': selected=(selected-1)%len(items)
            elif key=='down': selected=(selected+1)%len(items)
            elif key=='select': return items[selected][0]
            elif key=='back': return '0'
            elif key in {x[0] for x in items}: return key

    def battery_menu(self):
        items=[('1','Battery survey status'),('2','Save a one-time battery snapshot'),
               ('3','Start a full discharge survey'),('4','Stop and package the survey'),
               ('0','Back')]
        if not self.interactive:
            print('\nBattery accuracy survey')
            for key,desc in items: print('  '+key+'. '+desc)
            return input('Selection: ').strip()
        selected=0
        while True:
            self._screen('Battery accuracy survey',
                         [('> ' if i==selected else '  ')+desc for i,(_,desc) in enumerate(items)])
            key=self._key()
            if key=='up': selected=(selected-1)%len(items)
            elif key=='down': selected=(selected+1)%len(items)
            elif key=='select': return items[selected][0]
            elif key=='back': return '0'
            elif key in {x[0] for x in items}: return key

    def battery_tools(self):
        while True:
            choice=self.battery_menu()
            if choice in ('0',''): return
            if choice=='1':
                rc,msg=battery_action('status'); self.message('Battery survey status' if not rc else 'Battery survey error',msg)
            elif choice=='2':
                rc,msg=battery_action('snapshot'); self.message('Battery snapshot saved' if not rc else 'Snapshot stopped',msg)
            elif choice=='3':
                if self.confirm('Start battery survey','Start a read-only battery survey?\n\nFor useful calibration data, begin fully charged, unplug, use the G350 normally, and continue until its normal low-battery shutdown. Do not force it below the normal shutdown point.'):
                    rc,msg=battery_action('start'); self.message('Battery survey started' if not rc else 'Survey stopped',msg)
            elif choice=='4':
                if self.confirm('Package battery survey','Stop the logger and package the latest samples?'):
                    rc,msg=battery_action('stop-package'); self.message('Battery survey packaged' if not rc else 'Packaging stopped',msg)


def main():
    migration_error=''
    try:
        install_tools_launcher()
    except Exception as exc:
        migration_error=str(exc)
        legacy.STATE.mkdir(parents=True,exist_ok=True)
        legacy.atomic(legacy.STATE/'tools-migration-error.txt',migration_error.encode())
    ui=UI(); ui.start()
    try:
        if migration_error:
            ui.message('Tools migration stopped',migration_error+'\n\nThe Ports launcher was kept so you can retry Install / repair safely.')
        while True:
            choice=ui.menu()
            if choice in ('0',''): return 0
            if choice=='1': rc,msg=install_or_repair(); ui.message('Install / repair' if not rc else 'Install stopped',msg)
            elif choice=='2': rc,msg=status(); ui.message('Status' if not rc else 'Diagnostics found a problem',msg)
            elif choice=='3': rc,msg=legacy.create_backup(); ui.message('Settings backup' if not rc else 'Backup stopped',msg)
            elif choice=='4':
                available=legacy.backups()
                if not available: ui.message('Restore','No CozOS settings backup is available to restore.')
                elif ui.confirm('Restore settings','Restore the newest verified settings backup?\n\n'+str(available[0])+'\n\nA safety backup will be created first.'):
                    rc,msg=legacy.restore_latest(); ui.message('Restore complete' if not rc else 'Restore stopped',msg)
            elif choice=='5':
                if ui.confirm('Local update','Find and install the newest verified CozOS update ZIP?\n\nSearched locations:\n- SHARE/cozos-updates\n- SHARE/roms/ports\n- SHARE root\n\nInstalling the current version safely repairs its managed files.'):
                    rc,msg=update_local(); ui.message('Update complete' if not rc else 'Update stopped',msg)
            elif choice=='6':
                if ui.confirm('Online update','Connect to the CozOS release index, download, verify, and install the newest update?'):
                    rc,msg=update_online(); ui.message('Update complete' if not rc else 'Update stopped',msg)
            elif choice=='7':
                if ui.confirm('Version rollback','Switch the Control Center back to the newest retained previous version?'):
                    rc,msg=rollback_version(); ui.message('Rollback complete' if not rc else 'Rollback stopped',msg)
            elif choice=='8': ui.battery_tools()
            elif choice=='9':
                active=updater.current_version() or 'bootstrap copy'
                ui.message('Version and updates',f'Package version: {VERSION}\nActive managed version: {active}\n\n{updater.local_scan_report()}\n\nOnline index: {updater.INDEX_URL}\n\nUpdate log: /userdata/system/cozos/logs/updates.log\n\nUpdates are overlay application files, never firmware images.')
            elif choice=='r':
                if ui.confirm('Complete rollback','Remove CozOS and restore its verified backups?\n\nROMs, BIOS, saves, save states, and media are not deleted.'):
                    rc,msg=remove_cozos(); ui.message('Rollback complete' if not rc else 'Rollback stopped',msg)
            else: ui.message('CozOS','Unknown selection: '+choice)
    finally: ui.close()

if __name__=='__main__':
    try: sys.exit(main())
    except Exception:
        legacy.STATE.mkdir(parents=True,exist_ok=True)
        report=traceback.format_exc(); legacy.atomic(legacy.STATE/'control-center-error.txt',report.encode())
        raise
