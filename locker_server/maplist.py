#!/usr/bin/env python3

import json

class Maplist:
    """ map values to list of other values """

    def __init__(self, path=None, map=None, check_key=True):
        self.path = path
        self._map = map or dict()
        self._reverse = dict()
        self.check_key = check_key

        if(self.path):
            try:
                self.load()
            except FileNotFoundError:
                pass
    
    def load(self, path=None):
        path = path or self.path
        self.path = path
        with open(self.path) as fh:
            self._map = json.load(fh)
        self.build_reverse()
    
    def build_reverse(self):
        self._reverse = dict()
        for k, vlist in self._map.items():
            for v in vlist:
                self._reverse[v] = k
    
    def resolve(self, k):
        if self.check_key and k in self._map:
            return k
        return self._reverse[k]

    def __getitem__(self, k):
        return self.resolve(k)

    def delete(self, k):
        vlist = self._map[k]
        del self._map[k]
        for v in vlist:
            del self._reverse[v]
    
    def update(self, k, vlist):
        try:
            self.delete(k)
        except KeyError:
            pass

        self._map[k] = vlist
        for v in vlist:
            self._reverse[v] = k        

    def __setitem__(self, k, vlist):
        self.update(k, vlist)

    def __repr__(self):
        return(f"maplist {len(self._map)} to {len(self._reverse)}")

    def dump(self):
        print(self)
        for k, vlist in self._map.items():
            print(f"  {k}: {vlist}")

    def save(self, path=None):
        path = path or self.path
        self.path = path

        with open(self.path, "w") as fh:
            json.dump(self._map, fh, indent=4, sort_keys=True)
