import datetime
import os
import requests
import time

def myip():
    url = 'https://ifconfig.me/'

    while True:
        try:
            r = requests.get(url)
        except requests.exceptions.RequestException:
            time.sleep(1)
            pass
        if r.status_code == 200:
            return r.text
        else:
            time.sleep(5)


def shortdate(dt=None):
    dt = dt or datetime.datetime.now() 
    return dt.strftime("%Y/%m/%d %H:%M:%S") 

def str2bool(s: str) -> bool:
    """ True if string is yes/1/true/... """
    if s is None:
        return False
    return s.lower() in ['yes', '1', 'true', 'да', 'о, да, мой адмирал']

def timesuffix(t: str):

    size = {
        'd': 86400,
        'h': 3600,
        'm': 60,
        's': 1
    }

    if not t:
        return 0

    try:
        m = size[t[-1]] # get multiplier
        return int(t[:-1]) * m
    except KeyError:
        return int(t)

def filetype(path):
    if os.path.isdir(path):
        return 'DIR'
    elif os.path.isfile(path):
        return 'FILE'
    else:
        return 'OTHER'

def filelist(dirpath):
    def fileinfo(path):
        stat = os.stat(path)

        return {'size': stat.st_size, 'type': filetype(path), 'mtime': stat.st_mtime}

    return {file: fileinfo(os.path.join(dirpath, file)) for file in os.listdir(dirpath)}

def fileheaders(path):
    headers = dict()
    stat = os.stat(path)

    headers['X-FileType'] = filetype(path)
    headers['X-FileMTime'] = stat.st_mtime
    headers['X-FileSize'] = stat.st_size
    return headers

