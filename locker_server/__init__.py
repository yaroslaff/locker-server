#!/usr/bin/env python3 -u

# Python standard libraries
import json
import os
import sys
import argparse
from urllib import parse
from dotenv import load_dotenv
import logging
import secrets
import time
import traceback
from urllib.parse import urlparse
from logging.handlers import SMTPHandler
import redis

from flask import Flask, make_response, redirect, request, url_for, abort, Response, session, jsonify
from flask_session import Session
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)

from flask_socketio import SocketIO

from .myutils import (str2bool)

# Internal imports
# from db import init_db_command
from locker_server.datafile import BindingsFile

from locker_server.config import config
from locker_server.user import User, UserNotFound
from locker_server.app import App

from locker_server.bp.oidc_client import oidc_bp
from locker_server.bp.home import home_bp
from locker_server.bp.app_api import api_bp
from locker_server.bp.var import var_bp
from .exceptions import AppBadDomainName, LockerException, AppNotFound

from . serverinstance import ServerInstance



si = ServerInstance()
#print("__init__ si id:", id(si))

si.redis = redis.Redis(decode_responses=True)
si.config = config

si.socketio = SocketIO(message_queue = "redis://")

# print(si.redis)

# Only for localhost testing
# os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

log = logging.getLogger()
if str2bool(os.getenv('LOCKER_DEBUG')):    
    err = logging.StreamHandler(stream=sys.stdout)
    err.setLevel(logging.DEBUG)
    log.addHandler(err)
    log.setLevel(logging.DEBUG)

logging.debug('debug logging')

# Flask app setup
flask_app = Flask(__name__)

flask_app.register_blueprint(oidc_bp, url_prefix='/oidc')
flask_app.register_blueprint(home_bp, url_prefix='/~')
flask_app.register_blueprint(api_bp, url_prefix='/app')
flask_app.register_blueprint(var_bp, url_prefix='/var')

# User session management setup
login_manager = LoginManager()
login_manager.init_app(flask_app)


flask_app.config.update(config)
Session(flask_app)

started = time.time()

# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user(user_id):
    app = App(request.host)
    # print("load user", app, user_id)
    try:
        return User.get(app, user_id)
    except UserNotFound:
        return None

# OAuth 2 client setup
# client = WebApplicationClient(GOOGLE_CLIENT_ID)


@flask_app.route("/hello")
def hello():
    return 'Hello'

@flask_app.route("/pubconf")
def pubconf():
    try:
        origin = request.headers['Origin']
    except KeyError:
        origin = None

    response = Response(json.dumps(config['PUBCONF'], indent=4))
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'

    return response

@flask_app.route('/diag')
# @login_required
def diag():
    secure = False
    
    results = {
        'checks': list(),
        'info': dict(),
        'errors': list()
    }

    results['info']['pwd'] = os.getcwd()

    try:

        try:
            app = App(request.host)
        except AppNotFound as e:
            results['errors'].append('App not found')
            return jsonify(results)
        except AppBadDomainName as e:
            results['errors'].append('App bad domain name')
            return jsonify(results)


        # app exists or exception handled
        print("diag app:", app)
        app.log("test log message from /diag")

        try:
            options = app.get_config('etc/options.json')        
        except LockerException as e:
            results['checks'].append(f"ERR: {e}")
        else:
            results['checks'].append("OK: etc/options.json exists")

        if not 'origins' in options or not options['origins']:
            results['errors'].append('Origins not configured')
        
        for o in options['origins']:
            parsed = urlparse(o)
            if parsed.scheme not in ['http','https'] or parsed.path or parsed.params or parsed.query or parsed.fragment:
                results['errors'].append(f"Bad origin value '{o}'")

        try:
            credentials = app.get_config('etc/oidc_credentials.json')        
        except LockerException as e:
            results['checks'].append(f"ERR: {e}")
        else:
            results['checks'].append("OK: etc/oidc_credentials.json exists")

        if 'vendor' in credentials:
            for provider in credentials['vendor']:
                try:
                    c = config['VENDOR_CREDENTIALS'][provider] 
                    results['checks'].append(f'Vendor credentials for {provider} exists')
                except KeyError:
                    results['errors'].append(f'No vendor credentials for {provider}')                    


    except (LockerException, Exception) as e:
        if not secure:
            print("DIAG print_exc:")
            print(type(e), e)
            traceback.print_exc()
        results['errors'].append(str(e))

    return jsonify(results)


@flask_app.route("/")
def index():
    return ''

@flask_app.route("/set_roomspace_secret", methods=['POST'])
def set_roomspace_secret():
    app = App(request.host)
    secret = request.json['secret']
    si.redis.set(f'ws-emit::secret::{app.roomspace}', secret)
    return ''


@flask_app.route('/get_bindings', methods=['GET'])
@login_required
def get_bindings():
    app = App(request.host)
    with BindingsFile(app.localpath('etc/users.json')) as uf:
        bindings = uf.get_user_bindings(current_user.id)
        return app.cross_response(json.dumps(bindings), mimetype='application/json')



@flask_app.route('/authenticated')
# @login_required
def authenticated():

    reply = {'status': False, 'messages': []}

    try:

        try:
            app = App(request.host)
        except AppNotFound:
            reply['messages'].append(f'Not found app {request.host}')
            raise Exception

        try:
            origin = request.headers['Origin']
        except KeyError:
            reply['messages'].append(f'Request missing Origin header')
            origin = None

        # app.check_origin()
        if not app.allowed_origin(origin):
            reply['messages'].append(f'Origin {origin} is incorrect')
            raise Exception

        reply['status'] = current_user.is_authenticated
        
        # reply['messages'].append(f'Authenticated: {reply["status"]}')

    finally:
        response = Response(json.dumps(reply, indent=4))
        if origin:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
        return response

@flask_app.route("/logout", methods=['POST'])
def logout():
    app = App(request.host)
    app.check_origin()    

    if current_user.is_authenticated:
        logout_user()

    return app.cross_response('logged out')


####
# Handling exceptions
####

@flask_app.errorhandler(LockerException)
def handle_locker_exception(error):

    if 'Origin' in request.headers:
        origin = request.headers['Origin']
        headers = {
            'Access-Control-Allow-Origin': origin,
            'Access-Control-Allow-Credentials': 'true'
        }
    else:
        headers = {}

    return Response(response=error.message, status=error.status, headers = headers)
