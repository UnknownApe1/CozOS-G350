#!/usr/bin/env python3
"""CozOS 0.6.0 Control Center management layer."""
import subprocess, sys, traceback
import control_center as legacy
import updater

VERSION='0.6.0'
legacy.VERSION=VERSION


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
    return 0,'\n\n'.join(messages)+'\n\nCozOS 0.6.0 is installed. Reboot normally to finish applying system-level changes.'


def status():
    overlay_rc,overlay_text=run_helper('overlay_060.py','status')
    splash_rc,splash_text=run_helper('rootsplash_060.py','status')
    model=legacy.read(legacy.ROOT/'sys/firmware/devicetree/base/model') or '<unavailable>'
    lines=['CozOS G350 Control Center '+VERSION,
           'Active managed version: '+(updater.current_version() or 'bootstrap copy'),
           'Installed overlay version: '+legacy.installed_version(),
           'Device: '+model,'',
           'Overlay diagnostics: '+('PASS' if overlay_rc==0 else 'FAILED'),overlay_text,'',
           'Boot splash: '+('PASS' if splash_rc==0 else 'FAILED'),splash_text]
    report='\n'.join(lines).rstrip()+'\n'
    legacy.STATE.mkdir(parents=True,exist_ok=True)
    legacy.atomic(legacy.STATE/'control-center-report.txt',report.encode())
    return max(overlay_rc,splash_rc),report


def remove_cozos():
    steps=[('KNULLI boot splash','rootsplash_060.py','remove'),
           ('Legacy logo cleanup','bootlogo.py','remove'),
           ('CozOS settings and controls','overlay_060.py','remove')]
    messages=[]; result=0
    for label,helper,action in steps:
        rc,out=run_helper(helper,action); messages.append(label+':\n'+out); result=result or rc
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


class UI(legacy.UI):
    def menu(self):
        items=[('1','Install or repair CozOS '+VERSION),('2','Status and diagnostics'),
               ('3','Back up KNULLI settings'),('4','Restore latest settings backup'),
               ('5','Install local update from SHARE/cozos-updates'),
               ('6','Check and install online update'),('7','Roll back to previous CozOS version'),
               ('8','Version and update information'),('9','Remove CozOS / complete rollback'),('0','Exit')]
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


def main():
    ui=UI(); ui.start()
    try:
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
                if ui.confirm('Local update','Install the newest verified CozOS update ZIP from SHARE/cozos-updates?'):
                    rc,msg=update_local(); ui.message('Update complete' if not rc else 'Update stopped',msg)
            elif choice=='6':
                if ui.confirm('Online update','Connect to the CozOS release index, download, verify, and install the newest update?'):
                    rc,msg=update_online(); ui.message('Update complete' if not rc else 'Update stopped',msg)
            elif choice=='7':
                if ui.confirm('Version rollback','Switch the Control Center back to the newest retained previous version?'):
                    rc,msg=rollback_version(); ui.message('Rollback complete' if not rc else 'Rollback stopped',msg)
            elif choice=='8':
                active=updater.current_version() or 'bootstrap copy'
                ui.message('Version and updates',f'Package version: {VERSION}\nActive managed version: {active}\n\nLocal updates: /userdata/cozos-updates\nOnline index: {updater.INDEX_URL}\n\nUpdate log: /userdata/system/cozos/logs/updates.log\n\nUpdates are overlay application files, never firmware images.')
            elif choice=='9':
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
