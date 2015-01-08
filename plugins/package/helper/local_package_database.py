
import os
import os.path
import json

import cocos

class LocalPackagesDatabase(object):
    def __init__(self, path):
        self._path = path
        if os.path.isfile(self._path):
            f = open(self._path, "rb")
            self._data = json.load(f)
            f.close()
        else:
            self._data = {}

    def get_packages(self):
        return self._data.copy()

    def add_package(self, package_data):
        key = package_data["name"] + "-" + package_data["version"]
        self._data[key] = package_data
        self.update_database()
        print "[PACKAGE] add package '%s' ok." % key

    def remove_package(self, package_data):
        key = package_data["name"] + "-" + package_data["version"]
        if key in self._data:
            del self._data[key]
            self.update_database()
            print "[PACKAGE] remove package '%s' ok." % key
        else:
            message = "Fatal: not found specified package '%s'" % key
            raise cocos.CCPluginError(message)

    def update_database(self):
        f = open(self._path, "w+b")
        str = json.dump(self._data, f)
        f.close()
        print "[PACKAGE] update '%s' ok." % self._path

