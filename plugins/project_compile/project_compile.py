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

class CCPluginCompile(cocos.CCPlugin):
    """
    compiles a project
    """
    @staticmethod
    def plugin_category():
      return "project"

    @staticmethod
    def plugin_name():
      return "compile"

    @staticmethod
    def brief_description():
        return "compiles the current project to binary"

    def _add_custom_options(self, parser):
        from optparse import OptionGroup
        parser.add_option("-m", "--mode", dest="mode", default='debug',
                          help="Set the compile mode, should be debug|release, default is debug.")
        parser.add_option("-j", "--jobs", dest="jobs", type='int', default=1,
                          help="Allow N jobs at once.")

        group = OptionGroup(parser, "Android Options")
        group.add_option("--ap", dest="android_platform", type='int', help='parameter for android-update.Without the parameter,the script just build dynamic library for project. Valid android-platform are:[10|11|12|13|14|15|16|17|18|19]')  
        parser.add_option_group(group)

        category = self.plugin_category()
        name = self.plugin_name()
        usage = "\n\t%%prog %s %s -p <platform> [-s src_dir][-m <debug|release>]" \
                "\nSample:" \
                "\n\t%%prog %s %s -p android" % (category, name, category, name)

        parser.set_usage(usage)

    def _check_custom_options(self, options):

        if options.mode != 'release':
            options.mode = 'debug'

        self._mode = 'debug'
        if 'release' == options.mode:
            self._mode = options.mode

        cocos.Logging.info('Building mode: %s' % self._mode)

        self._ap = options.android_platform
        self._jobs = options.jobs


    def build_android(self):
        if not self._platforms.is_android_active():
            return

        project_dir = self._src_dir
        build_mode = self._mode
        if self._is_script_project():
            cocos_root = os.path.join(project_dir, 'frameworks' ,'%s-bindings' % self._project_lang, 'cocos2d-x')
            output_dir = os.path.join(project_dir, 'runtime', 'android')
        else: 
            cocos_root = os.path.join(project_dir, 'cocos2d')
            output_dir = os.path.join(project_dir, 'bin', build_mode, 'android')

        # check ant path
        ant_root = cocos.check_environment_variable('ANT_PATH')
        ndk_root = cocos.check_environment_variable('NDK_ROOT')
        project_android_dir = self._platforms.project_path()

        from build_android import AndroidBuilder
        builder = AndroidBuilder(cocos_root, project_android_dir)
        
        # build native code
        cocos.Logging.info("building native")
        ndk_build_param = "-j%s" % self._jobs
        builder.do_ndk_build(ndk_root, ndk_build_param)
		
        # build apk
        cocos.Logging.info("building apk")
        if not self._ap:
            cocos.Logging.info('Android platform not specified, searching a default one...')
            self._ap = cocos.select_default_android_platform()
            if self._ap is None:
                 cocos.Logging.warning('No valid android platform found, will not generate apk.')

        android_platform = self._ap
        if android_platform:
            android_platform = 'android-' + str(android_platform)
            sdk_root = cocos.check_environment_variable('ANDROID_SDK_ROOT')
            builder.do_build_apk(sdk_root, ant_root, android_platform, build_mode, output_dir)

        cocos.Logging.info("build succeeded.")

        
    def build_ios(self):
        if not self._platforms.is_ios_active():
            return

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

        res = self.checkFileByExtention(".xcodeproj")
        if not res:
            message = "Can't find the \".xcodeproj\" file"
            raise cocos.CCPluginError(message)


        project_dir = self._src_dir
        ios_project_dir = self._platforms.project_path()
        build_mode = self._mode
        if self._is_script_project():
            cocos_root = os.path.join(project_dir, 'frameworks' ,'%s-bindings' % self._project_lang, 'cocos2d-x')
            output_dir = os.path.join(project_dir, 'runtime', 'ios')
        else: 
            cocos_root = os.path.join(project_dir, 'cocos2d')
            output_dir = os.path.join(project_dir, 'bin', build_mode, 'ios')

        projectPath = os.path.join(ios_project_dir, self.project_name)
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
        names = re.split("\*", targets.group())
        for name in names:
            if "iOS" in name:
                targetName = str.strip(name)

        if targetName is None:
            message = "Can't find iOS target"
            raise cocos.CCPluginError(message)

        if os.path.isdir(output_dir):
            filelist = os.listdir(output_dir)
            for filename in filelist:
                if ".app" in filename:
                    f = os.path.join(output_dir, filename)
                    shutil.rmtree(f)

        cocos.Logging.info("building")

        commands = [
            "xcodebuild",
            "-project",
            projectPath,
            "-configuration",
            "Debug",
            "-target",
            targetName, 
            "-sdk",
            "iphonesimulator",
            "CONFIGURATION_BUILD_DIR=%s" % (output_dir)
        ]

        self._run_cmd(commands)

        filelist = os.listdir(output_dir)

        for filename in filelist:
            name, extention = os.path.splitext(filename)
            if extention == '.a':
                filename = os.path.join(output_dir, filename)
                os.remove(filename)
            if extention == '.app':
                filename = os.path.join(output_dir, filename)
                newname = os.path.join(output_dir, name[:name.find(' ')]+extention)
                os.rename(filename, newname)

        cocos.Logging.info("build succeeded.")
    pass

    def build_mac(self):
        if not self._platforms.is_mac_active():
            return

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

        res = self.checkFileByExtention(".xcodeproj")
        if not res:
            message = "Can't find the \".xcodeproj\" file"
            raise cocos.CCPluginError(message)

        project_dir = self._src_dir
        mac_project_dir = self._platforms.project_path()
        build_mode = self._mode
        if self._is_script_project():
            cocos_root = os.path.join(project_dir, 'frameworks' ,'%s-bindings' % self._project_lang, 'cocos2d-x')
            output_dir = os.path.join(project_dir, 'runtime', 'mac')
        else: 
            cocos_root = os.path.join(project_dir, 'cocos2d')
            output_dir = os.path.join(project_dir, 'bin', build_mode, 'mac')


        projectPath = os.path.join(mac_project_dir, self.project_name)
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
        names = re.split("\*", targets.group())
        for name in names:
            if "Mac" in name:
                targetName = str.strip(name)

        if targetName is None:
            message = "Can't find Mac target"
            raise cocos.CCPluginError(message)

        if os.path.isdir(output_dir):
            shutil.rmtree(output_dir)

        cocos.Logging.info("building")

        commands = [
            "xcodebuild",
            "-project",
            projectPath,
            "-configuration",
            "Debug",
            "-target",
            targetName,
            "CONFIGURATION_BUILD_DIR=%s" % (output_dir)
        ]

        self._run_cmd(commands)

        filelist = os.listdir(output_dir)
        for filename in filelist:
            name, extention = os.path.splitext(filename)
            if extention == '.a':
                filename = os.path.join(output_dir, filename)
                os.remove(filename)
            if extention == '.app':
                filename = os.path.join(output_dir, filename)
                if ' ' in name:
                    newname = os.path.join(output_dir, name[:name.find(' ')]+extention)
                    os.rename(filename, newname)

        cocos.Logging.info("build succeeded.")
    pass

    def build_win32(self):
        if not self._platforms.is_ios_active():
            return
        project_dir = self._platforms.project_path()
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

        res = self.checkFileByExtention(".sln")
        if not res:
            message = "Can't find the \".sln\" file"
            raise cocos.CCPluginError(message)

        msbuildPath = os.path.join(msbuildPath, "MSBuild.exe")
        projectPath = os.path.join(project_dir, self.project_name)
        commands = [
            msbuildPath,
            projectPath,
            "/maxcpucount:4",
            "/t:build",
            "/p:configuration=Debug"
        ]

        self._run_cmd(commands)

        cocos.Logging.info("build succeeded.")
        return True
        

    def checkFileByExtention(self, ext, path=None):
        filelist = ""
        if path is None:
            filelist = os.listdir(self._platforms.project_path())
        else:
            filelist = os.listdir(path)

        for file in filelist:
            name, extention = os.path.splitext(file)
            if extention == ext:
                self.project_name = file
                return True
        raise cocos.CCPluginError(message)


    def run(self, argv, dependencies):
        self.parse_args(argv)
        self.build_android()
        self.build_ios()
        self.build_mac()
