#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos2d "compile" plugin
#
# Copyright 2013 (C) Luis Parravicini
#
# License: MIT
# ----------------------------------------------------------------------------
'''
"compile" plugin for cocos command line tool
'''

__docformat__ = 'restructuredtext'

import cocos
import subprocess
import os
import re
import sys
import shutil
import platform
import json
import build_web
if sys.platform == 'win32':
    import _winreg


def copy_files_in_dir(src, dst):

    for item in os.listdir(src):
        path = os.path.join(src, item)
        if os.path.isfile(path):
            shutil.copy(path, dst)
        if os.path.isdir(path):
            new_dst = os.path.join(dst, item)
            if not os.path.isdir(new_dst):
                os.makedirs(new_dst)
            copy_files_in_dir(path, new_dst)

def copy_files_with_config(config, src_root, dst_root):
    src_dir = config["from"]
    dst_dir = config["to"]

    src_dir = os.path.join(src_root, src_dir)
    dst_dir = os.path.join(dst_root, dst_dir)

    include_rules = None
    if config.has_key("include"):
        include_rules = config["include"]
        include_rules = convert_rules(include_rules)

    exclude_rules = None
    if config.has_key("exclude"):
        exclude_rules = config["exclude"]
        exclude_rules = convert_rules(exclude_rules)

    copy_files_with_rules(src_dir, src_dir, dst_dir, include_rules, exclude_rules)

def copy_files_with_rules(src_rootDir, src, dst, include = None, exclude = None):
    if os.path.isfile(src):
        if not os.path.exists(dst):
            os.makedirs(dst)
        shutil.copy(src, dst)
        return

    if (include is None) and (exclude is None):
        if not os.path.exists(dst):
            os.makedirs(dst)
        copy_files_in_dir(src, dst)
    elif (include is not None):
        # have include
        for name in os.listdir(src):
            abs_path = os.path.join(src, name)
            rel_path = os.path.relpath(abs_path, src_rootDir)
            if os.path.isdir(abs_path):
                sub_dst = os.path.join(dst, name)
                copy_files_with_rules(src_rootDir, abs_path, sub_dst, include = include)
            elif os.path.isfile(abs_path):
                if _in_rules(rel_path, include):
                    if not os.path.exists(dst):
                        os.makedirs(dst)
                    shutil.copy(abs_path, dst)
    elif (exclude is not None):
        # have exclude
        for name in os.listdir(src):
            abs_path = os.path.join(src, name)
            rel_path = os.path.relpath(abs_path, src_rootDir)
            if os.path.isdir(abs_path):
                sub_dst = os.path.join(dst, name)
                copy_files_with_rules(src_rootDir, abs_path, sub_dst, exclude = exclude)
            elif os.path.isfile(abs_path):
                if not _in_rules(rel_path, exclude):
                    if not os.path.exists(dst):
                        os.makedirs(dst)
                    shutil.copy(abs_path, dst)

def _in_rules(rel_path, rules):
    import re
    ret = False
    path_str = rel_path.replace("\\", "/")
    for rule in rules:
        if re.match(rule, path_str):
            ret = True

    return ret

def convert_rules(rules):
    ret_rules = []
    for rule in rules:
        ret = rule.replace('.', '\\.')
        ret = ret.replace('*', '.*')
        ret = "%s" % ret
        ret_rules.append(ret)

    return ret_rules

