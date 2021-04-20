import os
import json
import shutil

from flask_login import UserMixin
from flask import request
from .myutils import shortdate

class UserException(Exception):
    pass

class UserNotFound(UserException):
    pass

class UserHomeRootViolation(UserException):
    pass

class UserHomePermissionViolation(UserException):
    pass


class User(UserMixin):
    def __init__(self, id_, app, userinfo=None):
        self.id = id_
        self.app = app
        self.userinfo = userinfo
        self.root = self.app.localpath(f'home/{self.id}')


    @staticmethod
    def get(app, user_id):
        user = User(id_=user_id, app=app)
        if os.path.isdir(user.root):
            return user
        raise UserNotFound

    def localpath(self, subpath='', mode=None):
        path = os.path.join(self.root, subpath)

        if mode is None:
            root_path_list = [self.root]
        elif mode == 'r':
            root_path_list = [
                os.path.join(self.root, 'r'),
                os.path.join(self.root, 'rw'),
            ]
        elif mode == 'w':
            root_path_list = [ os.path.join (self.root, 'rw') ]
        else:
            assert(False)

        if not os.path.abspath(path).startswith(self.root):
            raise UserHomeRootViolation()

        if any(os.path.abspath(path).startswith(r) for r in root_path_list):
            return path

        raise UserHomePermissionViolation


    def create_structure(self):
        skeleton = os.path.join(self.app.root,'etc','skeleton')
    
        if os.path.isdir(skeleton):
            shutil.copytree(skeleton, self.root)
        else:
            for subpath in  [ '', 's', 'r', 'rw' ]:
                path = self.localpath(subpath)
                if not os.path.isdir(path):
                    os.mkdir(path)

    def create(self):
        self.create_structure()
        self.update('r/userinfo_create.json')
        self.update()

    def update(self, subpath='r/userinfo.json'):
        path = self.localpath(subpath)
        
        profile = {
            'id': self.id,
            'name': self.userinfo['name'],
            'email': self.userinfo['email'],
            'picture': self.userinfo['picture'],
            'ip': request.remote_addr,
            'date': shortdate() 
        }

        with open(path, "w") as fh:
            json.dump(profile, fh)
        
    def log(self, msg):
        self.app.log(f'u: {self.id} {msg}')

    def disk_usage(self, skip=None, root=None):
        skip = skip or list()
        root = root or self.root

        if os.path.isfile(root):
            if root in skip:
                return 0
            return os.path.getsize(root)

        usage = sum([self.disk_usage(skip=skip, root=os.path.join(root,f)) for f in os.listdir(root)])
        return usage

    def __repr__(self):
        return self.id

