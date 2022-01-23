import time

from locker_server.datafile.datafile import DataFile
from .datafile import FlagFile, DataFileInvalidFlag, DataFileContentError
from .exceptions import FileContentError

"""
    lower-level file operations without any access-control
"""

def list_append(localpath, data, default=None):
    # localpath = current_user.localpath(path,'w')
    try:
        with DataFile(localpath, 'rw', default=default) as f:
            content = f.data

            # update magic fields in data[e]
            for key in data['e']:
                if key.startswith('_'):
                    if key == '_timestamp':
                        data['e'][key] = int(time.time())
                    if key == '_id':
                        if len(content):
                            max_e = max(content, key = lambda x: x.get('_id', 0))
                            data['e'][key] = max_e['_id'] + 1
                        else:
                            data['e'][key] = 0

            content.append(data['e'])
            f.data = content

    except DataFileContentError as e:
        raise FileContentError(f'Content error with file {request.path!r}')

def list_delete(localpath, data, default=None):

    # localpath = current_user.localpath(path,'w')
    with DataFile(localpath, 'rw', default=data.get('default', None)) as f:
        content = f.data

        _id = data['_id']

        sz = len(content)

        content = list(filter(lambda d: d['_id']!=_id, content))

        f.data = content
        return sz - len(content)
        