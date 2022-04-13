import json
import yaml
import os
import socket
from myutils import myip


venv_path = os.getenv('LOCKER_VENV', os.getenv('VIRTUAL_ENV', '.'))

print(f"{venv_path} (LOCKER_VENV: {os.getenv('LOCKER_VENV')} VIRTUAL_ENV: {os.getenv('VIRTUAL_ENV')})")

def env2list(varname, default="", sep=' '):
    return list(filter(None, list(os.getenv(varname, default).split(sep))))

# Default config
config = {

    #
    # Main config
    #
    'APPS_PATH': os.getenv('LOCKER_APPS_PATH', '/opt/locker-apps/'),
    'LOCAL_CONFIG': os.getenv('LOCKER_LOCAL_CONFIG', 'config.yml'),
    'CERTBOT_WEBROOT': '/var/www/acme',
    'NGINX_VHOST_PATH': '/etc/nginx/vhosts/{user}-{app}.conf',
    'NGINX_VHOST_TPL_PATH': '/etc/locker/nginx-vhost.tpl',

    'MKVHOST': os.path.join(venv_path, 'bin', 'mkvhost.py'),

    'MYIPS': env2list('LOCKER_MYIPS'),
    'RESERVED_DOMAIN_SUFFIXES': env2list('LOCKER_RESERVED_DOMAIN_SUFFIXES'),

    # 
    # SSL
    #
    # 'PRIVKEY': None,
    # 'CERT': None,


    #
    # Flask settings
    #
    'JSONIFY_PRETTYPRINT_REGULAR': True,


    #
    # Session and cookie
    #
    'SESSION_COOKIE_SAMESITE': "None",
    'SESSION_COOKIE_SECURE': True,
    'SESSION_TYPE': 'redis',
    'PERMANENT_SESSION_LIFETIME': 86400,


    #
    # Authentication
    #
    'AUTH_TIMEOUT': 600,

    #
    # Applications
    #

    'APPS_CONFIG': {
        '*': {
            'home_size': 50,
            'users': 2
        }
    }
}

# update config
for path in [c for c in config['LOCAL_CONFIG'].split(' ') if os.path.exists(c)]:
    print("Load local config from file:", path)
    with open(path, "r") as fh:
        cfg = yaml.full_load(fh)
        config.update(cfg)

# fix config
if config['APPS_PATH']:
    config['APPS_PATH'] = os.path.expanduser(config['APPS_PATH'])

pubconf = config['PUBCONF']
if not pubconf.get('hostname'):
    pubconf['hostname'] = socket.gethostname()

if not config['MYIPS']:
    config['MYIPS'] = [ myip() ]
    print(f"Autodetect MYIPS: {config['MYIPS']}")


