import os
import json
import subprocess
from ..config import config
from ..myutils import str2bool

class vhost_manager:


    def __init__(self, app):
        self.app = app
       
        self.vhostconf = config['NGINX_VHOST_PATH'].format(user=app.username, app=app.appname)
        self.tpl_path = config['NGINX_VHOST_TPL_PATH']
        self.mainhostname = f"{app.appname}-{app.username}.{config['TOPDOMAIN']}"
        self.servernames_path = os.path.join(config['APPS_PATH'], app.username, app.appname, 'etc/servernames.json')
        

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

    def vhost_update(self):
        if not self.vhost_need_update():
            print("no need to update")
            return
        
        regenerate_certificates = not str2bool(os.getenv('LOCKER_DEBUG_SKIP_CERTS'))

        if regenerate_certificates:
            # delete old cert
            print("delete old cert")
            subprocess.run([
                'sudo',
                'certbot','--non-interactive','delete',
                '--cert-name', self.mainhostname])
        
            print("get new cert")
            mkcert_cmd = [
                'sudo',
                'certbot','certonly','--allow-subset-of-names',
                '--webroot', 
                '-w', config['CERTBOT_WEBROOT']]

            for sn in self.servernames:
                mkcert_cmd.extend(['-d', sn])

            print("make cert:", mkcert_cmd)
            
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
            '-d', *self.servernames)
        ]
        subprocess.run(mkvhost_cmd)

        subprocess.run(['nginx', '-s', 'reload'])

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
