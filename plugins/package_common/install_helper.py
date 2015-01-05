
# python
import os, os.path
import sys
import json
import shutil
import cocos
import json
import re
from pprint import pprint

class InstallHelper(object):
    def __init__(self, project, package_data):
        self._package_path = project["packages_dir"] + os.sep + package_data["name"]
        self._install_json_path = self._package_path + os.sep + "install.json"
        f = open(self._install_json_path, "rb")
        self._commands = json.load(f)
        self._project = project
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
        platforms = command["platform"]
        for platform in platforms:
            name = "do_add_lib_to_project_on_" + platform
            cmd = getattr(self, name)
            cmd(command)

    def get_ios_mac_lib_path(self, project_path, libfilename):
        libfilename = libfilename.strip(',"\t\n\r')
        if not libfilename[:10] == '${SRCROOT}':
            libfilename = '${SRCROOT}' + os.sep + os.path.relpath(self._project["packages_dir"] + os.sep + libfilename, project_path)
        return libfilename

    def do_add_lib_to_project_on_ios(self, command):
        if not "proj.ios_mac" in self._project:
            print "This project not include proj.ios_mac"
            return

        workdir = self._project["proj.ios_mac"]
        files = os.listdir(workdir)
        for filename in files:
            if filename[-10:] == ".xcodeproj":
                proj_dir = filename
                break

        if proj_dir is None:
            print "Not found *.xcodeproj in proj.ios_mac"
            return

        if not os.path.isdir(workdir + os.sep + proj_dir):
            raise cocos.CCPluginError("'%s' is not xcode project" % proj_dir)

        proj_pbx_path = workdir + os.sep + proj_dir + os.sep + "project.pbxproj"
        f = open(proj_pbx_path, "rb")
        lines = f.readlines()
        f.close()

        contents = []
        lib_begin = False
        libs = []
        for line in lines:
            if lib_begin == False:
                contents.append(line)
                match = re.search('\$\(_COCOS_LIB_IOS_BEGIN\)', line)
                if not match is None:
                    lib_begin = True
            else:
                match = re.search('\$\(_COCOS_LIB_IOS_END\)', line)
                if match is None:
                    libs.append(self.get_ios_mac_lib_path(workdir, line))
                else:
                    # add new lib to libs
                    libs.append(self.get_ios_mac_lib_path(workdir, command["source"].encode('UTF-8')))
                    libs = list(set(libs))
                    for lib in libs:
                        contents.append('\t\t\t\t\t"' + lib + '",\n')

                    libs = []
                    lib_begin = False
                    contents.append(line)

        f = open(proj_pbx_path, "wb")
        f.writelines(contents)
        f.close()

