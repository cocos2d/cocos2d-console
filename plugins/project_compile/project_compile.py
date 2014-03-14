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
            os.makedirs(new_dst)
            copy_files_in_dir(path, new_dst)

def copy_dir_into_dir(src, dst):
    normpath = os.path.normpath(src)
    dir_to_create = normpath[normpath.rfind(os.sep)+1:]
    dst_path = os.path.join(dst, dir_to_create)
    if os.path.isdir(dst_path):
        shutil.rmtree(dst_path)
    shutil.copytree(src, dst_path, True)


class CCPluginCompile(cocos.CCPlugin):
    """
    compiles a project
    """

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

    def _is_debug_mode(self):
        return self._mode == 'debug'


    def build_android(self):
        if not self._platforms.is_android_active():
            return

        project_dir = self._project.get_project_dir()
        build_mode = self._mode
        if self._project._is_script_project():
            output_dir = os.path.join(project_dir, 'runtime', 'android')
            if self._project._is_lua_project():
                cocos_root = os.path.join(project_dir, 'frameworks' ,'cocos2d-x')
            else:
                cocos_root = os.path.join(project_dir, 'frameworks' ,'%s-bindings' % self._project.get_language(), 'cocos2d-x')

        else:
            cocos_root = os.path.join(project_dir, 'cocos2d')
            output_dir = os.path.join(project_dir, 'bin', build_mode, 'android')

        # check ant path
        ant_root = cocos.check_environment_variable('ANT_ROOT')
        ndk_root = cocos.check_environment_variable('NDK_ROOT')
        project_android_dir = self._platforms.project_path()

        from build_android import AndroidBuilder
        builder = AndroidBuilder(self._verbose, cocos_root, project_android_dir)

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

        name, xcodeproj_name = self.checkFileByExtention(".xcodeproj", self._platforms.project_path())
        if not xcodeproj_name:
            message = "Can't find the \".xcodeproj\" file"
            raise cocos.CCPluginError(message)

        self.project_name = name
        self.xcodeproj_name = xcodeproj_name


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
            output_dir = os.path.join(project_dir, 'runtime', 'ios')
        else:
            output_dir = os.path.join(project_dir, 'bin', build_mode, 'ios')

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
            if extention == '.app':
                filename = os.path.join(output_dir, filename)
                newname = os.path.join(output_dir, name[:name.find(' ')]+extention)
                os.rename(filename, newname)
                self._iosapp_path = newname
        
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
            output_dir = os.path.join(project_dir, 'runtime', 'mac')
        else:
            output_dir = os.path.join(project_dir, 'bin', build_mode, 'mac')


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
        names = re.split("\*", targets.group())
        for name in names:
            if "Mac" in name:
                targetName = str.strip(name)

        if targetName is None:
            message = "Can't find Mac target"
            raise cocos.CCPluginError(message)

        if os.path.isdir(output_dir):
            filelist = os.listdir(output_dir)
            for filename in filelist:
                if ".app" in filename:
                    f = os.path.join(output_dir, filename)
                    shutil.rmtree(f)

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
            if extention == '.app':
                filename = os.path.join(output_dir, filename)
                if ' ' in name:
                    filename = os.path.join(output_dir, filename)
                    newname = os.path.join(output_dir, name[:name.find(' ')]+extention)
                    os.rename(filename, newname)
                    self._macapp_path = newname

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
            output_dir = os.path.join(project_dir, 'runtime', 'win32')
        else:
            output_dir = os.path.join(project_dir, 'bin', build_mode, 'win32')

        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

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
            "/t:build",
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

        # copy dll & exe
        files = os.listdir(build_folder_path)
        for filename in files:
            name, ext = os.path.splitext(filename)
            if ext == '.dll' or ext == '.exe':
                file_path = os.path.join(build_folder_path, filename)
                cocos.Logging.info("Copying %s" % filename)
                shutil.copy(file_path, output_dir)

        # copy lua files & res
        build_cfg = os.path.join(win32_projectdir, 'build-cfg.json')
        if not os.path.exists(build_cfg):
            message = "%s not found" % build_cfg
            raise cocos.CCPluginError(message)
        f = open(build_cfg)
        data = json.load(f)
        fileList = data["copy_files"]
        for res in fileList:
           resource = os.path.join(win32_projectdir, res)
           if os.path.isdir(resource):
               if res.endswith('/'):
                   copy_files_in_dir(resource, output_dir)
               else:
                   copy_dir_into_dir(resource, output_dir)
           elif os.path.isfile(resource):
               shutil.copy(resource, output_dir)
        
        self.run_root = output_dir

    def build_web(self):
        if not self._platforms.is_web_active():
            return

        if self._is_debug_mode():
            return

        project_dir = self._project.get_project_dir()

        f = open(os.path.join(project_dir, "project.json"))
        project_json = json.load(f)
        f.close()
        engine_dir = os.path.join(project_json["engineDir"])
        realEngineDir = os.path.normpath(os.path.join(project_dir, engine_dir))
        publish_dir = os.path.normpath(os.path.join(project_dir, "publish/html5"))

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
        self._run_cmd("ant -f %s" % os.path.join(publish_dir, 'build.xml'))

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

        # store env for run
        self.run_root = project_dir
        if self._is_debug_mode():
            self.sub_url = '/'
        else:
            self.sub_url = '/publish/html5'


    def build_linux(self):
        if not self._platforms.is_linux_active():
            return

        #if not cocos.os_is_linux():
        #    raise cocos.CCPluginError("Please build on linux")

        project_dir = self._project.get_project_dir()
        cmakefile_dir = project_dir
        if self._project._is_lua_project():
            cmakefile_dir = os.path.join(project_dir, 'frameworks')

        # get the project name
        f = open(os.path.join(cmakefile_dir, 'CMakeLists.txt'), 'r')
        for line in f.readlines():
            if "set(APP_NAME " in line:
                self.project_name = re.search('APP_NAME ([^\)]+)\)', line).group(1)
                break
        
        build_dir = os.path.join(project_dir, 'build')
        if not os.path.exists(build_dir):
            os.makedirs(build_dir)

        with cocos.pushd(build_dir):
            self._run_cmd('cmake %s' % os.path.relpath(cmakefile_dir, build_dir))

        with cocos.pushd(build_dir):
            self._run_cmd('make')

        # move file
        build_mode = self._mode
        if self._project._is_script_project():
            output_dir = os.path.join(project_dir, 'runtime', 'linux')
        else:
            output_dir = os.path.join(project_dir, 'bin', build_mode, 'linux')

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
       
        copy_files_in_dir(os.path.join(build_dir, 'bin'), output_dir)

        self.run_root = output_dir

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
        self.build_android()
        self.build_ios()
        self.build_mac()
        self.build_win32()
        self.build_web()
        self.build_linux()
