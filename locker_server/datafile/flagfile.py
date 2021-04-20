import time

from .datafile import DataFile
from .exceptions import DataFileInvalidFlag

class FlagFile(DataFile):
    def set_flag(self, flag, user):
        try:
            self._data['flags'][flag][user] = round(time.time(), 2)
            self.updated = True
        except KeyError:
            raise DataFileInvalidFlag('No such flag')

    def drop_flag(self,flag, user, timestamp=None):
        try:
            if timestamp is None or self._data['flags'][flag][user] <= timestamp:
                del self._data['flags'][flag][user]
                self.updated = True
        except KeyError:
            raise DataFileInvalidFlag(f'No such flag or expired')
