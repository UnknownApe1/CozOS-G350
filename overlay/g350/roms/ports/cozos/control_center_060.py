#!/usr/bin/env python3
"""CozOS 0.6.0 Control Center management layer.

Keeps the hardware-tested 0.5.3 helpers intact and adds versioned updates,
rollback, progress, logs, and restart guidance.
"""
import sys
import traceback
from pathlib import Path

import control_center as legacy
import updater

VERSION='0.6.0'
legacy.VERSION=VERSION


def update_local():
    messages=[]
    def cb(pct,text):
        messages.append(f'{pct:3d}%  {text}')
    try:
        version, previous=updater.install_local(cb)
        return 0,'\n'.join(messages)+f'\n\nInstalled CozOS {version}.'+(f' Previous version {previous} was retained.' if previous else '')+'\nRestart the Control Center to use the new version.'
    except Exception as exc:
        return 1,'\n'.join(messages)+('\n\n' if messages else '')+'Update stopped safely: '+str(exc)+'\nThe active version was not changed.'


def update_online():
    messages=[]
    def cb(pct,text): messages.append(f'{pct:3d}%  {text}')
    try:
        version, previous=updater.fetch_online(cb)
        return 0,'\n'.join(messages)+f'\n\nInstalled CozOS {version}.'+(f' Previous version {previous} was retained.' if previous else '')+'\nRestart the Control Center to use the new version.'
    except Exception as exc:
        return 1,'\n'.join(messages)+('\n\n' if messages else '')+'Online update stopped safely: '+str(exc)+'\nThe active version was not changed.'


def rollback_version():
    messages=[]
    try:
        version=updater.rollback(lambda p,t: messages.append(f'{p:3d}%  {t}'))
        return 0,'\n'.join(messages)+f'\n\nActive version is now CozOS {version}.\nRestart the Control Center to load it.'
    except Exception as exc:
        return 1,'Rollback stopped safely: '+str(exc)


class UI(legacy.UI):
    def menu(self):
        items=[
            ('1','Install or repair CozOS '+VERSION),
            ('2','Status and diagnostics'),
            ('3','Back up KNULLI settings'),
            ('4','Restore latest settings backup'),
            ('5','Install local update from SHARE/cozos-updates'),
            ('6','Check and install online update'),
            ('7','Roll back to previous CozOS version'),
            ('8','Version and update information'),
            ('9','Remove CozOS / complete rollback'),
            ('0','Exit'),
        ]
        if not self.interactive:
            print('\nCozOS G350 Control Center '+VERSION)
            for key,desc in items: print('  '+key+'. '+desc)
            return input('Selection: ').strip()
        selected=0
        while True:
            body=[('> ' if i==selected else '  ')+desc for i,(_,desc) in enumerate(items)]
            self._screen('Choose an action',body)
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
            if choice=='1':
                rc,msg=legacy.install_or_repair(); ui.message('Install / repair' if not rc else 'Install stopped',msg)
            elif choice=='2':
                rc,msg=legacy.status(); ui.message('Status' if not rc else 'Diagnostics found a problem',msg)
            elif choice=='3':
                rc,msg=legacy.create_backup(); ui.message('Settings backup' if not rc else 'Backup stopped',msg)
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
                rc,msg=legacy.update_info()
                active=updater.current_version() or 'bootstrap copy'
                msg=f'Package version: {VERSION}\nActive managed version: {active}\n\nLocal updates: /userdata/cozos-updates\nOnline index: {updater.INDEX_URL}\n\nUpdate log: /userdata/system/cozos/logs/updates.log\n\nUpdates are overlay application files, never firmware images.'
                ui.message('Version and updates',msg)
            elif choice=='9':
                if ui.confirm('Complete rollback','Remove CozOS and restore its verified backups?\n\nROMs, BIOS, saves, save states, and media are not deleted.'):
                    rc,msg=legacy.remove_cozos(); ui.message('Rollback complete' if not rc else 'Rollback stopped',msg)
            else: ui.message('CozOS','Unknown selection: '+choice)
    finally: ui.close()

if __name__=='__main__':
    try: sys.exit(main())
    except Exception:
        legacy.STATE.mkdir(parents=True,exist_ok=True)
        report=traceback.format_exc(); legacy.atomic(legacy.STATE/'control-center-error.txt',report.encode())
        raise
