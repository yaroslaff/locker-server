#!/usr/bin/env python3

import argparse
import os
import sys
import subprocess



def create(domain, tpl_path, target, reload):
    # print(domain, tpl_path, vhost_path)
    with open(tpl_path) as fh:
        template = fh.read()
    
    template = template.replace("%host1%", domain[0]).replace('%hostnames%', ' '.join(domain))

    # print(template)
    # print("write to", target)
    with open(target, "w") as fh:
        fh.write(template)

    if reload:
        print("reload nginx...")
        subprocess.run(['nginx', '-s', 'reload'])


def get_args():

    def_template = '/etc/locker/nginx-vhost.tpl'
    def_path = '/etc/nginx/vhosts'

    parser = argparse.ArgumentParser(description='locker-server nginx vhost generator-updater')
    parser.add_argument('-d', '--domain', nargs='+', metavar='DOMAINS', help='domain name(s)')

    g = parser.add_argument_group('Commands')
    g.add_argument('--create', action='store_true', help=f'create or overwrite config file')

    g = parser.add_argument_group('Options')
    g.add_argument('--template', default=def_template, help=f'nginx vhost template, def: {def_template}')
    g.add_argument('--target', help=f'path to nginx config directory, def: {def_path}')
    g.add_argument('--reload', default=False, action='store_true', help=f'reload nginx after operation')


    return parser.parse_args()    

def main():
    args = get_args()

    if args.create:
        if not args.domain:
            print("Need hostnames (-d)")
            sys.exit(1)
        create(args.domain, args.template, args.target, reload=args.reload)


if __name__ == '__main__':
    main()