import os
import json
import subprocess
import socket
import logging

from ..config import config
from ..myutils import str2bool

from ..serverinstance import ServerInstance

si = ServerInstance()
log = logging.getLogger()

class vhost_manager:


    def __init__(self, app):
        self.app = app
       
        self.vhostconf = config['NGINX_VHOST_PATH'].format(user=app.username, app=app.appname)
        self.tpl_path = config['NGINX_VHOST_TPL_PATH']
        self.mainhostname = f"{app.appname}-{app.username}.{config['TOPDOMAIN']}"
        self.servernames_path = os.path.join(config['APPS_PATH'], app.username, app.appname, 'etc/servernames.json')
        self.myips = config['MYIPS']
        self.suffixes = config['RESERVED_DOMAIN_SUFFIXES']
        self.servernames = list()

    def read_servernames(self):
        # read servernames and fix it
        print("load", self.servernames_path)
        try:
            with open(self.servernames_path, "r") as fh:
                self.servernames = json.load(fh)
        except json.JSONDecodeError as e:
            return False

        if self.mainhostname in self.servernames:
            self.servernames.remove(self.mainhostname)
        
        self.servernames.insert(0, self.mainhostname)

        return True


    def vhost_need_update(self):

        if not os.path.exists(self.servernames_path):
            return False
        
        if not os.path.exists(self.vhostconf) or os.path.getmtime(self.vhostconf) < os.path.getmtime(self.servernames_path):
            return self.read_servernames()
        
        return False


    def verify_hosts(self):
        myips = set(self.myips)

        try:
            for host in self.servernames:
                if any([ host.endswith(s) for s in self.suffixes ]):
                    print(f"Suffix verification fails for {host}")
                    return False

            for host in self.servernames:
                ips = set(socket.gethostbyname_ex(host)[2])
                if not ips.issubset(self.myips):
                    print(f"host: {host} IPs: {ips} not inside {self.myips}")
                    return False
            return True

        except socket.gaierror as e:
            print(f"resolve error for {self.servernames}: {e}")
            return False


    def vhost_update(self):
        if not self.vhost_need_update():
            print("no need to update")
            return

        if not self.verify_hosts():
            print("failed verification")
            return
        
        regenerate_certificates = not str2bool(os.getenv('LOCKER_DEBUG_SKIP_CERTS'))
        test_certificates = str2bool(os.getenv('LOCKER_DEBUG_TEST_CERT'))


        if regenerate_certificates:
            # delete old cert
            log.debug("delete old cert")
            subprocess.run([
                'sudo',
                'certbot','--non-interactive','delete',
                '--cert-name', self.mainhostname])
        
            log.debug("get new cert")
            mkcert_cmd = [
                'sudo',
                'certbot','certonly',
                '--allow-subset-of-names',
                '--webroot', 
                '-w', config['CERTBOT_WEBROOT']  
                ] + ( ['--test-cert'] if test_certificates else [] )


            for sn in self.servernames:
                mkcert_cmd.extend(['-d', sn])

            log.debug(f"make cert: {mkcert_cmd}")
            
            subprocess.run(mkcert_cmd)
        
        else:
            print("Skipped certificates, because LOCKER_DEBUG_SKIP_CERTS")

        # update nginx vhost conf file

        mkvhost_cmd = [
            'sudo',
            config['MKVHOST'],
            '--create',
            '--template', self.tpl_path,
            '--target', self.vhostconf,
            '--reload',
            '-d', *self.servernames
        ]
        subprocess.run(mkvhost_cmd)
        self.update_mappings()

    def update_mappings(self):

        log.debug("update mappings")
        log.debug(f"vhost_map: {config['VHOST_MAP']}")

        # update vhost_map first
        try:
            with open(config['VHOST_MAP']) as fh:
                vhost_map = json.load(fh)
        except FileNotFoundError:
            log.warn(f'Not found {config["VHOST_MAP"]}, use empty file')
            vhost_map = dict()

        key = ':'.join(self.app.tuplename())

        if key in vhost_map:
            for old_sn in vhost_map[key]:
                if old_sn not in self.servernames:
                    si.redis.hdel('locker:apphostnames', old_sn)
        else:
            log.warn(f'{key} not found in vhost_map')

        for sn in self.servernames:
            if (not key in vhost_map) or (not sn in vhost_map[key]):
                si.redis.hset('locker:apphostnames', sn, ':'.join(self.app.tuplename()))


        vhost_map[key] = self.servernames
        
        with open(config['VHOST_MAP'], "w") as fh:
            json.dump(vhost_map, fh, indent=4, sort_keys=True)


    #
    # /opt/venv/certbot/bin/certbot --non-interactive delete --cert-name x1.rudev.www-security.net
    # /opt/venv/certbot/bin/certbot certonly --allow-subset-of-names --webroot -w /var/www/acme/ -d x1.rudev.www-security.net -d x2.rudev.www-security.net
    # 

    def scan(self, apps = None):
        apps = self.locker_apps
        # print("scan")
        for user in os.listdir(apps):
            upath = os.path.join(apps, user)
            if not os.path.isdir(upath):
                continue
            # print(user)
            for app in os.listdir(upath):
                apath = os.path.join(upath, app)
                # print(f"{user} {apath}")
                if vhost_need_update(user, app):
                    vhost_update(user, app)


if __name__ == '__main__':
    pass
