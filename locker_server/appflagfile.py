import json
from flask_socketio import SocketIO

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
                if self.path == self.app.localpath("var/" + key):
                    if 'notify' in opts:
                        if opts['notify'] == 'http':
                            print("notify via", opts['URL'])
                            req = {
                                'url': opts['URL'],
                                'method': 'POST',
                                'payload': None

                            }
                            si.redis.sadd('http_requests_queue', json.dumps(req))
                        elif opts['notify'] == 'redis:publish':                            
                            channel = opts.get('channel', 'sleep')
                            data = self.app.name
                            si.redis.publish(channel, data)

                        elif opts['notify'] == 'socketio':
                            event = opts.get('event', 'update')
                            room = opts.get('room', self.app.name)
                            data = opts.get('data')
                            si.socketio.emit(event, data, room=room)





        except KeyError:
            pass

        super().set_flag(flag, user)
