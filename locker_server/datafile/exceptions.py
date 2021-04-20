class DataFileException(Exception):
    pass

class DataFileReadOnlyException(DataFileException):
    pass

class DataFileInvalidFlag(DataFileException):
    pass

class DateFileInvalidOperation(DataFileException):
    pass
