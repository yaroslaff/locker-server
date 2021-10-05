import json

from .datafile.flagfile import FlagFile

from . serverinstance import ServerInstance

si = ServerInstance()

class AppFlagFile(FlagFile):

    def __init__(self, app, path, mode='r', default=None):
        self.app = app
        super().__init__(path, mode, default)

    def set_flag(self, flag, user):
        options = self.app.get_config('etc/options.json')

        try:
            for key, opts in options['flag-options'].items():
                if self.path == self.app.localpath(key):
                    print(opts)
                    if opts['notify'] == 'http':
                        print("notify via", opts['URL'])
                        req = {
                            'url': opts['URL'],
                            'method': 'POST',
                            'payload': None

                        }
                        si.redis.sadd('http_requests_queue', json.dumps(req))

        except KeyError:
            pass

        super().set_flag(flag, user)
