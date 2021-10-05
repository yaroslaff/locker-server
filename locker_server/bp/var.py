import os
import json
import time
import fcntl

from flask import Blueprint, request, abort, send_file, Response, make_response
from flask_login import login_required, current_user

from ..user import User, UserNotFound, UserHomeRootViolation, UserHomePermissionViolation
from ..app import App
from ..datafile import FlagFile, DataFileInvalidFlag
from ..appflagfile import AppFlagFile 
from ..exceptions import SysFilePermissionError

var_bp = Blueprint('var', __name__)

#### set_flag ####
def set_flag(app, path):
    app.check_origin()
    response = app.cross_response()
    
    if not current_user.is_authenticated:
        response.status_code = 401
        response.data = 'not auth'
        abort(response)

    with AppFlagFile(app, path,"rw") as file:
        if not file.user_action_allowed('set_flag'):
            app.abort(403, f'This action not allowed for {path}')

        flag = request.json['set_flag']
        try:
            file.set_flag(flag, current_user.id)
        except DataFileInvalidFlag:
            app.abort(403, 'Invalid flag')
        
        current_user.log(f'set_flag {flag}')
        response.data = 'OK'
        return response


#### drop_flag ####
def drop_flag(app, path):
    app.check_origin()
    response = app.cross_response()
    
    if not current_user.is_authenticated:
        response.status_code = 401
        response.data = 'not auth'
        app.abort(response)

    with FlagFile(path,"rw") as file:
        if not file.user_action_allowed('set_flag'):
            app.abort(403, f'This action not allowed for {path}')

        flag = request.json['set_flag']
        timestamp = request.json['timestamp']
        try:
            file.drop_flag(flag, current_user.id, timestamp)
        except DataFileInvalidFlag:
            app.abort(403, 'Invalid flag')
        
        current_user.log(f'drop_flag {flag} {timestamp}')

        response.data = 'OK'
        return response


##################
# Admin functions
##################

#### set_flag_admin ####
def set_flag_admin(app, path):
    app.check_key()

    flag = request.json['set_flag']
    user = request.json['user']

    with FlagFile(path,"rw") as file:
        try:
            file.set_flag(flag, current_user)
        except DataFileInvalidFlag:
            return Response('Invalid flag', status=403)
        return Response('OK')

#### drop_flag_admin ####
def drop_flag_admin(app, path):
    app.check_key()


    flag = request.json['set_flag']
    user = request.json['user']
    timestamp = request.json['timestamp']


    with FlagFile(path,"rw") as file:
        try:
            file.drop_flag(flag, current_user, timestamp)
        except DataFileInvalidFlag:
            return Response('Invalid flag', status=403)

    return Response('OK')

##################
# Web functions
##################


#### POST ####
@var_bp.route('/', defaults={'path': ''}, methods=['POST'])
@var_bp.route('/<path:path>', methods=['POST'])
def post(path):

    actions = {
        'set_flag': set_flag,
        'drop_flag': drop_flag,
        
        'set_flag_admin': set_flag_admin,
        'drop_flag_admin': drop_flag_admin
    }

    if not request.json or 'action' not in request.json:
        return Response('Incorrect JSON request', status=400)

    app = App()

    if '..' in path:
        abort(404)

    try:
        filepath = app.localpath('var/'+path)
        if os.path.isfile(filepath):
            action = actions.get(request.json['action'], lambda: "Incorrect action")
            return action(app, filepath)    
        else:
            print("404")
            # return app.cross_response(response='No such file', status=404)
            app.abort(404)

    except (UserHomeRootViolation, UserHomePermissionViolation) as e:
        print(f'{type(e)} exception: {e}')
        abort(403)

post.provide_automatic_options = False
post.methods = ['POST']
var_bp.add_url_rule('/', 'post', post)
var_bp.add_url_rule('/<path:path>', 'post', post)


#### OPTIONS ####

@var_bp.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@var_bp.route('/<path:path>', methods=['OPTIONS'])
# @login_required
def options(path):
    app = App()
    app.check_origin()
    response = app.cross_response()

    if current_user.is_authenticated:
        app.abort(401, 'not auth')
        
    response.headers['Access-Control-Allow-Methods'] = 'POST'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


