#!/usr/bin/env python3
"""Interactive fresh-install wizard. Never reuses an existing guest or mount."""
import argparse
import getpass
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

PROJECT = Path(__file__).resolve().parents[1]


def run(args, *, data=None, timeout=180, visible=False):
    result = subprocess.run([str(a) for a in args], input=data, text=True, timeout=timeout,
                            stdout=None if visible else subprocess.PIPE, stderr=None if visible else subprocess.PIPE)
    if result.returncode:
        # Command output may contain mount credentials or package configuration.
        raise RuntimeError('Systemaktion fehlgeschlagen: ' + str(args[0]) + '. Installation bleibt zur Diagnose erhalten.')
    return result.stdout.strip() if result.stdout else ''


def prompt(label, default, validate=lambda value: bool(value)):
    while True:
        value = input(f'{label} [{default}]: ').strip() or str(default)
        try:
            if validate(value):
                return value
        except (ValueError, TypeError):
            pass
        print('Bitte einen gültigen Wert eingeben.')


def parse_share(value):
    parts = value.strip().replace('\\', '/').removeprefix('//').rstrip('/').split('/')
    if len(parts) < 2 or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.\-]{0,252}', parts[0]):
        raise ValueError('Ungültiger NAS-Hostname oder Freigabepfad.')
    for part in parts[1:]:
        if not part or part in ('.', '..') or any(ord(c) < 32 or c in ':*?"<>|,\\' for c in part):
            raise ValueError('Ungültiger NAS-Pfad.')
    return '//' + '/'.join(parts[:2]), parts[2:]


def valid_ip(value):
    return isinstance(ipaddress.ip_address(value), ipaddress.IPv4Address)


def private_file(path, text, mode=0o600):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
    with os.fdopen(fd, 'w') as handle:
        handle.write(text)


