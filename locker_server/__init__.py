#!/usr/bin/env python3

# Python standard libraries
import json
import os
import sys
import argparse
from dotenv import load_dotenv
import logging
import secrets
import time
import traceback
from logging.handlers import SMTPHandler

from flask import Flask, make_response, redirect, request, url_for, abort, Response, session, jsonify
from flask_session import Session
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)

# Internal imports
# from db import init_db_command
from locker_server.datafile import UserFile

from locker_server.config import config
from locker_server.user import User, UserNotFound
from locker_server.app import App

from locker_server.bp.oidc_client import oidc_bp
from locker_server.bp.home import home_bp
from locker_server.bp.app_api import api_bp
from locker_server.bp.var import var_bp
from .exceptions import LockerException


# Only for localhost testing
# os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

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

@flask_app.route('/diag')
# @login_required
def diag():
    print("diag get app")
    secure = False

    results = {
        'checks': list(),
        'info': dict(),
        'config': config,
        'errors': list()
    }

    results['info']['pwd'] = os.getcwd()

    try:
        app = App(request.host)

        # app exists or exception handled
        print("app:", app)

        try:
            options = app.get_config('etc/options.json')        
        except LockerException as e:
            results['checks'].append(f"ERR: {e}")
        else:
            results['checks'].append("OK: etc/options.json exists")

        try:
            credentials = app.get_config('etc/oidc_credentials.json')        
        except LockerException as e:
            results['checks'].append(f"ERR: {e}")
        else:
            results['checks'].append("OK: etc/oidc_credentials.json exists")

        if 'vendor' in credentials:
            for provider in credentials['vendor']:
                results['checks'].append(f'Vendor credentials for {provider}')


    except (LockerException, Exception) as e:
        if not secure:
            print(type(e), e)
            traceback.print_exc()
        results['errors'].append(str(e))

    return jsonify(results)


@flask_app.route("/")
def index():
    app = App(request.host)

    if current_user.is_authenticated:
        userinfo = session.get('userinfo', None)
        return (
            "<p>Hello, {}! App: {}. You're ({}) logged in! Email: {}</p>".
                format( app.name, userinfo['name'], userinfo['id'], userinfo['email']
            )
        )
    else:        
        return Response(status=400, response='Not authenticated (index)')


@flask_app.route('/get_bindings', methods=['GET'])
@login_required
def get_bindings():
    app = App(request.host)
    with UserFile(app.localpath('etc/users.json')) as uf:
        bindings = uf.get_user_bindings(current_user.id)
        return app.cross_response(json.dumps(bindings), mimetype='application/json')



@flask_app.route('/authenticated')
# @login_required
def authenticated():

    app = App(request.host)
    try:
        origin = request.headers['Origin']
    except KeyError:
        return Response(status=400, response='Missing "Origin" header')

    app.check_origin()

    if current_user.is_authenticated:
        response = Response(json.dumps(True))
    else:
        response = Response(json.dumps(False))

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
    # print(f"HANDLE EXCEPTION {type(error)}: {error.status_code}")
    response = Response(error.message)
    response.status_code = error.status
    return response