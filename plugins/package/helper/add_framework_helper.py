
import os
import os.path
import json
import re
import shlex

import cocos


class AddFrameworkHelper(object):
    IOS_HEADER_MATCH_TAG = '(\$\(_COCOS_HEADER_IOS_BEGIN\))(.+)(\$\(_COCOS_HEADER_IOS_END\))'
    IOS_LIB_BEGIN_TAG = '\$\(_COCOS_LIB_IOS_BEGIN\)'
    IOS_LIB_END_TAG = '\$\(_COCOS_LIB_IOS_END\)'

    MAC_HEADER_MATCH_TAG = '(\$\(_COCOS_HEADER_MAC_BEGIN\))(.+)(\$\(_COCOS_HEADER_MAC_END\))'
    MAC_LIB_BEGIN_TAG = '\$\(_COCOS_LIB_MAC_BEGIN\)'
    MAC_LIB_END_TAG = '\$\(_COCOS_LIB_MAC_END\)'

    WIN32_HEADER_MATCH_TAG = '(\$\(_COCOS_HEADER_WIN32_BEGIN\))(.+)(\$\(_COCOS_HEADER_WIN32_END\))'
    WIN32_LIB_PATH_MATCH_TAG = '(\$\(_COCOS_LIB_PATH_WIN32_BEGIN\))(.+)(\$\(_COCOS_LIB_PATH_WIN32_END\))'
    WIN32_LIB_MATCH_TAG = '(\$\(_COCOS_LIB_WIN32_BEGIN\))(.+)(\$\(_COCOS_LIB_WIN32_END\))'

    ANDROID_HEADER_BEGIN_TAG = '# _COCOS_HEADER_ANDROID_BEGIN'
    ANDROID_HEADER_END_TAG = '# _COCOS_HEADER_ANDROID_END'
    ANDROID_HEADER_PREFIX = 'LOCAL_C_INCLUDES'
    ANDROID_LIB_BEGIN_TAG = '# _COCOS_LIB_ANDROID_BEGIN'
    ANDROID_LIB_END_TAG = '# _COCOS_LIB_ANDROID_END'
    ANDROID_LIB_PREFIX = 'LOCAL_STATIC_LIBRARIES'
    ANDROID_LIB_IMPORT_BEGIN_TAG = '# _COCOS_LIB_IMPORT_ANDROID_BEGIN'
    ANDROID_LIB_IMPORT_END_TAG = '# _COCOS_LIB_IMPORT_ANDROID_END'


    def __init__(self, project, package_data):
        self._package_path = project["packages_dir"] + os.sep + package_data["name"] + '-' + package_data["version"]
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

    def do_add_header_path_on_win(self, command):
        source = command["source"].encode('UTF-8')
        tag = self.__class__.WIN32_HEADER_MATCH_TAG
        self.do_add_header_lib_on_win(source, tag)

    def do_add_header_path_on_android(self, command):
        source = command["source"].encode('UTF-8')
        begin_tag = self.__class__.ANDROID_HEADER_BEGIN_TAG
        end_tag = self.__class__.ANDROID_HEADER_END_TAG
        prefix_tag = self.__class__.ANDROID_HEADER_PREFIX
        self.do_add_header_lib_on_android(source, begin_tag, end_tag, prefix_tag)

    def add_header_path_on_ios_mac(self, source, platform):
        if platform == "ios":
            tag = self.__class__.IOS_HEADER_MATCH_TAG
        elif platform == "mac":
            tag = self.__class__.MAC_HEADER_MATCH_TAG
        else:
            raise cocos.CCPluginError("Invalid platform '%s'" % platform)

        workdir, proj_file_path, lines = self.load_proj_ios_mac()
        contents = []
        tag_found = False
        for line in lines:
            match = re.search(tag, line)
            if match is None:
                contents.append(line)
            else:
                includes = shlex.split(match.group(2))
                headers = []
                for include in includes:
                    include = self.get_ios_mac_path(workdir, include)
                    headers.append(include)

                headers.append(self.get_ios_mac_path(workdir, source))
                headers = list(set(headers))
                start, end = match.span(0)
                parts = []
                parts.append(line[:start])
                parts.append(match.group(1))
                parts.append(' ')
                for header in headers:
                    if header.find(' ') != -1:
                        header = '"' + header + '"'
                    parts.append(header)
                    parts.append(' ')
                parts.append(match.group(3))
                parts.append(line[end:])
                contents.append(''.join(parts))
                tag_found = True

        if tag_found == False:
            raise cocos.CCPluginError("Not found header TAG in project for platform '%s'" % platform)
        else:
            f = open(proj_file_path, "wb")
            f.writelines(contents)
            f.close()

    def do_add_lib_on_ios(self, command):
        self.add_lib_on_ios_mac(command["source"].encode('UTF-8'), "ios")

    def do_add_lib_on_mac(self, command):
        self.add_lib_on_ios_mac(command["source"].encode('UTF-8'), "mac")

    def do_add_lib_on_win(self, command):
        source = command["source"].encode('UTF-8')
        self.do_add_header_lib_on_win(os.path.basename(source), self.__class__.WIN32_LIB_MATCH_TAG)
        self.do_add_header_lib_on_win(os.path.dirname(source), self.__class__.WIN32_LIB_PATH_MATCH_TAG)

    def do_add_header_lib_on_win(self, source, tag):
        workdir, proj_file_path, lines = self.load_proj_win32()
        contents = []
        tag_found = False
        for line in lines:
            match = re.search(tag, line)
            if match is None:
                contents.append(line)
            else:
                includes = re.split(';', match.group(2))
                headers = []
                for include in includes:
                    include = self.get_win32_path(workdir, include)
                    if include is not None:
                        headers.append(include)

                headers.append(self.get_win32_path(workdir, source))
                headers = list(set(headers))
                start, end = match.span(0)
                parts = []
                parts.append(line[:start])
                parts.append(match.group(1))
                parts.append(';')
                for header in headers:
                    if header.find(' ') != -1:
                        header = '"' + header + '"'
                    parts.append(header)
                    parts.append(';')
                parts.append(match.group(3))
                parts.append(line[end:])
                contents.append(''.join(parts))
                tag_found = True

        if tag_found == False:
            raise cocos.CCPluginError("Not found header TAG in project for platform 'win32'")
        else:
            f = open(proj_file_path, "wb")
            f.writelines(contents)
            f.close()

    def do_add_lib_on_android(self, command):
        source = command["source"].encode('UTF-8')
        begin_tag = self.__class__.ANDROID_LIB_BEGIN_TAG
        end_tag = self.__class__.ANDROID_LIB_END_TAG
        prefix_tag = self.__class__.ANDROID_LIB_PREFIX
        self.do_add_header_lib_on_android(source, begin_tag, end_tag, prefix_tag)

        source = command["import-module"].encode('UTF-8')
        begin_tag = self.__class__.ANDROID_LIB_IMPORT_BEGIN_TAG
        end_tag = self.__class__.ANDROID_LIB_IMPORT_END_TAG
        self.do_add_header_lib_on_android(source, begin_tag, end_tag, None, True)

    def do_add_header_lib_on_android(self, source, begin_tag, end_tag, prefix_tag, is_import = False):
        workdir, proj_pbx_path, lines = self.load_proj_android()
        contents = []
        lib_begin = False
        tag_found = False
        libs = []
        for line in lines:
            if lib_begin == False:
                contents.append(line)
                match = re.search(begin_tag, line)
                if not match is None:
                    lib_begin = True
                    tag_found = True
            else:
                if prefix_tag is not None:
                    match = re.search(prefix_tag, line)
                    if match is not None:
                        continue

                match = re.search(end_tag, line)
                if match is None:
                    libs.append(self.get_android_path(workdir, line, is_import))
                else:
                    # add new lib to libs
                    libs.append(self.get_android_path(workdir, source, is_import))
                    libs = list(set(libs))
                    count = len(libs)
                    cur = 1
                    if count > 0 and prefix_tag is not None:
                        contents.append(prefix_tag)
                        contents.append(" += \\\n")
                    for lib in libs:
                        if cur < count and prefix_tag is not None:
                            contents.append('    ' + lib + ' \\')
                        elif is_import is False:
                            contents.append('    ' + lib)
                        else:
                            contents.append('$(call import-module,')
                            contents.append(lib)
                            contents.append(')')
                        contents.append("\n")

                    libs = []
                    lib_begin = False
                    contents.append(line)

        if tag_found == False:
            raise cocos.CCPluginError("Not found lib TAG in project for platform 'android'")
        else:
            f = open(proj_pbx_path, "wb")
            f.writelines(contents)
            f.close()

    def add_lib_on_ios_mac(self, source, platform):
        if platform == "ios":
            begin_tag = self.__class__.IOS_LIB_BEGIN_TAG
            end_tag = self.__class__.IOS_LIB_END_TAG
        elif platform == "mac":
            begin_tag = self.__class__.MAC_LIB_BEGIN_TAG
            end_tag = self.__class__.MAC_LIB_END_TAG
        else:
            raise cocos.CCPluginError("Invalid platform '%s'" % platform)

        workdir, proj_pbx_path, lines = self.load_proj_ios_mac()
        contents = []
        lib_begin = False
        tag_found = False
        libs = []
        for line in lines:
            if lib_begin == False:
                contents.append(line)
                match = re.search(begin_tag, line)
                if not match is None:
                    lib_begin = True
                    tag_found = True
            else:
                match = re.search(end_tag, line)
                if match is None:
                    libs.append(self.get_ios_mac_path(workdir, line))
                else:
                    # add new lib to libs
                    libs.append(self.get_ios_mac_path(workdir, source))
                    libs = list(set(libs))
                    for lib in libs:
                        contents.append('\t\t\t\t\t"' + lib + '",\n')

                    libs = []
                    lib_begin = False
                    contents.append(line)

        if tag_found == False:
            raise cocos.CCPluginError("Not found lib TAG in project for platform '%s'" % platform)
        else:
            f = open(proj_pbx_path, "wb")
            f.writelines(contents)
            f.close()

    def get_ios_mac_path(self, project_path, source):
        source = source.strip(',"\t\n\r')
        if not source[:10] == '$(SRCROOT)':
            source = '$(SRCROOT)' + os.sep + os.path.relpath(self._project["packages_dir"] + os.sep + source,
                                                             project_path)

        return source.replace(os.sep, '/')

    def get_win32_path(self, project_path, source):
        if source == ";" or source == "":
            return None

        if source.find('\\') == -1 and source.find('/') == -1:
            return source

        source = source.strip(',"\t\n\r')
        if not source[:13] == '$(ProjectDir)':
            source = '$(ProjectDir)' + os.sep + os.path.relpath(self._project["packages_dir"] + os.sep + source,
                                                             project_path)

        return source.replace('/', '\\')

    def get_android_path(self, project_path, source, ignore_local_path):
        source = source.strip(' ,"\t\n\r')

        if source.find('\\') == -1 and source.find('/') == -1:
            return source

        if source[-2:] == ' \\':
            source = source[0:-2]
        if source[:21] == '$(call import-module,':
            # strip "$(call import-module, ../../../../packages/"
            source = source[21:-1].strip('./\\')
            if source[:8] == "packages":
                source = source[9:]
        if not source[:13] == '$(LOCAL_PATH)':
            source = os.path.relpath(self._project["packages_dir"] + os.sep + source, project_path)
            if ignore_local_path is False:
                source = '$(LOCAL_PATH)' + os.sep + source

        return source

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

        proj_file_path = workdir + os.sep + proj_dir + os.sep + "project.pbxproj"
        f = open(proj_file_path, "rb")
        lines = f.readlines()
        f.close()

        return workdir, proj_file_path, lines

    def load_proj_win32(self):
        if not "proj.win32" in self._project:
            print "This project not include proj.win32"
            return

        workdir = self._project["proj.win32"]
        files = os.listdir(workdir)
        for filename in files:
            if filename[-8:] == ".vcxproj":
                proj_file_path = workdir + os.sep +  filename
                break

        if proj_file_path is None:
            print "Not found *.vcxproj in proj.win32"
            return

        f = open(proj_file_path, "rb")
        lines = f.readlines()
        f.close()

        return workdir, proj_file_path, lines

    def load_proj_android(self):
        if not "proj.android" in self._project:
            print "This project not include proj.android"
            return

        workdir = self._project["proj.android"] + os.sep + "jni"
        proj_file_path = workdir + os.sep + "Android.mk"
        if not os.path.isfile(proj_file_path):
            print "Not found Android.mk in proj.android/jni"
            return

        f = open(proj_file_path, "rb")
        lines = f.readlines()
        f.close()

        return workdir, proj_file_path, lines