def wizard():
    print((PROJECT / 'ascii logo.txt').read_text(encoding='utf-8-sig'))
    print('\nProxmox VE · neue, eigenständige JDownloader-Installation\n')
    if os.geteuid() != 0 or not shutil.which('pct'):
        raise RuntimeError('Als root auf einem Proxmox-VE-Knoten starten.')
    version = run(['pveversion'])
    if not re.search(r'pve-manager/[89]\.', version):
        raise RuntimeError('Unterstützt werden Proxmox VE 8 und 9 auf amd64.')
    if run(['dpkg', '--print-architecture']) != 'amd64':
        raise RuntimeError('Diese Installation benötigt amd64.')
    node = run(['hostname', '-s'])
    status = json.loads(run(['pvesh', 'get', '/nodes/' + node + '/storage', '--output-format', 'json']))
    roots = [s['storage'] for s in status if s.get('active') and 'rootdir' in s.get('content', '').split(',')]
    templates = [s['storage'] for s in status if s.get('active') and 'vztmpl' in s.get('content', '').split(',')]
    if not roots or not templates:
        raise RuntimeError('Aktiver Storage für rootdir und vztmpl wird benötigt.')
    ct = prompt('Neue Container-ID', run(['pvesh', 'get', '/cluster/nextid']), lambda s: s.isdecimal() and 100 <= int(s) <= 999999999)
    if subprocess.run(['pct', 'config', ct], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0 or (Path('/etc/pve/qemu-server') / (ct + '.conf')).exists():
        raise RuntimeError('Diese Gast-ID ist bereits belegt. Bestehende Gäste werden nicht geändert.')
    name = prompt('Container-Hostname', 'jdownloader2', lambda s: bool(re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9-]{0,62}', s)))
    root = prompt('Systemdisk-Storage: ' + ', '.join(roots), 'local-lvm' if 'local-lvm' in roots else roots[0], lambda s: s in roots)
    template_store = prompt('Template-Storage: ' + ', '.join(templates), templates[0], lambda s: s in templates)
    bridge = prompt('Netzwerkbridge', 'vmbr0', lambda s: bool(re.fullmatch(r'[A-Za-z0-9_.-]+', s)) and (Path('/sys/class/net') / s).exists())
    cidr = prompt('Freie IPv4-Adresse mit Präfix, z.B. 192.0.2.20/24', '', lambda s: '/' in s and isinstance(ipaddress.ip_interface(s), ipaddress.IPv4Interface))
    address = str(ipaddress.ip_interface(cidr).ip)
    network = ipaddress.ip_interface(cidr).network
    gateway = prompt('IPv4-Gateway', str(network.network_address + 1), lambda s: valid_ip(s) and ipaddress.ip_address(s) in network)
    dns = prompt('DNS-Server (IPv4)', gateway, valid_ip)
    local_ips = [value for value in run(['hostname','-I']).split() if ':' not in value]
    host_default = next((value for value in local_ips if ipaddress.ip_address(value) in network), local_ips[0] if local_ips else '')
    host = prompt('IPv4 dieses Proxmox-Knotens für NAS-Verwaltung', host_default, lambda s: valid_ip(s) and s in local_ips)
    cores = prompt('vCPUs', '4', lambda s: s.isdecimal() and 1 <= int(s) <= 128)
    memory = prompt('RAM in MiB', '4096', lambda s: s.isdecimal() and 2048 <= int(s) <= 1048576)
    disk = prompt('Systemdisk in GiB', '24', lambda s: s.isdecimal() and 16 <= int(s) <= 4096)
    nas = prompt('NAS-Ziel, z.B. \\\\nas.example\\Downloads', '', lambda s: bool(parse_share(s)))
    source, parts = parse_share(nas)
    username = prompt('SMB-Benutzername', '', lambda s: bool(s) and not any(c in s for c in '\r\n\x00'))
    password = getpass.getpass('SMB-Passwort (verdeckt): ')
    if not password or any(c in password for c in '\r\n\x00'):
        raise RuntimeError('Ungültiges SMB-Passwort.')
    admin = getpass.getpass('Neues WebGUI-Passwort für admin (mind. 12 Zeichen): ')
    if len(admin) < 12 or len(admin) > 256 or admin != getpass.getpass('WebGUI-Passwort bestätigen: '):
        raise RuntimeError('WebGUI-Passwörter stimmen nicht überein oder haben eine ungültige Länge.')
    print(f'\nNeuer LXC {ct} · {name} · {cidr} · {root}:{disk} GiB · {cores} vCPU · {memory} MiB RAM')
    print('Ubuntu 24.04 · unprivilegiert · SMB-Bind-Mount · eingeschränkter NAS-Verwaltungszugang')
    if input('Installation mit diesen Werten starten? [ja/NEIN]: ').strip().lower() != 'ja':
        print('Abgebrochen. Es wurde nichts geändert.')
        return
    install(dict(ct=ct, name=name, root=root, template_store=template_store, bridge=bridge, cidr=cidr, address=address,
                 network=str(network), gateway=gateway, dns=dns, host=host, cores=cores, memory=memory, disk=disk,
                 source=source, parts=parts, username=username, password=password, admin=admin))


def install(c):
    ct = c['ct']
    base = Path('/etc/jdownloader-nas') / ct
    mount = Path('/mnt/bindmounts') / ('jd2-' + ct)
    candidate = Path('/mnt/bindmounts') / ('jd2-' + ct + '-candidate')
    helper_dir = Path('/usr/local/lib/jdownloader-nas') / ct
    rpc_user = 'jd2mount-' + ct
    rpc = Path('/usr/local/sbin') / ('jd2-nas-rpc-' + ct)
    for path in (base, mount, candidate, helper_dir, rpc):
        if path.exists() or path.is_symlink():
            raise RuntimeError('Ein Installationspfad ist bereits belegt: ' + str(path))
    # Exact static IP is also the source restriction of the SSH management key.
    if shutil.which('ping') and subprocess.run(['ping', '-c', '1', '-W', '2', c['address']], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        raise RuntimeError('Die gewünschte IP antwortet bereits. Bitte eine freie IP verwenden.')
    print('Host-Werkzeuge und Ubuntu-Vorlage werden vorbereitet …')
    if not Path('/etc/ssh/ssh_host_ed25519_key.pub').is_file():
        raise RuntimeError('Der SSH-Hostschlüssel des Proxmox-Knotens fehlt.')
    run(['apt-get', 'update', '-qq'], timeout=600)
    run(['apt-get', 'install', '-y', '-qq', 'cifs-utils', 'sudo'], timeout=600)
    run(['pveam', 'update'], timeout=180)
    available = run(['pveam', 'available', '--section', 'system'])
    choices = re.findall(r'\b(ubuntu-24\.04-standard_[^\s]+_amd64\.tar\.(?:zst|gz|xz))', available)
    if not choices:
        raise RuntimeError('Ubuntu-24.04-Template ist nicht verfügbar.')
    template = sorted(choices)[-1]
    run(['pveam', 'download', c['template_store'], template], timeout=1200)
    base.mkdir(mode=0o700, parents=True)
    credential = base / 'credentials'
    private_file(credential, 'username=' + c['username'] + '\npassword=' + c.pop('password') + '\n')
    mount.mkdir(mode=0o000, parents=True)
    options = f'credentials={credential},vers=3.0,uid=101000,gid=101000,forceuid,forcegid,file_mode=0660,dir_mode=0770,nosuid,nodev,noexec,_netdev,x-systemd.mount-timeout=20s'
    run(['mount', '-t', 'cifs', c['source'], mount, '-o', options], timeout=40)
    destination = mount
    for part in c['parts']:
        destination = destination / part
        if destination.is_symlink():
            raise RuntimeError('Symbolische NAS-Pfade sind nicht zulässig.')
        destination.mkdir(exist_ok=True)
    probe = 'import tempfile,os,sys; f=tempfile.TemporaryFile(dir=sys.argv[1]); f.write(b"jd2-install-check"); f.flush(); os.fsync(f.fileno())'
    run(['setpriv', '--reuid=101000', '--regid=101000', '--clear-groups', 'python3', '-c', probe, destination], timeout=20)
    escape = lambda s: str(s).replace('\\', r'\134').replace(' ', r'\040').replace('\t', r'\011')
    with Path('/etc/fstab').open('a') as handle:
        handle.write(f'\n# JDownloader LXC {ct}\n{escape(c["source"])} {mount} cifs {options} 0 0\n')
    run(['systemctl', 'daemon-reload'])
    print('NAS geprüft. Neuer Container wird angelegt …')
    run(['pct', 'create', ct, c['template_store'] + ':vztmpl/' + template, '--hostname', c['name'], '--unprivileged', '1',
         '--cores', c['cores'], '--memory', c['memory'], '--swap', '2048', '--rootfs', c['root'] + ':' + c['disk'],
         '--onboot', '1', '--startup', 'order=30', '--features', 'nesting=1', '--nameserver', c['dns'],
         '--net0', f'name=eth0,bridge={c["bridge"]},ip={c["cidr"]},gw={c["gateway"]},firewall=1',
         '--mp0', f'{destination},mp=/mnt/downloads,backup=0'], timeout=600)
    # Store the pre-start guard on an existing directory storage supporting snippets.
    storages = json.loads(run(['pvesh', 'get', '/storage', '--output-format', 'json']))
    dirs = [s for s in storages if s.get('type') == 'dir' and s.get('path') and not s.get('disable')]
    if not dirs:
        raise RuntimeError('Für den NAS-Startschutz wird ein aktiver Directory-Storage benötigt.')
    storage = next((s for s in dirs if s['storage'] == 'local'), dirs[0])
    contents = storage.get('content', '')
    if 'snippets' not in contents.split(','):
        run(['pvesm', 'set', storage['storage'], '--content', contents + ',snippets'])
    snippets = Path(storage['path']) / 'snippets'
    snippets.mkdir(exist_ok=True)
    hook = snippets / ('jd2-nas-' + ct + '.sh')
    private_file(hook, '#!/bin/bash\nset -euo pipefail\nif [ "$2" = pre-start ]; then\n  mountpoint -q ' + str(mount) + ' || mount ' + str(mount) + '\n  test "$(findmnt -n -o FSTYPE -T ' + str(mount) + ')" = cifs\n  timeout 10 stat ' + shlex.quote(str(mount)) + ' >/dev/null\nfi\n', 0o700)
    run(['pct', 'set', ct, '--hookscript', storage['storage'] + ':snippets/' + hook.name])
    run(['pct', 'start', ct], timeout=120)
    with tempfile.TemporaryDirectory(prefix='jd2-bootstrap-') as temporary:
        work = Path(temporary)
        archive = work / 'project.tar.gz'
        # Explicit source allowlist excludes local access files and developer artifacts.
        with tarfile.open(archive, 'w:gz') as tar:
            for name in ('backend','frontend','scripts','config','systemd','nginx','browser-extension','docs','README.md','LICENSE','ascii logo.txt'):
                def filt(info):
                    if any(part in ('.private','.git','__pycache__','node_modules','dist','venv','signed') for part in Path(info.name).parts):
                        return None
                    if info.issym() or info.islnk():
                        return None
                    return info
                tar.add(PROJECT / name, arcname=name, filter=filt)
        run(['pct', 'push', ct, archive, '/run/jd2-project.tar.gz'])
        run(['pct', 'exec', ct, '--', 'mkdir', '-p', '/opt/jdownloader-web'])
        run(['pct', 'exec', ct, '--', 'tar', '-xzf', '/run/jd2-project.tar.gz', '-C', '/opt/jdownloader-web'])
        values = dict(line.split('=', 1) for line in (PROJECT / 'config/config.env.example').read_text().splitlines() if line and not line.startswith('#'))
        values.update(NAS_SOURCE=json.dumps(c['source']), NAS_ROOT=json.dumps('/' + '/'.join(c['parts'])),
                      NAS_TARGET=json.dumps(c['source'].replace('/', '\\') + ('\\' + '\\'.join(c['parts']) if c['parts'] else '')),
                      NAS_ADMIN_HOST=c['host'], NAS_ADMIN_USER=rpc_user)
        env = work / 'config.env'
        private_file(env, '\n'.join(k+'='+v for k,v in values.items())+'\n')
        run(['pct', 'exec', ct, '--', 'mkdir', '-p', '/etc/jdownloader-web'])
        run(['pct', 'push', ct, env, '/etc/jdownloader-web/config.env', '--perms', '0640'])
        firewall = work / 'nftables.conf'
        firewall.write_text((PROJECT / 'config/nftables.conf').read_text().replace('192.0.2.0/24', c['network']).replace('192.0.2.0/24', c['network']))
        run(['pct', 'push', ct, firewall, '/opt/jdownloader-web/config/nftables.conf'])
        print('Container-Pakete und geschützter Administratorzugang werden eingerichtet …')
        run(['pct','exec',ct,'--','bash','-c','apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-venv ca-certificates'], timeout=600)
        run(['pct','exec',ct,'--','python3','-m','venv','/opt/jdownloader-web/venv'])
        run(['pct','exec',ct,'--','/opt/jdownloader-web/venv/bin/pip','install','-q','-r','/opt/jdownloader-web/backend/requirements.txt'], timeout=600)
        hashing = 'import sys,json,os; from argon2 import PasswordHasher; p=sys.stdin.read(); fd=os.open("/run/jd2-admin.json",os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); f=os.fdopen(fd,"w"); json.dump({"username":"admin","password_hash":PasswordHasher().hash(p)},f); f.close()'
        run(['pct','exec',ct,'--','/opt/jdownloader-web/venv/bin/python','-c',hashing], data=c.pop('admin'))
        # install.sh loads the environment before testing the real NAS mount.
        print('WebGUI und JDownloader werden installiert. Das erste Engine-Update kann mehrere Minuten dauern …')
        run(['pct','exec',ct,'--','bash','/opt/jdownloader-web/scripts/install.sh','--admin-hash-file','/run/jd2-admin.json'], timeout=2400, visible=True)
        setup_management(c, base, mount, candidate, helper_dir, rpc_user, rpc, work)
        run(['pct','exec',ct,'--','rm','-f','/run/jd2-project.tar.gz','/run/jd2-admin.json'])
    print(f'\nInstallation abgeschlossen: http://{c["address"]}/ · Benutzer admin\n')
    print('Passwörter wurden nicht ausgegeben. Den DNS-Namen bitte im eigenen DNS auf die Container-IP setzen.')


def setup_management(c, base, mount, candidate, helper_dir, user, rpc, work):
    ct = c['ct']
    helper_dir.mkdir(mode=0o700, parents=True)
    helper = helper_dir / 'nas_host.py'
    shutil.copyfile(PROJECT / 'scripts/nas_host.py', helper)
    helper.chmod(0o700)
    private_file(helper.with_suffix('.json'), json.dumps(dict(ct_id=int(ct),base=str(base),mount=str(mount),candidate=str(candidate))))
    private_file(base / 'state.json', json.dumps(dict(target=c['source'].replace('/', '\\') + ('\\'+'\\'.join(c['parts']) if c['parts'] else ''),status='ready',message='NAS verbunden.')))
    private_file(rpc, '#!/bin/sh\nexec /usr/bin/python3 ' + str(helper) + '\n', 0o755)
    run(['useradd','--system','--create-home','--home-dir','/var/lib/'+user,'--shell','/bin/sh',user])
    ssh = Path('/var/lib') / user / '.ssh'
    ssh.mkdir(mode=0o750)
    run(['chown','root:'+user,ssh.parent,ssh])
    run(['chmod','750',ssh.parent,ssh])
    key = work / 'nas_key'
    run(['ssh-keygen','-q','-t','ed25519','-N','','-C','jd2-nas-'+ct,'-f',key])
    public = key.with_suffix('.pub').read_text().strip()
    authorized = ssh / 'authorized_keys'
    private_file(authorized, f'from="{c["address"]}",command="sudo -n {rpc}",restrict ' + public + '\n', 0o640)
    run(['chown','root:'+user,authorized])
    sudo = Path('/etc/sudoers.d') / user
    private_file(sudo, user+' ALL=(root) NOPASSWD: '+str(rpc)+' ""\n', 0o440)
    run(['visudo','-cf',sudo])
    known = work / 'nas_known_hosts'
    host_key = Path('/etc/ssh/ssh_host_ed25519_key.pub').read_text().split()
    private_file(known, c['host']+' '+host_key[0]+' '+host_key[1]+'\n')
    for path in (key, known):
        run(['pct','push',ct,path,'/etc/jdownloader-web/'+path.name,'--perms','0600'])
        run(['pct','exec',ct,'--','chown','jdweb:jdownloader','/etc/jdownloader-web/'+path.name])
    run(['pct','exec',ct,'--','systemctl','restart','jdownloader-web'])
    status = run(['pct','exec',ct,'--','runuser','-u','jdweb','--','ssh','-T','-i','/etc/jdownloader-web/nas_key','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/jdownloader-web/nas_known_hosts',user+'@'+c['host']],data='{"action":"status"}',timeout=25)
    if json.loads(status).get('status') != 'ready':
        raise RuntimeError('Der NAS-Verwaltungszugang konnte nicht geprüft werden.')
    for attempt in range(20):
        health = json.loads(run(['pct','exec',ct,'--','curl','-fsS','http://127.0.0.1/api/health']))
        if health.get('nas') == 'online' and health.get('jdownloader') == 'online':
            return
        time.sleep(2)
    raise RuntimeError('Abschließender Healthcheck ist noch nicht vollständig grün.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Nur Quelldateien und Proxmox-Werkzeuge prüfen; nichts ändern.')
    args = parser.parse_args()
    if args.check:
        missing = [name for name in ('pct','pveversion','pvesm','pveam','pvesh','python3','curl','tar','ssh-keygen','setpriv') if not shutil.which(name)]
        if missing:
            raise RuntimeError('Fehlende Proxmox-Werkzeuge: '+', '.join(missing))
        print('Proxmox-Werkzeuge vorhanden. Prüfung ohne Änderungen abgeschlossen.')
        return
    if not sys.stdin.isatty():
        raise RuntimeError('Eine interaktive Konsole wird benötigt.')
    wizard()


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        print('\nInstallation angehalten: '+str(error) if not isinstance(error, subprocess.TimeoutExpired) else '\nInstallation angehalten: Zeitlimit einer Systemaktion erreicht.', file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print('\nAbgebrochen.', file=sys.stderr)
        sys.exit(130)