class CCPluginCompile(cocos.CCPlugin):
    """
    compiles a project
    """

    BUILD_CONFIG_FILE = "build-cfg.json"
    CFG_KEY_WIN32_COPY_FILES = "copy_files"
    CFG_KEY_WIN32_MUST_COPY_FILES = "must_copy_files"

    CFG_KEY_COPY_RESOURCES = "copy_resources"
    CFG_KEY_MUST_COPY_RESOURCES = "must_copy_resources"

    OUTPUT_DIR_NATIVE = "bin"
    OUTPUT_DIR_SCRIPT_DEBUG = "runtime"
    OUTPUT_DIR_SCRIPT_RELEASE = "publish"

    @staticmethod
    def plugin_name():
      return "compile"

    @staticmethod
    def brief_description():
        return "Compiles the current project to binary"

    def _add_custom_options(self, parser):
        from argparse import ArgumentParser
        parser.add_argument("-m", "--mode", dest="mode", default='debug',
                          help="Set the compile mode, should be debug|release, default is debug.")
        parser.add_argument("-j", "--jobs", dest="jobs", type=int, default=1,
                          help="Allow N jobs at once.")

        group = parser.add_argument_group("Android Options")
        group.add_argument("--ap", dest="android_platform", type=int, help='parameter for android-update.Without the parameter,the script just build dynamic library for project. Valid android-platform are:[10|11|12|13|14|15|16|17|18|19]')

        group = parser.add_argument_group("Web Options")
        group.add_argument("--source-map", dest="source_map", action="store_true", help='Enable source-map')

        group = parser.add_argument_group("lua/js project arguments")
        group.add_argument("--no-res", dest="no_res", action="store_true", help="Package without project resources.")

        category = self.plugin_category()
        name = self.plugin_name()
        usage = "\n\t%%prog %s %s -p <platform> [-s src_dir][-m <debug|release>]" \
                "\nSample:" \
                "\n\t%%prog %s %s -p android" % (category, name, category, name)

    def _check_custom_options(self, args):

        if args.mode != 'release':
            args.mode = 'debug'

        self._mode = 'debug'
        if 'release' == args.mode:
            self._mode = args.mode

        self._ap = args.android_platform
        self._jobs = args.jobs

        self._has_sourcemap = args.source_map
        self._no_res = args.no_res

    def _build_cfg_path(self):
        cur_cfg = self._platforms.get_current_config()
        if self._platforms.is_win32_active():
            if cur_cfg.build_cfg_path is not None:
                project_dir = self._project.get_project_dir()
                ret = os.path.join(project_dir, cur_cfg.build_cfg_path)
            else:
                ret = self._platforms.project_path()
        elif self._platforms.is_ios_active():
            ret = os.path.join(self._platforms.project_path(), "ios")
        elif self._platforms.is_mac_active():
            ret = os.path.join(self._platforms.project_path(), "mac")
        else:
            ret = self._platforms.project_path()

        return ret

    def _update_build_cfg(self):
        build_cfg_dir = self._build_cfg_path()
        cfg_file_path = os.path.join(build_cfg_dir, CCPluginCompile.BUILD_CONFIG_FILE)
        if not os.path.isfile(cfg_file_path):
            return

        key_of_copy = None
        key_of_must_copy = None
        if self._platforms.is_android_active():
            from build_android import AndroidBuilder
            key_of_copy = AndroidBuilder.CFG_KEY_COPY_TO_ASSETS
            key_of_must_copy = AndroidBuilder.CFG_KEY_MUST_COPY_TO_ASSERTS
        elif self._platforms.is_win32_active():
            key_of_copy = CCPluginCompile.CFG_KEY_WIN32_COPY_FILES
            key_of_must_copy = CCPluginCompile.CFG_KEY_WIN32_MUST_COPY_FILES

        if key_of_copy is None and key_of_must_copy is None:
            return

        try:
            outfile = None
            open_file = open(cfg_file_path)
            cfg_info = json.load(open_file)
            open_file.close()
            open_file = None
            changed = False
            if key_of_copy is not None:
                if cfg_info.has_key(key_of_copy):
                    src_list = cfg_info[key_of_copy]
                    ret_list = self._convert_cfg_list(src_list, build_cfg_dir)
                    cfg_info[CCPluginCompile.CFG_KEY_COPY_RESOURCES] = ret_list
                    del cfg_info[key_of_copy]
                    changed = True

            if key_of_must_copy is not None:
                if cfg_info.has_key(key_of_must_copy):
                    src_list = cfg_info[key_of_must_copy]
                    ret_list = self._convert_cfg_list(src_list, build_cfg_dir)
                    cfg_info[CCPluginCompile.CFG_KEY_MUST_COPY_RESOURCES] = ret_list
                    del cfg_info[key_of_must_copy]
                    changed = True

            if changed:
                # backup the old-cfg
                split_list = os.path.splitext(CCPluginCompile.BUILD_CONFIG_FILE)
                file_name = split_list[0]
                ext_name = split_list[1]
                bak_name = file_name + "-for-v0.1" + ext_name
                bak_file_path = os.path.join(build_cfg_dir, bak_name)
                if os.path.exists(bak_file_path):
                    os.remove(bak_file_path)
                os.rename(cfg_file_path, bak_file_path)

                # write the new data to file
                with open(cfg_file_path, 'w') as outfile:
                    json.dump(cfg_info, outfile, sort_keys = True, indent = 4)
                    outfile.close()
                    outfile = None
        finally:
            if open_file is not None:
                open_file.close()

            if outfile is not None:
                outfile.close()

    def _convert_cfg_list(self, src_list, build_cfg_dir):
        ret = []
        for element in src_list:
            ret_element = {}
            if str(element).endswith("/"):
                sub_str = element[0:len(element)-1]
                ret_element["from"] = sub_str
                ret_element["to"] = ""
            else:
                element_full_path = os.path.join(build_cfg_dir, element)
                if os.path.isfile(element_full_path):
                    to_dir = ""
                else:
                    to_dir = os.path.basename(element)
                ret_element["from"] = element
                ret_element["to"] = to_dir

            ret.append(ret_element)

        return ret

    def _is_debug_mode(self):
        return self._mode == 'debug'


    def build_android(self):
        if not self._platforms.is_android_active():
            return

        project_dir = self._project.get_project_dir()
        build_mode = self._mode
        if self._project._is_script_project():
            if build_mode == 'debug':
                output_dir = os.path.join(project_dir, CCPluginCompile.OUTPUT_DIR_SCRIPT_DEBUG, 'android')
            else:
                output_dir = os.path.join(project_dir, CCPluginCompile.OUTPUT_DIR_SCRIPT_RELEASE, 'android')

            if self._project._is_lua_project():
                cocos_root = os.path.join(project_dir, 'frameworks' ,'cocos2d-x')
            else:
                cocos_root = os.path.join(project_dir, 'frameworks' ,'%s-bindings' % self._project.get_language(), 'cocos2d-x')

        else:
            cocos_root = os.path.join(project_dir, 'cocos2d')
            output_dir = os.path.join(project_dir, CCPluginCompile.OUTPUT_DIR_NATIVE, build_mode, 'android')

        # check environment variable
        ant_root = cocos.check_environment_variable('ANT_ROOT')
        ndk_root = cocos.check_environment_variable('NDK_ROOT')
        sdk_root = cocos.check_environment_variable('ANDROID_SDK_ROOT')
        project_android_dir = self._platforms.project_path()

        from build_android import AndroidBuilder
        builder = AndroidBuilder(self._verbose, cocos_root, project_android_dir, self._no_res)

        # build native code
        cocos.Logging.info("building native")
        ndk_build_param = "-j%s" % self._jobs
        builder.do_ndk_build(ndk_root, ndk_build_param, build_mode)

        # build apk
        cocos.Logging.info("building apk")
        self.apk_path = builder.do_build_apk(sdk_root, ant_root, self._ap, build_mode, output_dir) 

        cocos.Logging.info("build succeeded.")

    def check_ios_mac_build_depends(self):
        commands = [
            "xcodebuild",
            "-version"
        ]
        child = subprocess.Popen(commands, stdout=subprocess.PIPE)

        xcode = None
        version = None
        for line in child.stdout:
            if 'Xcode' in line:
                xcode, version = str.split(line, ' ')

        child.wait()

        if xcode is None:
            message = "Xcode wasn't installed"
            raise cocos.CCPluginError(message)

        if version <= '5':
            message = "Update xcode please"
            raise cocos.CCPluginError(message)

        cfg_obj = self._platforms.get_current_config()
        if cfg_obj.proj_file is not None:
            xcodeproj_name = cfg_obj.proj_file
            name = os.path.basename(xcodeproj_name)
        else:
            name, xcodeproj_name = self.checkFileByExtention(".xcodeproj", self._platforms.project_path())
        if not xcodeproj_name:
            message = "Can't find the \".xcodeproj\" file"
            raise cocos.CCPluginError(message)

        self.project_name = name
        self.xcodeproj_name = xcodeproj_name

    def _remove_res(self, target_path):
        build_cfg_dir = self._build_cfg_path()
        cfg_file = os.path.join(build_cfg_dir, CCPluginCompile.BUILD_CONFIG_FILE)
        if os.path.exists(cfg_file) and os.path.isfile(cfg_file):
            # have config file
            open_file = open(cfg_file)
            cfg_info = json.load(open_file)
            open_file.close()
            if cfg_info.has_key("remove_res"):
                remove_list = cfg_info["remove_res"]
                for f in remove_list:
                    res = os.path.join(target_path, f)
                    if os.path.isdir(res):
                        # is a directory
                        if f.endswith('/'):
                            # remove files & dirs in it
                            for sub_file in os.listdir(res):
                                sub_file_fullpath = os.path.join(res, sub_file)
                                if os.path.isfile(sub_file_fullpath):
                                    os.remove(sub_file_fullpath)
                                elif os.path.isdir(sub_file_fullpath):
                                    shutil.rmtree(sub_file_fullpath)
                        else:
                            # remove the dir
                            shutil.rmtree(res)
                    elif os.path.isfile(res):
                        # is a file, remove it
                        os.remove(res)

    def build_ios(self):
        if not self._platforms.is_ios_active():
            return

        if not cocos.os_is_mac():
            raise cocos.CCPluginError("Please build on MacOSX")

        self.check_ios_mac_build_depends()

        project_dir = self._project.get_project_dir()
        ios_project_dir = self._platforms.project_path()
        build_mode = self._mode
        if self._project._is_script_project():
            if build_mode == 'debug':
                output_dir = os.path.join(project_dir, CCPluginCompile.OUTPUT_DIR_SCRIPT_DEBUG, 'ios')
            else:
                output_dir = os.path.join(project_dir, CCPluginCompile.OUTPUT_DIR_SCRIPT_RELEASE, 'ios')
        else:
            output_dir = os.path.join(project_dir, CCPluginCompile.OUTPUT_DIR_NATIVE, build_mode, 'ios')

        projectPath = os.path.join(ios_project_dir, self.xcodeproj_name)
        pbxprojectPath = os.path.join(projectPath, "project.pbxproj")

        f = file(pbxprojectPath)
        contents = f.read()

        section = re.search(r"Begin PBXProject section.*End PBXProject section", contents, re.S)

        if section is None:
            message = "Can't find iOS target"
            raise cocos.CCPluginError(message)

        targets = re.search(r"targets = (.*);", section.group(), re.S)
        if targets is None:
            message = "Can't find iOS target"
            raise cocos.CCPluginError(message)

        targetName = None
        cfg_obj = self._platforms.get_current_config()
        if cfg_obj.target_name is not None:
            targetName = cfg_obj.target_name
        else:
            names = re.split("\*", targets.group())
            for name in names:
                if "iOS" in name:
                    targetName = str.strip(name)

        if targetName is None:
            message = "Can't find iOS target"
            raise cocos.CCPluginError(message)

        if os.path.isdir(output_dir):
            target_app_dir = os.path.join(output_dir, "%s.app" % targetName[:targetName.find(' ')])
            if os.path.isdir(target_app_dir):
                shutil.rmtree(target_app_dir)

        cocos.Logging.info("building")

        command = ' '.join([
            "xcodebuild",
            "-project",
            "\"%s\"" % projectPath,
            "-configuration",
            "%s" % 'Debug' if self._mode is 'debug' else 'Release',
            "-target",
            "\"%s\"" % targetName,
            "-sdk",
            "iphonesimulator",
            "-arch i386",
            "CONFIGURATION_BUILD_DIR=%s" % (output_dir)
            ])

        self._run_cmd(command)

        filelist = os.listdir(output_dir)

        for filename in filelist:
            name, extention = os.path.splitext(filename)
            if extention == '.a':
                filename = os.path.join(output_dir, filename)
                os.remove(filename)
            if extention == '.app' and name == targetName:
                filename = os.path.join(output_dir, filename)
                newname = os.path.join(output_dir, name[:name.find(' ')]+extention)
                os.rename(filename, newname)
                self._iosapp_path = newname
        
        if self._no_res:
            self._remove_res(self._iosapp_path)
        
        cocos.Logging.info("build succeeded.")


    def build_mac(self):
        if not self._platforms.is_mac_active():
            return

        if not cocos.os_is_mac():
            raise cocos.CCPluginError("Please build on MacOSX")

        self.check_ios_mac_build_depends()

        project_dir = self._project.get_project_dir()
        mac_project_dir = self._platforms.project_path()
        build_mode = self._mode
        if self._project._is_script_project():
            if build_mode == 'debug':
                output_dir = os.path.join(project_dir, CCPluginCompile.OUTPUT_DIR_SCRIPT_DEBUG, 'mac')
            else:
                output_dir = os.path.join(project_dir, CCPluginCompile.OUTPUT_DIR_SCRIPT_RELEASE, 'mac')
        else:
            output_dir = os.path.join(project_dir, CCPluginCompile.OUTPUT_DIR_NATIVE, build_mode, 'mac')


        projectPath = os.path.join(mac_project_dir, self.xcodeproj_name)
        pbxprojectPath = os.path.join(projectPath, "project.pbxproj")

        f = file(pbxprojectPath)
        contents = f.read()

        section = re.search(
            r"Begin PBXProject section.*End PBXProject section",
            contents,
            re.S
        )

        if section is None:
            message = "Can't find Mac target"
            raise cocos.CCPluginError(message)

        targets = re.search(r"targets = (.*);", section.group(), re.S)
        if targets is None:
            message = "Can't find Mac target"
            raise cocos.CCPluginError(message)

        targetName = None
        cfg_obj = self._platforms.get_current_config()
        if cfg_obj.target_name is not None:
            targetName = cfg_obj.target_name
        else:
            names = re.split("\*", targets.group())
            for name in names:
                if "Mac" in name:
                    targetName = str.strip(name)

        if targetName is None:
            message = "Can't find Mac target"
            raise cocos.CCPluginError(message)

        if os.path.isdir(output_dir):
            target_app_dir = os.path.join(output_dir, "%s.app" % targetName[:targetName.find(' ')])
            if os.path.isdir(target_app_dir):
                shutil.rmtree(target_app_dir)

        cocos.Logging.info("building")

        command = ' '.join([
            "xcodebuild",
            "-project",
            "\"%s\"" % projectPath,
            "-configuration",
            "%s" % 'Debug' if self._mode is 'debug' else 'Release',
            "-target",
            "\"%s\"" % targetName,
            "CONFIGURATION_BUILD_DIR=%s" % (output_dir)
            ])

        self._run_cmd(command)

        filelist = os.listdir(output_dir)
        for filename in filelist:
            name, extention = os.path.splitext(filename)
            if extention == '.a':
                filename = os.path.join(output_dir, filename)
                os.remove(filename)
            if extention == '.app' and name == targetName:
                filename = os.path.join(output_dir, filename)
                if ' ' in name:
                    filename = os.path.join(output_dir, filename)
                    newname = os.path.join(output_dir, name[:name.find(' ')]+extention)
                    os.rename(filename, newname)
                    self._macapp_path = newname

        if self._no_res:
            resource_path = os.path.join(self._macapp_path, "Contents", "Resources")
            self._remove_res(resource_path)

        cocos.Logging.info("build succeeded.")


    def build_win32(self):
        if not self._platforms.is_win32_active():
            return

        if not cocos.os_is_win32():
            raise cocos.CCPluginError("Please build on winodws")

        project_dir = self._project.get_project_dir()
        win32_projectdir = self._platforms.project_path()
        build_mode = self._mode
        if self._project._is_script_project():
            if build_mode == 'debug':
                output_dir = os.path.join(project_dir, CCPluginCompile.OUTPUT_DIR_SCRIPT_DEBUG, 'win32')
            else:
                output_dir = os.path.join(project_dir, CCPluginCompile.OUTPUT_DIR_SCRIPT_RELEASE, 'win32')
        else:
            output_dir = os.path.join(project_dir, CCPluginCompile.OUTPUT_DIR_NATIVE, build_mode, 'win32')

        cocos.Logging.info("building")
        try:
            vs = _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\VisualStudio"
            )

            msbuild = _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\MSBuild\ToolsVersions"
            )

        except WindowsError:
            message = "Visual Studio wasn't installed"
            raise cocos.CCPluginError(message)

        vsPath = None
        i = 0
        try:
            while True:
                version = _winreg.EnumKey(vs, i)
                try:
                    if float(version) >= 11.0:
                        key = _winreg.OpenKey(vs, r"SxS\VS7")
                        vsPath,type = _winreg.QueryValueEx(key, version)
                except:
                    pass
                i += 1
        except WindowsError:
            pass

        if vsPath is None:
            message = "Can't find the Visual Studio's path in the regedit"
            raise cocos.CCPluginError(message)

        msbuildPath = None
        i = 0
        try:
            while True:
                version = _winreg.EnumKey(msbuild,i)
                try:
                    if float(version) >= 4.0:
                        key = _winreg.OpenKey(msbuild, version)
                        msbuildPath, type = _winreg.QueryValueEx(
                            key,
                            "MSBuildToolsPath"
                        )
                except:
                    pass
                i += 1
        except WindowsError:
            pass

        if msbuildPath is None:
            message = "Can't find the MSBuildTools' path in the regedit"
            raise cocos.CCPluginError(message)

        cfg_obj = self._platforms.get_current_config()
        if cfg_obj.sln_file is not None:
            sln_name = cfg_obj.sln_file
            if cfg_obj.project_name is None:
                import cocos_project
                raise cocos.CCPluginError("Must specified \"%s\" when \"%s\" is specified in file \"%s\"") % \
                      (cocos_project.Win32Config.KEY_PROJECT_NAME, cocos_project.Win32Config.KEY_SLN_FILE, cocos_project.Project.CONFIG)
            else:
                name = cfg_obj.project_name
        else:
            name, sln_name = self.checkFileByExtention(".sln", win32_projectdir)
            if not sln_name:
                message = "Can't find the \".sln\" file"
                raise cocos.CCPluginError(message)

        self.project_name = name
        msbuildPath = os.path.join(msbuildPath, "MSBuild.exe")
        projectPath = os.path.join(win32_projectdir, sln_name)
        build_mode = 'Debug' if self._is_debug_mode() else 'Release'

        commands = ' '.join([
            msbuildPath,
            projectPath,
            "/maxcpucount:4",
            "/t:%s" % self.project_name,
            "/p:configuration=%s" % build_mode
        ])

        self._run_cmd(commands)

        cocos.Logging.info("build succeeded.")
        
        # copy files
        build_folder_name = "%s.win32" % build_mode
        build_folder_path = os.path.join(win32_projectdir, build_folder_name)
        if not os.path.isdir(build_folder_path):
            message = "Can not find the %s" % build_folder_path
            raise cocos.CCPluginError(message)

        # remove the files in output dir (keep the exe files)
        if os.path.exists(output_dir):
            output_files = os.listdir(output_dir)
            for element in output_files:
                ele_full_path = os.path.join(output_dir, element)
                if os.path.isfile(ele_full_path):
                    base_name, file_ext = os.path.splitext(element)
                    if not file_ext == ".exe":
                        os.remove(ele_full_path)
                elif os.path.isdir(ele_full_path):
                    shutil.rmtree(ele_full_path)

        # create output dir if it not existed
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # copy dll & exe
        files = os.listdir(build_folder_path)
        for filename in files:
            name, ext = os.path.splitext(filename)
            proj_exe_name = "%s.exe" % self.project_name
            if ext == '.dll' or filename == proj_exe_name:
                file_path = os.path.join(build_folder_path, filename)
                cocos.Logging.info("Copying %s" % filename)
                shutil.copy(file_path, output_dir)

        # copy lua files & res
        build_cfg_path = self._build_cfg_path()
        build_cfg = os.path.join(build_cfg_path, CCPluginCompile.BUILD_CONFIG_FILE)
        if not os.path.exists(build_cfg):
            message = "%s not found" % build_cfg
            raise cocos.CCPluginError(message)
        f = open(build_cfg)
        data = json.load(f)

        if data.has_key(CCPluginCompile.CFG_KEY_MUST_COPY_RESOURCES):
            if self._no_res:
                fileList = data[CCPluginCompile.CFG_KEY_MUST_COPY_RESOURCES]
            else:
                fileList = data[CCPluginCompile.CFG_KEY_COPY_RESOURCES] + data[CCPluginCompile.CFG_KEY_MUST_COPY_RESOURCES]
        else:
            fileList = data[CCPluginCompile.CFG_KEY_COPY_RESOURCES]

        for cfg in fileList:
            copy_files_with_config(cfg, build_cfg_path, output_dir)
        
        self.run_root = output_dir

    def build_web(self):
        if not self._platforms.is_web_active():
            return

        project_dir = self._platforms.project_path()

        # store env for run
        cfg_obj = self._platforms.get_current_config()
        if cfg_obj.run_root_dir is not None:
            self.run_root = cfg_obj.run_root_dir
        else:
            self.run_root = project_dir

        if cfg_obj.sub_url is not None:
            self.sub_url = cfg_obj.sub_url
        else:
            self.sub_url = '/'

        if self._is_debug_mode():
            return
        else:
            self.sub_url = '%spublish/html5/' % self.sub_url

        f = open(os.path.join(project_dir, "project.json"))
        project_json = json.load(f)
        f.close()
        engine_dir = os.path.join(project_json["engineDir"])
        realEngineDir = os.path.normpath(os.path.join(project_dir, engine_dir))
        publish_dir = os.path.normpath(os.path.join(project_dir, "publish", "html5"))

        # need to config in options of command
        buildOpt = {
                "outputFileName" : "game.min.js",
                #"compilationLevel" : "simple",
                "compilationLevel" : "advanced",
                "sourceMapOpened" : True if self._has_sourcemap else False
                }

        if os.path.exists(publish_dir) == False:
            os.makedirs(publish_dir)

        # generate build.xml
        build_web.gen_buildxml(project_dir, project_json, publish_dir, buildOpt)

        outputJsPath = os.path.join(publish_dir, buildOpt["outputFileName"])
        if os.path.exists(outputJsPath) == True:
            os.remove(outputJsPath)


        # call closure compiler
        ant_root = cocos.check_environment_variable('ANT_ROOT')
        ant_path = os.path.join(ant_root, 'ant')
        self._run_cmd("%s -f %s" % (ant_path, os.path.join(publish_dir, 'build.xml')))

        # handle sourceMap
        sourceMapPath = os.path.join(publish_dir, "sourcemap")
        if os.path.exists(sourceMapPath):
            smFile = open(sourceMapPath)
            try:
                smContent = smFile.read()
            finally:
                smFile.close()

            dir_to_replace = project_dir
            if cocos.os_is_win32():
                dir_to_replace = project_dir.replace('\\', '\\\\')
            smContent = smContent.replace(dir_to_replace, os.path.relpath(project_dir, publish_dir))
            smContent = smContent.replace(realEngineDir, os.path.relpath(realEngineDir, publish_dir))
            smContent = smContent.replace('\\\\', '/')
            smContent = smContent.replace('\\', '/')
            smFile = open(sourceMapPath, "w")
            smFile.write(smContent)
            smFile.close()

        # handle project.json
        del project_json["engineDir"]
        del project_json["modules"]
        del project_json["jsList"]
        project_json_output_file = open(os.path.join(publish_dir, "project.json"), "w")
        project_json_output_file.write(json.dumps(project_json))
        project_json_output_file.close()

        # handle index.html
        indexHtmlFile = open(os.path.join(project_dir, "index.html"))
        try:
            indexContent = indexHtmlFile.read()
        finally:
            indexHtmlFile.close()
        reg1 = re.compile(r'<script\s+src\s*=\s*("|\')[^"\']*CCBoot\.js("|\')\s*><\/script>')
        indexContent = reg1.sub("", indexContent)
        mainJs = project_json.get("main") or "main.js"
        indexContent = indexContent.replace(mainJs, buildOpt["outputFileName"])
        indexHtmlOutputFile = open(os.path.join(publish_dir, "index.html"), "w")
        indexHtmlOutputFile.write(indexContent)
        indexHtmlOutputFile.close()
        
        # copy res dir
        dst_dir = os.path.join(publish_dir, 'res')
        src_dir = os.path.join(project_dir, 'res')
        if os.path.exists(dst_dir):
            shutil.rmtree(dst_dir)
        shutil.copytree(src_dir, dst_dir)



    def build_linux(self):
        if not self._platforms.is_linux_active():
            return

        #if not cocos.os_is_linux():
        #    raise cocos.CCPluginError("Please build on linux")

        project_dir = self._project.get_project_dir()
        cfg_obj = self._platforms.get_current_config()
        if cfg_obj.cmake_path is not None:
            cmakefile_dir = os.path.join(project_dir, cfg_obj.cmake_path)
        else:
            cmakefile_dir = project_dir
            if self._project._is_lua_project():
                cmakefile_dir = os.path.join(project_dir, 'frameworks')

        # get the project name
        if cfg_obj.project_name is not None:
            self.project_name = cfg_obj.project_name
        else:
            f = open(os.path.join(cmakefile_dir, 'CMakeLists.txt'), 'r')
            for line in f.readlines():
                if "set(APP_NAME " in line:
                    self.project_name = re.search('APP_NAME ([^\)]+)\)', line).group(1)
                    break

        if cfg_obj.build_dir is not None:
            build_dir = os.path.join(project_dir, cfg_obj.build_dir)
        else:
            build_dir = os.path.join(project_dir, 'linux-build')

        if not os.path.exists(build_dir):
            os.makedirs(build_dir)

        with cocos.pushd(build_dir):
            self._run_cmd('cmake %s' % os.path.relpath(cmakefile_dir, build_dir))

        with cocos.pushd(build_dir):
            self._run_cmd('make -j%s' % self._jobs)

        # move file
        build_mode = self._mode
        if self._project._is_script_project():
            if build_mode == 'debug':
                output_dir = os.path.join(project_dir, CCPluginCompile.OUTPUT_DIR_SCRIPT_DEBUG, 'linux')
            else:
                output_dir = os.path.join(project_dir, CCPluginCompile.OUTPUT_DIR_SCRIPT_RELEASE, 'linux')
        else:
            output_dir = os.path.join(project_dir, CCPluginCompile.OUTPUT_DIR_NATIVE, build_mode, 'linux')

        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(output_dir)

        if cfg_obj.build_result_dir is not None:
            result_dir = os.path.join(build_dir, 'bin', cfg_obj.build_result_dir)
        else:
            result_dir = os.path.join(build_dir, 'bin')
        copy_files_in_dir(result_dir, output_dir)

        self.run_root = output_dir

        if self._no_res:
            res_dir = os.path.join(output_dir, "Resources")
            self._remove_res(res_dir)

        cocos.Logging.info('Build successed!')

    def checkFileByExtention(self, ext, path):
        filelist = os.listdir(path)
        for fullname in filelist:
            name, extention = os.path.splitext(fullname)
            if extention == ext:
                return name, fullname
        return (None, None)


    def run(self, argv, dependencies):
        self.parse_args(argv)
        cocos.Logging.info('Building mode: %s' % self._mode)
        self._update_build_cfg()
        self.build_android()
        self.build_ios()
        self.build_mac()
        self.build_win32()
        self.build_web()
        self.build_linux()
