#!/usr/bin/env python3

"""
# Python standard libraries
import json
import os
import sys
import logging
import secrets
import time
"""

import os
import sys
import argparse
import logging
import json
from logging.handlers import SMTPHandler

from dotenv import load_dotenv


from locker_server.config import config
from locker_server import flask_app
from locker_server.app import App

def parse_args():
    load_dotenv()
    def_secret = os.urandom(16)

    parser = argparse.ArgumentParser(description='locker server')
    #parser.add_argument('--secret', default=os.getenv('SECRET', def_secret), 
    #    help='secret key')
    parser.add_argument('--debug', default=False, action='store_true', 
        help='Run flask in debug mode')
    parser.add_argument('--opt', nargs='+', 
        help='CLI options (overriding config)')

    return parser.parse_args()


def check_sanity(cfg):

    status = True

    if 'APPS_PATH' not in cfg:
        print("no APP_PATH in config")
        status = False

    # Not-null keys
    for key in ['APPS_PATH']:
        if cfg[key] is None:
            print(f'Incorrect {key}, must be set')
            status = False

    # Fix path 
    for key in ['APPS_PATH', 'CERT', 'PRIVKEY']:
        if key in cfg:
            if cfg[key] is None:
                continue
            cfg[key] = os.path.expanduser(cfg[key])

    # Check valid dirs
    for key in ['APPS_PATH']:
        if cfg[key] is None:
            continue
        if not os.path.isdir(cfg[key]):
            print(f"Incorrect {key}: {cfg[key]} (No such directory)")
            status = False

    # Check valid files
    for key in ['CERT', 'PRIVKEY']:
        if cfg[key] is None:
            continue
        if not os.path.isfile(cfg[key]):
            print(f"Incorrect {key}: {cfg[key]} (No such file)")
            status = False

    return status

def main():

    # App.apps_path = os.path.expanduser(config['APPS_PATH'])

    args = parse_args()

    # adjust config from CLI options
    if args.opt:
        for opt in args.opt:
            k, v = opt.split('=', 1)
            config[k] = v

    if args.debug:
        print(json.dumps(config, indent=4, sort_keys=True))

    if not check_sanity(config):  
        sys.exit(1)

    App.set_config(config)

    if config.get('ADMIN_EMAIL', None):
        mail_handler = SMTPHandler(config['MAIL_SERVER'], config['MAIL_FROM'], config['ADMIN_EMAIL'], config['MAIL_SUBJ'])
        mail_handler.setLevel(logging.ERROR)
        flask_app.logger.addHandler(mail_handler)

    # flask_app.secret_key = args.secret or os.urandom(24)

    if 'CERT' in config and config['CERT']:
        ssl_context = (config['CERT'], config['PRIVKEY'])
        print(ssl_context)
        flask_app.run(host='0.0.0.0', ssl_context = ssl_context, debug=args.debug)
    else:
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        flask_app.run(host='0.0.0.0', debug=args.debug)

    # app.run(ssl_context="adhoc")

if __name__ == '__main__':
    main()
