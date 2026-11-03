"""Capture boot/WLAN evidence; never reboot or power off automatically."""
import argparse
import datetime as dt
import json
from pathlib import Path
import shlex
import time
import subprocess
import getpass
from adb_login import AdbSession, resolve_adb

ROOT = Path(__file__).resolve().parents[1]

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def capture(dest, session):
    dest.mkdir(parents=True, exist_ok=True)
    report = {'host_utc':utc(),'scope':'Read-only boot/WLAN capture; no manual WLAN activation','checks':[]}
    commands = {
        'identity': 'id -u; cat /etc/build_version; uname -a; cat /proc/sys/kernel/random/boot_id; cat /proc/uptime; date -u',
        'boot': 'systemd-analyze time; systemctl --failed --plain --no-legend --no-pager; journalctl -b -p err -n 100 --no-pager; dmesg | tail -n 100',
        'network': 'nmcli --colors no -f GENERAL.STATE,GENERAL.CONNECTION,IP4.ADDRESS,IP4.GATEWAY,IP4.DNS device show wlan0; ip -4 addr show dev wlan0; ip -4 route; timedatectl show -p NTPSynchronized -p TimeUSec; systemctl is-active NetworkManager; systemctl is-active dhcpcd',
        'wlan-profile': 'nmcli --colors no -g connection.id,connection.interface-name,connection.autoconnect,connection.autoconnect-retries,ipv4.method,ipv4.route-metric connection show qb560d-training-wlan; stat -c "%a %U %n" /etc/NetworkManager/system-connections/*; grep -n "denyinterfaces\\|wlan0" /etc/dhcpcd.conf',
        'wlan-check': 'cd /opt/qb560d-training-payload && timeout -k 2 32 sh target/wlan.sh check',
        'persistence': 'set -e; df -h / /opt; ls -ld /opt/qb560d-training-payload /opt/qb560d-training-payload/.python-deps /opt/qb560d-workshop /opt/qb560d-docker-demo /opt/qairt-isolated/2.51.40.260930 /opt/qb560d-ai-htp251; test -x /opt/qb560d-workshop/bin/iperf3; test -x /opt/qairt-isolated/2.51.40.260930/bin/qnn-net-run; test -f /opt/qairt-isolated/2.51.40.260930/lib/libQnnHtp.so; /opt/qb560d-workshop/bin/iperf3 --version | head -n 1; cd /opt/qb560d-training-payload; sh target/ai.sh verify',
        'activity': 'ps -eo pid,comm; systemctl is-active qb560d-training.service; systemctl is-active qb560d-docker-demo.service; ss -lnt | head -n 20',
        'thermal': 'for p in /sys/class/thermal/thermal_zone*; do printf "%s " "$p"; cat "$p/type" "$p/temp" 2>/dev/null | tr "\\n" " "; echo; done',
    }
    for name, cmd in commands.items():
        r=session.run(cmd,timeout=45)
        (dest/(name+'.log')).write_bytes(r.stdout)
        report['checks'].append({'name':name,'exit_code':r.returncode,'log':name+'.log'})
        print(name, r.returncode,flush=True)
    failed=session.run('systemctl --failed --plain --no-legend --no-pager',timeout=15)
    units=[line.split()[0] for line in failed.stdout.decode(errors='replace').splitlines() if '.service' in line]
    report['failed_units']=units
    for unit in units:
        cmd='systemctl show '+shlex.quote(unit)+' -p ActiveState -p SubState -p Result -p ExecMainStatus -p FragmentPath -p Requires -p Wants -p After -p Before; systemctl cat '+shlex.quote(unit)+'; journalctl -b -u '+shlex.quote(unit)+' -n 24 --no-pager'
        r=session.run(cmd,timeout=25)
        (dest/('unit-'+unit+'.log')).write_bytes(r.stdout)
    report['authentication']=session.auth
    (dest/'capture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('EVIDENCE',dest,flush=True)
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['capture','operator-watch'])
    p.add_argument('--adb');p.add_argument('--serial');p.add_argument('--transport-id')
    p.add_argument('--output',type=Path)
    p.add_argument('--before',type=Path,help='Pre-power capture folder; required for operator-watch')
    a=p.parse_args()
    dest=a.output or ROOT/'evidence/boot-wlan'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    if a.action=='capture':
        with AdbSession(a.adb,a.serial,a.transport_id) as s:capture(dest,s)
        return 0
    # The operator supplies the physical power event. This is not a reboot test.
    if not a.before or not (a.before/'identity.log').is_file():
        p.error('operator-watch requires --before with a saved pre-power identity.log')
    import re
    before=re.search(r'\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b',(a.before/'identity.log').read_text()).group()
    password=getpass.getpass('Linux root password (not saved): ')
    print('Finish all other target activity. Shut down Linux safely, remove DC power and any USB power, and wait at least 10 seconds.')
    input('With power still OFF, press Enter to arm this recording: ')
    off=subprocess.run([resolve_adb(a.adb),'get-state'],capture_output=True,timeout=8)
    if off.returncode==0:
        raise SystemExit('ADB is still online. Physical power-off was not confirmed; do not mark a cold boot.')
    dest.mkdir(parents=True,exist_ok=False)
    input('Restore power, then IMMEDIATELY press Enter to mark power-on: ')
    start=time.monotonic(); marked=utc()
    first=None
    connect_deadline=time.monotonic()+180
    while time.monotonic()<connect_deadline:
        try:
            s=AdbSession(a.adb,a.serial,a.transport_id,password=password)
            s.connect(timeout=4)
            with s:
                first={'power_on_operator_mark_utc':marked,'authenticated_shell_utc':utc(),'seconds_operator_mark_to_authenticated_shell':time.monotonic()-start,'timing_limit':'Operator presses Enter after energizing; includes manual reaction offset. ADB polling period up to 1 second plus login.','cold_cycle':'Operator-directed physical power interruption; compare boot_id and logs with pre-capture.'}
                r=s.run('cat /proc/sys/kernel/random/boot_id; cat /proc/uptime',timeout=8)
                first['post_boot_identity']=r.stdout.decode().strip()
                first['previous_boot_id']=before
                first['boot_id_changed']=before not in first['post_boot_identity']
                if not first['boot_id_changed']:raise RuntimeError('Boot ID did not change')
                # Observe autoconnect only. Never activate/reapply the profile here.
                wlan_start=time.monotonic()
                first['wlan_automatic_connected']=False
                while time.monotonic()-wlan_start<120:
                    state=s.run('nmcli --colors no -g GENERAL.STATE device show wlan0',timeout=8)
                    if state.returncode==0 and state.stdout.decode().strip().startswith('100 '):
                        first['wlan_automatic_connected']=True
                        first['seconds_operator_mark_to_wlan_connected']=time.monotonic()-start
                        break
                    time.sleep(2)
                (dest/'power-cycle.json').write_text(json.dumps(first,indent=2)+'\n',encoding='utf-8')
                # A usable early shell does not mean systemd startup is finished.
                boot_deadline=time.monotonic()+120
                first['systemd_startup_finished']=False
                while time.monotonic()<boot_deadline:
                    settled=s.run('systemd-analyze time',timeout=8)
                    if settled.returncode==0 and b'Startup finished in ' in settled.stdout:
                        first['systemd_startup_finished']=True
                        first['systemd_startup_summary']=settled.stdout.decode().strip()
                        break
                    time.sleep(2)
                (dest/'power-cycle.json').write_text(json.dumps(first,indent=2)+'\n',encoding='utf-8')
                post=capture(dest,s)
                previous=json.loads((a.before/'capture.json').read_text())
                first['new_failed_units']=sorted(set(post['failed_units'])-set(previous['failed_units']))
                first['required_checks_pass']=all(x['exit_code']==0 for x in post['checks'] if x['name'] in ['identity','persistence','wlan-check'])
                first['result']='PASS_COLD_BOOT_PERSISTENCE_AND_WLAN' if first['required_checks_pass'] and first['wlan_automatic_connected'] and first['systemd_startup_finished'] and not first['new_failed_units'] else 'REVIEW_REQUIRED'
                (dest/'power-cycle.json').write_text(json.dumps(first,indent=2)+'\n',encoding='utf-8')
                print(first['result'],flush=True)
                break
        except (OSError,RuntimeError,ValueError,ConnectionError,TimeoutError) as exc:
            if 's' in locals():s.close()
            if first is not None:
                first.update(result='REVIEW_REQUIRED',error=type(exc).__name__+': '+str(exc))
                (dest/'power-cycle.json').write_text(json.dumps(first,indent=2)+'\n',encoding='utf-8')
                raise
            time.sleep(1)
    if first is None:raise SystemExit('No authenticated shell within observation window; do not mark boot PASS.')
    return 0 if first['result']=='PASS_COLD_BOOT_PERSISTENCE_AND_WLAN' else 1

if __name__=='__main__':raise SystemExit(main())
