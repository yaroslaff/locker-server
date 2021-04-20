class LockerException(Exception):
    status_code = 500

    def __init__(self, message, status=None):
        Exception.__init__(self)
        self.message = message
        if status is not None:
            self.status = status
    
    def __str__(self):
        return self.message

class AppUnconfigured(LockerException):
    pass

class AppNotFound(LockerException):
    pass