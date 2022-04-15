#!/usr/bin/python3

import argparse
import redis
import os
import json

locker_path = None

def get_args():

    def_locker = os.getenv('LOCKER_PATH', '/opt/locker')

    parser = argparse.ArgumentParser(description='locker server admin tool')
    parser.add_argument('--locker', default=def_locker, help=f'Path to locker dir ($LOCKER_PATH={def_locker})')
    parser.add_argument('--load-vhostmap', default=False, action='store_true', help=f'Load vhostmap to redis')
    return parser.parse_args()



def loadvhostmap():
    r = redis.Redis(decode_responses=True)
    vhostmap_path = os.path.join(locker_path, 'var', 'vhostmap.json')
    with open(vhostmap_path) as fh:
        vhmap = json.load(fh)
    print(json.dumps(vhmap, indent=4))
    r.delete('locker:apphostnames')

    for app, hostlist in vhmap.items():
        for host in hostlist: 
            print(f"set {host} to {app}")
            r.hset('locker:apphostnames', host, app)


def main():
    global locker_path

    args = get_args()
    print(args)
    locker_path = args.locker

    if args.load_vhostmap:
        loadvhostmap()

if __name__ == '__main__':
    main()
