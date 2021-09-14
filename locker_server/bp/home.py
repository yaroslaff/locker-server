from locker_server.datafile.datafile import DataFile
import os
import json
import time
import traceback


from flask import Blueprint, request, abort, send_file, Response, make_response
from flask.globals import current_app
from flask_login import login_required, current_user

from ..user import User, UserNotFound, UserHomeRootViolation, UserHomePermissionViolation
from ..app import App
from ..myutils import fileheaders, filelist
# from datafile.flagfile import FlagFile
from ..datafile import FlagFile, DataFileInvalidFlag, DataFileContentError
from ..exceptions import FileContentError

home_bp = Blueprint('home', __name__)


#### GET ####
@login_required
def get(path):
    current_user.app.check_origin()

    if '..' in path:
        abort(404)

    # security checks
    # if request.method in ['PUT', 'DELETE']
    try:
        filepath = current_user.localpath(path, 'r')

        if not os.path.exists(filepath):
            current_user.app.abort(404)

        qo = current_user.app.query_options(filepath)

        if os.path.isfile(filepath):
            response = make_response(send_file(filepath))
            response.headers.update(fileheaders(filepath))
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'

            response.headers.update(qo.headers())
            response.headers['Access-Control-Allow-Origin'] = request.headers['Origin']
            response.headers['Access-Control-Allow-Credentials'] = 'true'

            # Disable cache
            # response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'

            return(response)
        elif os.path.isdir(filepath):
            data = json.dumps(filelist(filepath), indent=4)
            response = Response(data)

            response.headers.update(fileheaders(filepath))
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'

            response.headers.update(qo.headers(filepath))
            response.headers['Access-Control-Allow-Origin'] = request.headers['Origin']
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Content-Type'] = 'application/json'

            # Disable cache
            return(response)

        else:
            return current_user.app.cross_response(response='')
    except (UserHomeRootViolation, UserHomePermissionViolation) as e:
        print(f'{type(e)} exception: {e}')
        abort(403)

get.provide_automatic_options = False
get.methods = ['GET']
home_bp.add_url_rule('/', 'get', get)
home_bp.add_url_rule('/<path:path>', 'get', get)

#### PUT ####
@login_required
def put(path):

    current_user.app.check_origin()
    try:
        filepath = current_user.localpath(path, 'w')

        qo = current_user.app.query_options(filepath)

        if not os.path.exists(filepath) and not qo.get_option('create'):
            return current_user.app.abort(403, 'Cannot create new files there')

        max_cl = qo.get_option('max_content_length')
        if max_cl and request.content_length > max_cl:
            return current_user.app.abort(403, f'Content-Length ({request.content_length}) is too big')

        newsize = current_user.disk_usage(skip=[filepath])
        
        if os.path.exists(filepath):
            newsize += os.path.getsize(filepath)
        
        if newsize > current_user.app.limits.home_size():
            return current_user.app.abort(404, 'Homedir size limit exceeded')

        with open(filepath, "wb") as fh:
            fh.write(request.get_data())

        sf = qo.get_option('set_flag')

        if sf:
            filepath = current_user.app.localpath('var/'+sf['file'])

            try:
                with FlagFile(filepath,"rw") as file:
                    file.set_flag(sf['flag'], current_user.id)
            except DataFileInvalidFlag:
                current_user.app.abort(403, 'Invalid flag')            

        response = Response(status=200, response='OK')
        response.headers['Access-Control-Allow-Origin'] = request.headers['Origin']
        response.headers['Access-Control-Allow-Credentials'] = 'true'                
        return(response)
    except (UserHomeRootViolation, UserHomePermissionViolation) as e:
        print(f'{type(e)} exception: {e}')
        abort(403)

put.provide_automatic_options = False
put.methods = ['PUT']
home_bp.add_url_rule('/', 'put', put)
home_bp.add_url_rule('/<path:path>', 'put', put)

#### DELETE ####
@login_required
def delete(path):
    current_user.app.check_origin()
    try:
        filepath = current_user.localpath(path, 'w')
        if os.path.exists(filepath):
            os.unlink(filepath)
            response = Response(status=200, response=f'OK written {path}')
            response.headers['Access-Control-Allow-Origin'] = request.headers['Origin']
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return(response)
        else:
            abort(404)
            
    except (UserHomeRootViolation, UserHomePermissionViolation) as e:
        print(f'{type(e)} exception: {e}')
        abort(403)

delete.provide_automatic_options = False
delete.methods = ['DELETE']
home_bp.add_url_rule('/<path:path>', 'delete', delete)



#### OPTIONS ####

@home_bp.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@home_bp.route('/<path:path>', methods=['OPTIONS'])
# @login_required
def options(path):
    app = App()
    app.check_origin()
    response = app.cross_response(response='')
    if path.startswith('rw/'):
        response.headers['Access-Control-Allow-Methods'] = 'GET, PUT, POST'
        response.headers['Access-Control-Allow-Headers'] = 'X-Token, Content-Type'
    elif path.startswith('r/'):
        response.headers['Access-Control-Allow-Methods'] = 'GET'
        response.headers['Access-Control-Allow-Headers'] = 'X-Token'

    return response


#### POST ####
@home_bp.route('/', defaults={'path': ''}, methods=['POST'])
@home_bp.route('/<path:path>', methods=['POST'])
# @login_required
def post(path):
    app = App()
    app.check_origin()
    response = app.cross_response(response='OK')

    data = request.json

    action = data['action']
    
    if action == 'append':
        try:
            append(path, data)
        except TypeError as e:
            traceback.print_exc()
            response = app.cross_response(status=400, response='Operation failed')

        return response

def append(path, data):
    localpath = current_user.localpath(path,'w')
    try:
        with DataFile(localpath, 'rw', default=data.get('default', None)) as f:
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
