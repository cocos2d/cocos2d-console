
# python
import os, os.path
import sys
import json
import shutil
import cocos
import json
from pprint import pprint

class InstallHelper(object):
    def __init__(self, project, package_data):
        self._package_path = project["packages_dir"] + os.sep + package_data["name"]
        self._install_json_path = self._package_path + os.sep + "install.json"
        f = open(self._install_json_path, "rb")
        self._commands = json.load(f)
        f.close()

    def run(self):
        for command in self._commands:
            try:
                name = "do_" + command["command"]
                cmd = getattr(self, name)
            except AttributeError:
                raise cocos.CCPluginError("cmd = %s is not found" % name)

            try:
                cmd(command)
            except Exception as e:
                raise cocos.CCPluginError(str(e))

    def do_add_lib_to_project(self, command):
        print "add_lib_to_project"
        print self, command

