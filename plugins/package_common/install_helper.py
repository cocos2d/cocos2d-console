
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
    IOS_LIB_BEGIN_TAG = '\$\(_COCOS_LIB_IOS_BEGIN\)'
    IOS_LIB_END_TAG = '\$\(_COCOS_LIB_IOS_END\)'
    MAC_LIB_BEGIN_TAG = '\$\(_COCOS_LIB_MAC_BEGIN\)'
    MAC_LIB_END_TAG = '\$\(_COCOS_LIB_MAC_END\)'

    def __init__(self, project, package_data):
        self._package_path = project["packages_dir"] + os.sep + package_data["name"]
        self._install_json_path = self._package_path + os.sep + "install.json"
        print self._install_json_path
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

    def do_add_lib(self, command):
        platforms = command["platform"]
        for platform in platforms:
            name = "do_add_lib_on_" + platform
            cmd = getattr(self, name)
            cmd(command)

    def do_add_header_path(self, command):
        platforms = command["platform"]
        for platform in platforms:
            name = "do_add_header_path_on_" + platform
            cmd = getattr(self, name)
            cmd(command)

    def do_add_header_path_on_ios(self, command):
        self.add_header_path_on_ios_mac(command["source"].encode('UTF-8'), "ios")

    def do_add_header_path_on_mac(self, command):
        self.add_header_path_on_ios_mac(command["source"].encode('UTF-8'), "mac")

    def add_header_path_on_ios_mac(self, source, platform):
        print source, platform

    def do_add_lib_on_ios(self, command):
        self.add_lib_on_ios_mac(command["source"].encode('UTF-8'), "ios")

    def do_add_lib_on_mac(self, command):
        self.add_lib_on_ios_mac(command["source"].encode('UTF-8'), "mac")

    def add_lib_on_ios_mac(self, source, platform):
        workdir, proj_pbx_path, lines = self.load_proj_ios_mac()

        if platform == "ios":
            begin_tag = self.__class__.IOS_LIB_BEGIN_TAG
            end_tag = self.__class__.IOS_LIB_END_TAG
        elif platform == "mac":
            begin_tag = self.__class__.MAC_LIB_BEGIN_TAG
            end_tag = self.__class__.MAC_LIB_END_TAG
        else:
            raise cocos.CCPluginError("Invalid platform '%s'" % platform)

        contents = []
        lib_begin = False
        libs = []
        for line in lines:
            if lib_begin == False:
                contents.append(line)
                match = re.search(begin_tag, line)
                if not match is None:
                    lib_begin = True
            else:
                match = re.search(end_tag, line)
                if match is None:
                    libs.append(self.get_ios_mac_lib_path(workdir, line))
                else:
                    # add new lib to libs
                    libs.append(self.get_ios_mac_lib_path(workdir, source))
                    libs = list(set(libs))
                    for lib in libs:
                        contents.append('\t\t\t\t\t"' + lib + '",\n')

                    libs = []
                    lib_begin = False
                    contents.append(line)

        f = open(proj_pbx_path, "wb")
        f.writelines(contents)
        f.close()

    def get_ios_mac_lib_path(self, project_path, libfilename):
        libfilename = libfilename.strip(',"\t\n\r')
        if not libfilename[:10] == '${SRCROOT}':
            libfilename = '${SRCROOT}' + os.sep + os.path.relpath(self._project["packages_dir"] + os.sep + libfilename, project_path)
        return libfilename

    def load_proj_ios_mac(self):
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

        return workdir, proj_pbx_path, lines
