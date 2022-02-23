import os
import pathlib
import shutil
import fcntl
import json
from itertools import islice
import traceback

from flask import Blueprint, request, abort, send_file, Response, make_response
from flask_login import login_required, current_user

from ..user import User, UserNotFound, UserHomeRootViolation, UserHomePermissionViolation
from ..app import App

from ..myutils import filelist, fileheaders
from ..fileops import list_append, list_delete

api_bp = Blueprint('api', __name__)

#### GET ####
@api_bp.route('/', defaults={'path': ''}, methods=['GET', 'HEAD'])
@api_bp.route('/<path:path>', methods=['GET', 'HEAD'])
def get(path):
    app = App()    
    app.check_key()
    if '..' in path:
        abort(404)

    app.log(f"GET {path}")

    # security checks
    # if request.method in ['PUT', 'DELETE']
    try:
        filepath = app.localpath(path)

        if not os.path.exists(filepath):
            abort(404)

        headers = fileheaders(filepath)

        if request.method == 'HEAD':
            response = Response()
            response.headers.update(headers)
            return(response)

        if os.path.isfile(filepath):
            response = make_response(send_file(filepath))
            response.headers.update(headers)
            return(response)

        elif os.path.isdir(filepath):
            # return as dir
            data = json.dumps(filelist(filepath), indent=4)
            response = Response(data)
            response.headers.update(headers)
            response.headers['Content-Type'] = 'application/json'
            return(response)
        else:
            abort(404)
    except (UserHomeRootViolation, UserHomePermissionViolation) as e:
        print(f'{type(e)} exception: {e}')
        abort(403)

#### PUT ####
@api_bp.route('/<path:path>', methods=['PUT'])
def put(path):

    app = App()
    app.check_key()

    if '..' in path:
        abort(404)

    # security checks
    # if request.method in ['PUT', 'DELETE']
    try:
        filepath = app.localpath(path)
        dirpath = os.path.dirname(filepath)
        
        with open(filepath, "wb") as fh:
            fh.write(request.get_data())
        app.tracewrite(method='API PUT', path=path)
        return Response(f'Uploaded {path}\n')

    except (UserHomeRootViolation, UserHomePermissionViolation) as e:
        print(f'{type(e)} exception: {e}')
        abort(403)

#### DELETE ####
@api_bp.route('/<path:path>', methods=['DELETE'])
def delete(path):

    app = App()
    app.check_key()

    if '..' in path:
        abort(404)

    # security checks
    # if request.method in ['PUT', 'DELETE']
    try:
        filepath = app.localpath(path)
        if os.path.exists(filepath):
            if os.path.isfile(filepath):
                os.unlink(filepath)
                return Response(f'Deleted file {path}\n')
            elif os.path.isdir(filepath):
                if 'rmdir' in request.headers:
                    if 'recursive' in request.headers:
                        shutil.rmtree(filepath)
                        return f'Deleted (recursively) dir {path}\n'
                    else:
                        os.rmdir(filepath)
                        return f'Deleted dir {path}\n'
                else:
                    return abort(400, f'{path} is directory, but rmdir header is not set')

        else:
            abort(404)

    except OSError as e:
        abort(409, str(e))

    except (UserHomeRootViolation, UserHomePermissionViolation) as e:
        print(f'{type(e)} exception: {e}')
        abort(403)

#### POST (MKDIR) ####
@api_bp.route('/<path:path>', methods=['POST'])
def post(path):
    app = App()
    
    app.check_key()

    if '..' in path:
        abort(404)

    try:
        payload = request.get_json()
        # cmd = request.form['cmd']
        cmd = payload['cmd']
    except ValueError as e:
        abort(400, 'Missing cmd')

    try:
        if cmd == "mkdir":
            p = pathlib.Path(app.localpath(path))
            if not p.exists():
                p.mkdir()
                return Response(f'Created {path}\n')
            else:
                return f'Already exists {path}\n'

        elif cmd == "get_flags":
            flag = payload.get('flag','flag')
            n = int(payload.get('n', 10))    
            return get_flags(app, path, flag, n)
            
        elif cmd == "drop_flags":
            flag = payload.get('flag','flag')
            droplist = payload.get('droplist','[]')
            return drop_flags(app, path, flag, droplist)

        elif cmd == "list_append":
            localpath = app.localpath(path)
            try:
                list_append(localpath, request.json)
            except TypeError as e:
                return 'Operation failed', 400
            return 'OK'

        elif cmd == "list_delete":
            localpath = app.localpath(path)
            n = list_delete(localpath, request.json)
            return str(n)


    except (UserHomeRootViolation, UserHomePermissionViolation) as e:
        print(f'{type(e)} exception: {e}')
        abort(403)


#
# support functions
#

def get_flags(app, path, flag, n):
    data = list()
    if n>50:
        n=50

    lpath = app.localpath(path)
    try:
        with open(lpath,"r") as fh:
            flags = json.load(fh)
        f = flags['flags'][flag]
        data = list(flags['flags'][flag].items())[:n]
    except FileNotFoundError:
        abort(404, "No such file")
    except KeyError:
        abort(404, "No such flag")    
    return json.dumps(data, indent=4)

def drop_flags(app, path, flag, droplist):
    lpath = app.localpath(path)

    result = {
        'dropped': [],
        'refreshed': [],
        'miss': []
    }
    with open(lpath,"r+") as fh:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX)
            flags = json.load(fh)
            f = flags['flags'][flag]
            for u, ts in droplist:
                
                if not u in f:
                    result['miss'].append(u)
                    continue
                
                if ts is None or ts==f[u]:
                    del f[u]
                    result['dropped'].append(u)
                    continue

                result['refreshed'].append(u)
            # print(flags)
            if result['dropped']:
                fh.seek(0)
                json.dump(flags, fh, indent=4, sort_keys=True)
            fh.truncate()
        except FileNotFoundError:
            abort(404, "No such flags file")    

        return json.dumps(result, indent=4)
