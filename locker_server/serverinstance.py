# empty singleton module to store singletons

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class ServerInstance(metaclass=Singleton):
    def __init__(self):
        self.redis = None
        self.config = None
        
        