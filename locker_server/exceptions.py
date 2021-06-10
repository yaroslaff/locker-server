class LockerException(Exception):
    status = 500

    def __init__(self, message, status=None):
        Exception.__init__(self)
        self.message = message
        if status is not None:
            self.status = status
    
    def __str__(self):
        return f'{self.status}: {self.message}'

class AppUnconfigured(LockerException):
    pass

class AppNotFound(LockerException):
    pass

class AppBadDomainName(LockerException):
    pass

class FileContentError(LockerException):
    status = 409

class SysFilePermissionError(LockerException):
    pass