from .datafile import DataFile

"""

    File with user list and bingings

"""

class BindingsFile(DataFile):
    def get_binding(self, provider, sub):
        """return username based on provider/uid or None"""
        try:
            return self._data['bindings'][provider][sub]
        except KeyError:
            return None

    def get_user_bindings(self, username):
        #bindings = dict()
        #for k in self._data['bindings']:
        #    bindings[k]  = username in self._data['bindings'][k].values()

        return {k: username in self._data['bindings'][k].values() for k in self._data['bindings']}

    def create(self, provider, sub):                
        index = self._data['control']['last'] + 1
        self._data['control']['last'] = index
        username = f'u{index}'
        self.bind(provider, sub, username)
        return username
        
    def bind(self, provider, sub, username):
        if provider not in self._data['bindings']:
            self._data['bindings'][provider] = dict()

        self._data['bindings'][provider][sub] = username
        self.updated = True
    

