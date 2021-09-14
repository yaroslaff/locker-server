import json
import fcntl
from typing import DefaultDict

from .exceptions import (
    DataFileException,
    DataFileReadOnlyException, 
    DataFileContentError
    )

from ..exceptions import SysFilePermissionError



class DataFile():

    def __init__(self, path, mode='r', default=None):
        assert(mode == 'r' or mode == 'rw')
        self.path = path
        self.mode = mode
        self.updated = False
        self.fh = None
        self.default = default
        self.created = False
        
    def __enter__(self):        
        if self.mode == 'r':
            with open(self.path, 'r') as fh:
                self._data = json.load(fh)
        else:
            try:
                self.fh = open(self.path, 'r+')
            except FileNotFoundError as e:
                if self.default is not None:
                    self.created = True
                    self.fh = open(self.path, "w")
                else:
                    raise
            except PermissionError as e:
                raise SysFilePermissionError(f"System Error, permission error")


            fcntl.flock(self.fh, fcntl.LOCK_EX)
            if self.created:
                self._data = self.default
            else:
                try:
                    payload = self.fh.read()
                    if payload:
                        self._data = json.loads(payload) 
                    else:
                        self._data = self.default
                except json.decoder.JSONDecodeError as e:
                    raise DataFileContentError
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            if isinstance(exc_value, DataFileException):
               # no special handling
               # traceback.print_exception(exc_type, exc_value, tb)
               pass

            if self.fh:
                self.fh.close()

        elif self.updated:
            self.fh.seek(0)
            json.dump(self._data, self.fh, indent=4, sort_keys=True)
            self.fh.truncate()
        
        if self.fh:
            # fh could be empty if we open for read
            self.fh.close()

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        if self.mode == 'r':
            raise DataFileReadOnlyException(f'Attempt to modify data file {self.path} opened for {self.mode!r}')
        self._data = value
        self.updated = True

    def user_action_allowed(self, action):
        try:
            return action in self._data['control']['user_actions']
        except KeyError:
            return False
