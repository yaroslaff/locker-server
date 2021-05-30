import os
import pathlib
import shutil
import json

from flask import Blueprint, request, abort, send_file, Response, make_response
from flask_login import login_required, current_user

from ..user import User, UserNotFound, UserHomeRootViolation, UserHomePermissionViolation
from ..app import App

from ..myutils import filelist, fileheaders

api_bp = Blueprint('api', __name__)

#### GET ####
@api_bp.route('/', defaults={'path': ''}, methods=['GET', 'HEAD'])
@api_bp.route('/<path:path>', methods=['GET', 'HEAD'])
def get(path):
    app = App()
    app.check_key()
    if '..' in path:
        abort(404)

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
        if 'cmd' in request.form and request.form['cmd'] == "mkdir":
            p = pathlib.Path(app.localpath(path))
            if not p.exists():
                p.mkdir()
                return Response(f'Created {path}\n')
            else:
                return f'Already exists {path}\n'

    except (UserHomeRootViolation, UserHomePermissionViolation) as e:
        print(f'{type(e)} exception: {e}')
        abort(403)
