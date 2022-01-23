import os
import json
from os.path import abspath
import re
import datetime

from flask import abort, request, Response, current_app
from flask_login import current_user

from .datafile import DataFileInvalidFlag
from .appflagfile import AppFlagFile
from .exceptions import AppUnconfigured, AppNotFound, AppBadDomainName, AppRestrictions

from .config import config

class QueryOptions:
    def __init__(self, app, data=None):
        self.app = app
        self.data = data or dict()

    def validate_request(self):
        max_cl = self.get_option('max_content_length')
        if max_cl is not None and request.content_length > max_cl:
            raise AppRestrictions(f'Content-Length ({request.content_length}) is too big', status=403)

    def postprocess(self):
        sf = self.get_option('set_flag')
        if sf:
            filepath = self.app.localpath('var/'+sf['file'])

            try:
                with AppFlagFile(self.app, filepath,"rw") as file:
                    file.set_flag(sf['flag'], current_user.id)
            except DataFileInvalidFlag:
                current_user.app.abort(403, 'Invalid flag')            


    def match(self, path):
        if 'filter_methods' in self.data:
            if request.method not in self.data['filter_methods']:
                return False
        
        if 'filter_path' in self.data:
            homedir_regex = '^home/[^/]+'
            fpath = self.data['filter_path'].replace('${HOME}', homedir_regex)
            if not re.match(fpath, self.app.relpath(path)):
                return False 

        return True

    def headers(self):
        try:
            return self.data['headers']
        except KeyError:
            return dict() 

    def get_option(self, name):
        
        defaults = {
            'create': True,
            'max_content_length': 10240,
            'set_flag': None
        }

        try:
            return self.data['options'][name]
        except KeyError:
            return defaults[name]

    def __repr__(self):
        return f'QO: {self.data}'


class AppLimits:
    def __init__(self, app):
        try:
            app_limits = current_app.config['APPS_CONFIG'][app.name]
            expire = datetime.datetime.strptime(app_limits['expire'], '%Y-%m-%d')
            now = datetime.datetime.now()
            if now > expire:
                self.limits = current_app.config['APPS_CONFIG'][app.name]['*']
            else:
                self.limits = app_limits
        except KeyError:
            self.limits = current_app.config['APPS_CONFIG']['*']        

    def home_size(self):
        return self.limits['home_size']*1024
    
    def users(self):
        return self.limits['users']    

class App:

    # apps_path = os.getenv('LOCKER_APPS_PATH', '/opt/locker-apps/')
    apps_path = config['APPS_PATH']
    provider_regex = re.compile('^[a-zA-Z0-9-_]+$')

    def __init__(self, url=None):

        if self.apps_path is None:
            print("App.apps_path not configured")
            abort(500, 'App.apps_path not configured')

        url = url or request.host

        leftpart = url.split('.')[0]

        try:
            self.appname, self.username = leftpart.rsplit('-', 1)
        except ValueError:
            raise AppBadDomainName(f'Bad app domain name {leftpart}')


        assert('/' not in self.appname)
        assert('/' not in self.username)
        assert('.' not in self.appname)
        assert('.' not in self.username)

        self.name = '.'.join([self.username, self.appname])
        self.root = os.path.join(self.apps_path, self.username, self.appname)
        
        assert(os.path.abspath(self.root).startswith(os.path.abspath(self.apps_path)))

        if not self.exist():
            self.log(f"path {self.root} not found on locker server")
            # abort(Response(f'App {self.name!r} not found', status=404))
            raise AppNotFound(f'App {self.name!r} not found', status=404)
        self.loaded_configs=dict()
        self.limits = AppLimits(self)

    @classmethod
    def set_config(cls, config):
        cls.apps_path = config['APPS_PATH']

    def exist(self):
        return os.path.isdir(self.root)

    def __repr__(self):
        return f'App {self.name!r}'
    
    def localpath(self, subpath):
        path = os.path.join(self.root, subpath)
        assert(os.path.abspath(path).startswith(self.root))
        return path

    def def_path(self, subpath):
        # return default path for user file, e.g. "r/file.json"
        defdir = os.path.join(self.root, 'etc/default')
        defpath = os.path.join(defdir, subpath)
        assert(os.path.abspath(defpath).startswith(defdir))
        return defpath

    def get_json_file(self, path):
        with open(self.localpath(path), "r") as fh:
            return json.load(fh)

    def get_credentials(self, provider):
        # sanitize name
        if not self.provider_regex.match(provider):
            abort(Response(status=400, response='Incorrect provider name'))

        # credentials = self.get_json_file('etc/oidc_credentials.json')
        credentials = self.get_config('etc/oidc_credentials.json')

        if provider in credentials.get('vendor', list()):
            # try to get this provider from vendor
            try:
                c = config['VENDOR_CREDENTIALS'][provider] 
            except KeyError as e:
                abort(Response(status=404, response=f'No provider {provider!r} in vendor oidc_credentials'))
            return c

        # get provider from app 
        try:
            c = credentials[provider]
        except KeyError as e:
            abort(Response(status=404, response='No such provider in app oidc_credentials'))
        return c

    def get_config(self, name):
        if name not in self.loaded_configs:
                try:
                    self.loaded_configs[name] = self.get_json_file(name)
                except FileNotFoundError:
                    raise AppUnconfigured(f"Application not configured, missing {name} file")
        return self.loaded_configs[name]
        
    def allowed_key(self, key, address):
        keys = self.get_config('etc/keys.json')
        if not keys:
            # no keys, allow all
            return True
        return any([k['key'] == key and (not k['ip'] or address in k['ip']) for k in keys])

    def check_key(self, key=None, address=None):
        key = key or request.headers.get('X-API-KEY','')
        address = address or request.remote_addr
        if not self.allowed_key(key, address):
            abort(403, 'Incorrect X-API-KEY')

    def allowed_origin(self, origin):
        options = self.get_config('etc/options.json')
        return 'origins' in options and origin in options['origins']

    def check_origin(self, origin = None):
        origin = origin or request.headers.get('Origin', None)
        if not self.allowed_origin(origin):
            abort(403, f'Cross-Origin request not allowed from this origin "{origin}"')

    def cross_response(self, response=None, status=None, mimetype = None):
        status = status or None
        origin = request.headers['Origin']
        headers = {
            'Access-Control-Allow-Origin': origin,
            'Access-Control-Allow-Credentials': 'true'
        }


        return Response(response=response, status=status, headers = headers, mimetype=mimetype)

    def log(self, msg):
        print(f'LOG app: {self.name}: {msg}')

    def abort(self, status, text=None):
        response = self.cross_response(text, status)
        abort(response)

    
    def relpath(self, path):
        return os.path.relpath(path, self.root)

    def query_options(self, path):
        """ return first matching QO """
        
        options = self.get_config('etc/options.json')
        
        if 'query-options' not in options:
            return QueryOptions(self)

        for qo_data in options['query-options']:
            qo = QueryOptions(self, qo_data)
            if qo.match(path):
                # all filters passed
                return qo
        return QueryOptions(self)
    
    def count_users(self):
        return len(os.listdir(os.path.join(self.root, 'home')))

    def readonly(self):
        options = self.get_config('etc/options.json')
        return options.get('readonly', False)

    def accept_new_users(self):
        options = self.get_config('etc/options.json')
        if self.readonly():
            return False
        if not options.get('accept_new_users', True):
            return False
        if self.count_users() >= self.limits.users():
            return False
        return True
