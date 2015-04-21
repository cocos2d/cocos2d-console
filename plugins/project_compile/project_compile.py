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

import multiprocessing
import cocos
import cocos_project
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
    WEB_PLATFORM_FOLDER_NAME = "html5"

    PROJ_CFG_KEY_IOS_SIGN_ID = "ios_sign_id"
    PROJ_CFG_KEY_ENGINE_DIR = "engine_dir"

    BACKUP_SUFFIX = "-backup"
    ENGINE_JS_DIRS = [
        "frameworks/js-bindings/bindings/script",
        "cocos/scripting/js-bindings/script"
    ]

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
        parser.add_argument("-j", "--jobs", dest="jobs", type=int,
                          help="Allow N jobs at once.")
        parser.add_argument("-o", "--output-dir", dest="output_dir", help="Specify the output directory.")

        group = parser.add_argument_group("Android Options")
        group.add_argument("--ap", dest="android_platform", help='Specify the android platform used for building android apk.')
        group.add_argument("--ndk-mode", dest="ndk_mode", help='Set the compile mode of ndk-build, should be debug|release|none, native code will not be compiled when the value is none. Default is same value with -m')
        group.add_argument("--app-abi", dest="app_abi", help='Set the APP_ABI of ndk-build. Can be multi value separated with ":".Sample : --app-aib armeabi:x86:mips. Default value is "armeabi".')
        group.add_argument("--ndk-toolchain", dest="toolchain", help='Specify the NDK_TOOLCHAIN of ndk-build.')
        group.add_argument("--ndk-cppflags", dest="cppflags", help='Specify the APP_CPPFLAGS of ndk-build.')

        group = parser.add_argument_group("Web Options")
        group.add_argument("--source-map", dest="source_map", action="store_true", help='Enable source-map')
        group.add_argument("--advanced", dest="advanced", action="store_true", help="Compile all source js files using Closure Compiler's advanced mode, bigger compression ratio bug more risk")

        group = parser.add_argument_group("iOS/Mac Options")
        group.add_argument("-t", "--target", dest="target_name", help="Specify the target name to compile.")

        group = parser.add_argument_group("iOS Options")
        group.add_argument("--sign-identity", dest="sign_id", help="The code sign identity for iOS.")

        group = parser.add_argument_group("lua/js project arguments")
        group.add_argument("--no-res", dest="no_res", action="store_true", help="Package without project resources.")
        group.add_argument("--compile-script", dest="compile_script", type=int, choices=[0, 1], help="Diable/Enable the compiling of lua/js script files.")

        group = parser.add_argument_group("lua project arguments")
        group.add_argument("--lua-encrypt", dest="lua_encrypt", action="store_true", help="Enable the encrypting of lua scripts.")
        group.add_argument("--lua-encrypt-key", dest="lua_encrypt_key", help="Specify the encrypt key for the encrypting of lua scripts.")
        group.add_argument("--lua-encrypt-sign", dest="lua_encrypt_sign", help="Specify the encrypt sign for the encrypting of lua scripts.")

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

        # android arguments
        if args.ndk_mode is not None:
            self._ndk_mode = args.ndk_mode
        else:
            self._ndk_mode = self._mode

        self.app_abi = None
        if args.app_abi:
            self.app_abi = " ".join(args.app_abi.split(":"))

        self.cppflags = None
        if args.cppflags:
            self.cppflags = args.cppflags

        self.ndk_toolchain = None
        if args.toolchain:
            self.ndk_toolchain = args.toolchain

        # iOS/Mac arguments
        self.xcode_target_name = None
        if args.target_name is not None:
            self.xcode_target_name = args.target_name

        if args.compile_script is not None:
            self._compile_script = bool(args.compile_script)
        else:
            self._compile_script = (self._mode == "release")

        self._ap = args.android_platform

        if args.jobs is not None:
            self._jobs = args.jobs
        else:
            self._jobs = self.get_num_of_cpu()
        self._has_sourcemap = args.source_map
        self._web_advanced = args.advanced
        self._no_res = args.no_res

        if args.output_dir is None:
            self._output_dir = self._get_output_dir()
        else:
            if os.path.isabs(args.output_dir):
                self._output_dir = args.output_dir
            else:
                self._output_dir = os.path.abspath(args.output_dir)

        self._sign_id = args.sign_id

        if self._project._is_lua_project():
            self._lua_encrypt = args.lua_encrypt
            self._lua_encrypt_key = args.lua_encrypt_key
            self._lua_encrypt_sign = args.lua_encrypt_sign

        self.end_warning = ""
        self._gen_custom_step_args()

    def get_num_of_cpu(self):
        try:
            return multiprocessing.cpu_count()
        except Exception:
            print "Failed to detect number of cpus, assume 1 cpu"
            return 1

    def _get_output_dir(self):
        project_dir = self._project.get_project_dir()
        cur_platform = self._platforms.get_current_platform()
        if self._project._is_script_project():
            if self._project._is_js_project() and self._platforms.is_web_active():
                cur_platform = CCPluginCompile.WEB_PLATFORM_FOLDER_NAME

            if self._mode == 'debug':
                output_dir = os.path.join(project_dir, CCPluginCompile.OUTPUT_DIR_SCRIPT_DEBUG, cur_platform)
            else:
                output_dir = os.path.join(project_dir, CCPluginCompile.OUTPUT_DIR_SCRIPT_RELEASE, cur_platform)
        else:
            output_dir = os.path.join(project_dir, CCPluginCompile.OUTPUT_DIR_NATIVE, self._mode, cur_platform)

        return output_dir

    def _gen_custom_step_args(self):
        self._custom_step_args = {
            "project-path": self._project.get_project_dir(),
            "platform-project-path": self._platforms.project_path(),
            "build-mode": self._mode,
            "output-dir": self._output_dir
        }

        if self._platforms.is_android_active():
            self._custom_step_args["ndk-build-mode"] = self._ndk_mode

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

    def _remove_file_with_ext(self, work_dir, ext):
        file_list = os.listdir(work_dir)
        for f in file_list:
            full_path = os.path.join(work_dir, f)
            if os.path.isdir(full_path):
                self._remove_file_with_ext(full_path, ext)
            elif os.path.isfile(full_path):
                name, cur_ext = os.path.splitext(f)
                if cur_ext == ext:
                    os.remove(full_path)

    def compile_lua_scripts(self, src_dir, dst_dir, need_compile=None):
        if not self._project._is_lua_project():
            return

        if need_compile is None:
            need_compile = self._compile_script

        if not need_compile and not self._lua_encrypt:
            return

        cocos_cmd_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "cocos")
        rm_ext = ".lua"
        compile_cmd = "\"%s\" luacompile -s \"%s\" -d \"%s\"" % (cocos_cmd_path, src_dir, dst_dir)

        if not need_compile:
            compile_cmd = "%s --disable-compile" % compile_cmd

        if self._lua_encrypt:
            add_para = ""
            if self._lua_encrypt_key is not None:
                add_para = "%s -k %s" % (add_para, self._lua_encrypt_key)

            if self._lua_encrypt_sign is not None:
                add_para = "%s -b %s" % (add_para, self._lua_encrypt_sign)

            compile_cmd = "%s -e %s" % (compile_cmd, add_para)

        # run compile command
        self._run_cmd(compile_cmd)

        # remove the source scripts
        self._remove_file_with_ext(dst_dir, rm_ext)

    def compile_js_scripts(self, src_dir, dst_dir):
        if not self._project._is_js_project():
            return

        if not self._compile_script:
            return

        cocos_cmd_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "cocos")
        rm_ext = ".js"
        compile_cmd = "\"%s\" jscompile -s \"%s\" -d \"%s\"" % (cocos_cmd_path, src_dir, dst_dir)

        # run compile command
        self._run_cmd(compile_cmd)

        # remove the source scripts
        self._remove_file_with_ext(dst_dir, rm_ext)

    def add_warning_at_end(self, warning_str):
        if warning_str is None or len(warning_str) == 0:
            return
        self.end_warning = "%s\n%s" % (self.end_warning, warning_str)

    def build_android(self):
        if not self._platforms.is_android_active():
            return

        project_dir = self._project.get_project_dir()
        project_android_dir = self._platforms.project_path()
        build_mode = self._mode
        output_dir = self._output_dir

        # check environment variable
        ant_root = cocos.check_environment_variable('ANT_ROOT')
        sdk_root = cocos.check_environment_variable('ANDROID_SDK_ROOT')

        from build_android import AndroidBuilder
        builder = AndroidBuilder(self._verbose, project_android_dir, self._no_res, self._project)

        args_ndk_copy = self._custom_step_args.copy()
        target_platform = self._platforms.get_current_platform()

        # update the project with the android platform
        builder.update_project(sdk_root, self._ap)

        if not self._project._is_script_project() or self._project._is_native_support():
            if self._ndk_mode != "none":
                # build native code
                cocos.Logging.info("building native")
                ndk_build_param = [
                    "-j%s" % self._jobs
                ]

                if self.app_abi:
                    abi_param = "APP_ABI=\"%s\"" % self.app_abi
                    ndk_build_param.append(abi_param)

                if self.ndk_toolchain:
                    toolchain_param = "NDK_TOOLCHAIN=%s" % self.ndk_toolchain
                    ndk_build_param.append(toolchain_param)

                self._project.invoke_custom_step_script(cocos_project.Project.CUSTOM_STEP_PRE_NDK_BUILD, target_platform, args_ndk_copy)

                modify_mk = False
                app_mk = os.path.join(project_android_dir, "jni/Application.mk")
                mk_content = None
                if self.cppflags and os.path.exists(app_mk):
                    # record the content of Application.mk
                    f = open(app_mk)
                    mk_content = f.read()
                    f.close()

                    # Add cpp flags
                    f = open(app_mk, "a")
                    f.write("\nAPP_CPPFLAGS += %s" % self.cppflags)
                    f.close()
                    modify_mk = True

                try:
                    builder.do_ndk_build(ndk_build_param, self._ndk_mode, self)
                except:
                    raise cocos.CCPluginError("Ndk build failed!")
                finally:
                    # roll-back the Application.mk
                    if modify_mk:
                        f = open(app_mk, "w")
                        f.write(mk_content)
                        f.close()

                self._project.invoke_custom_step_script(cocos_project.Project.CUSTOM_STEP_POST_NDK_BUILD, target_platform, args_ndk_copy)

        # build apk
        cocos.Logging.info("building apk")
        self.apk_path = builder.do_build_apk(sdk_root, ant_root, build_mode, output_dir, self._custom_step_args, self)

        cocos.Logging.info("build succeeded.")

    def check_ios_mac_build_depends(self):
        version = cocos.get_xcode_version()

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

    def get_engine_dir(self):
        engine_dir = self._project.get_proj_config(CCPluginCompile.PROJ_CFG_KEY_ENGINE_DIR)
        if engine_dir is None:
            proj_dir = self._project.get_project_dir()
            if self._project._is_js_project():
                check_dir = os.path.join(proj_dir, "frameworks", "cocos2d-x")
                if os.path.isdir(check_dir):
                    # the case for jsb in cocos2d-x engine
                    engine_dir = check_dir
                else:
                    # the case for jsb in cocos2d-js engine
                    engine_dir = proj_dir
            elif self._project._is_lua_project():
                engine_dir = os.path.join(proj_dir, "frameworks", "cocos2d-x")
            else:
                engine_dir = os.path.join(proj_dir, "cocos2d")
        else:
            engine_dir = os.path.join(self._project.get_project_dir(), engine_dir)

        return engine_dir

    def backup_dir(self, dir_path):
        backup_dir = "%s%s" % (dir_path, CCPluginCompile.BACKUP_SUFFIX)
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)
        shutil.copytree(dir_path, backup_dir)

    def reset_backup_dir(self, dir_path):
        backup_dir = "%s%s" % (dir_path, CCPluginCompile.BACKUP_SUFFIX)
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
        os.rename(backup_dir, dir_path)

    def get_engine_js_dir(self):
        engine_js_dir = None
        isFound = False

        check_script_dir = os.path.join(self._project.get_project_dir(), "script")
        if os.path.isdir(check_script_dir):
            # JS script already copied into the project dir
            engine_js_dir = check_script_dir
            isFound = True
        else:
            for js_dir in CCPluginCompile.ENGINE_JS_DIRS:
                engine_js_dir = os.path.join(self.get_engine_dir(), js_dir)
                if os.path.isdir(engine_js_dir):
                    isFound = True
                    break

        if isFound:
            return engine_js_dir
        else:
            return None

    def build_ios(self):
        if not self._platforms.is_ios_active():
            return

        if not cocos.os_is_mac():
            raise cocos.CCPluginError("Please build on MacOSX")

        if self._sign_id is not None:
            cocos.Logging.info("Code Sign Identity: %s" % self._sign_id)
            self.use_sdk = 'iphoneos'
        else:
            self.use_sdk = 'iphonesimulator'

        self.check_ios_mac_build_depends()

        ios_project_dir = self._platforms.project_path()
        output_dir = self._output_dir

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
        if self.xcode_target_name is not None:
            targetName = self.xcode_target_name
        else:
            cfg_obj = self._platforms.get_current_config()
            if cfg_obj.target_name is not None:
                targetName = cfg_obj.target_name
            else:
                names = re.split("\*", targets.group())
                for name in names:
                    if "iOS" in name:
                        targetName = str.strip(name)
                        break

        if targetName is None:
            message = "Can't find iOS target"
            raise cocos.CCPluginError(message)

        if os.path.isdir(output_dir):
            target_app_dir = os.path.join(output_dir, "%s.app" % targetName)
            if os.path.isdir(target_app_dir):
                shutil.rmtree(target_app_dir)

        # is script project, check whether compile scripts or not
        need_reset_dir = False
        if self._project._is_script_project():
            script_src_dir = os.path.join(self._project.get_project_dir(), "src")

            if self._project._is_js_project() and self._compile_script:
                # backup the source scripts
                self.backup_dir(script_src_dir)
                self.compile_js_scripts(script_src_dir, script_src_dir)

                # js project need compile the js files in engine
                engine_js_dir = self.get_engine_js_dir()
                if engine_js_dir is not None:
                    self.backup_dir(engine_js_dir)
                    self.compile_js_scripts(engine_js_dir, engine_js_dir)
                need_reset_dir = True

            if self._project._is_lua_project() and self._lua_encrypt:
                # on iOS, only invoke luacompile when lua encrypt is specified
                self.backup_dir(script_src_dir)
                self.compile_lua_scripts(script_src_dir, script_src_dir, False)
                need_reset_dir = True

        try:
            cocos.Logging.info("building")

            command = ' '.join([
                "xcodebuild",
                "-project",
                "\"%s\"" % projectPath,
                "-configuration",
                "%s" % 'Debug' if self._mode == 'debug' else 'Release',
                "-target",
                "\"%s\"" % targetName,
                "%s" % "-arch i386" if self.use_sdk == 'iphonesimulator' else '',
                "-sdk",
                "%s" % self.use_sdk,
                "CONFIGURATION_BUILD_DIR=\"%s\"" % (output_dir),
                "%s" % "VALID_ARCHS=\"i386\"" if self.use_sdk == 'iphonesimulator' else ''
                ])

            if self._sign_id is not None:
                command = "%s CODE_SIGN_IDENTITY=\"%s\"" % (command, self._sign_id)

            self._run_cmd(command)

            filelist = os.listdir(output_dir)

            for filename in filelist:
                name, extention = os.path.splitext(filename)
                if extention == '.a':
                    filename = os.path.join(output_dir, filename)
                    os.remove(filename)

            self._iosapp_path = os.path.join(output_dir, "%s.app" % targetName)
            if self._no_res:
                self._remove_res(self._iosapp_path)

            if self._sign_id is not None:
                # generate the ipa
                app_path = os.path.join(output_dir, "%s.app" % targetName)
                ipa_path = os.path.join(output_dir, "%s.ipa" % targetName)
                ipa_cmd = "xcrun -sdk %s PackageApplication -v \"%s\" -o \"%s\"" % (self.use_sdk, app_path, ipa_path)
                self._run_cmd(ipa_cmd)

            cocos.Logging.info("build succeeded.")
        except:
            raise cocos.CCPluginError("Build failed: Take a look at the output above for details.")
        finally:
            # is script project & need reset dirs
            if need_reset_dir:
                script_src_dir = os.path.join(self._project.get_project_dir(), "src")
                self.reset_backup_dir(script_src_dir)

                if self._project._is_js_project():
                    engine_js_dir = self.get_engine_js_dir()
                    if engine_js_dir is not None:
                        self.reset_backup_dir(engine_js_dir)

    def build_mac(self):
        if not self._platforms.is_mac_active():
            return

        if not cocos.os_is_mac():
            raise cocos.CCPluginError("Please build on MacOSX")

        self.check_ios_mac_build_depends()

        mac_project_dir = self._platforms.project_path()
        output_dir = self._output_dir

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
        if self.xcode_target_name is not None:
            targetName = self.xcode_target_name
        else:
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
            target_app_dir = os.path.join(output_dir, "%s.app" % targetName)
            if os.path.isdir(target_app_dir):
                shutil.rmtree(target_app_dir)

        # is script project, check whether compile scripts or not
        need_reset_dir = False
        if self._project._is_script_project():
            script_src_dir = os.path.join(self._project.get_project_dir(), "src")

            if self._project._is_js_project() and self._compile_script:
                # backup the source scripts
                self.backup_dir(script_src_dir)
                self.compile_js_scripts(script_src_dir, script_src_dir)

                # js project need compile the js files in engine
                engine_js_dir = self.get_engine_js_dir()
                if engine_js_dir is not None:
                    self.backup_dir(engine_js_dir)
                    self.compile_js_scripts(engine_js_dir, engine_js_dir)
                need_reset_dir = True

            if self._project._is_lua_project() and (self._lua_encrypt or self._compile_script):
                # on iOS, only invoke luacompile when lua encrypt is specified
                self.backup_dir(script_src_dir)
                self.compile_lua_scripts(script_src_dir, script_src_dir)
                need_reset_dir = True

        try:
            cocos.Logging.info("building")

            command = ' '.join([
                "xcodebuild",
                "-project",
                "\"%s\"" % projectPath,
                "-configuration",
                "%s" % 'Debug' if self._mode == 'debug' else 'Release',
                "-target",
                "\"%s\"" % targetName,
                "CONFIGURATION_BUILD_DIR=\"%s\"" % (output_dir)
                ])

            self._run_cmd(command)

            self.target_name = targetName
            filelist = os.listdir(output_dir)
            for filename in filelist:
                name, extention = os.path.splitext(filename)
                if extention == '.a':
                    filename = os.path.join(output_dir, filename)
                    os.remove(filename)

            self._macapp_path = os.path.join(output_dir, "%s.app" % targetName)
            if self._no_res:
                resource_path = os.path.join(self._macapp_path, "Contents", "Resources")
                self._remove_res(resource_path)

            cocos.Logging.info("build succeeded.")
        except:
            raise cocos.CCPluginError("Build failed: Take a look at the output above for details.")
        finally:
            # is script project & need reset dirs
            if need_reset_dir:
                script_src_dir = os.path.join(self._project.get_project_dir(), "src")
                self.reset_backup_dir(script_src_dir)

                if self._project._is_js_project():
                    engine_js_dir = self.get_engine_js_dir()
                    if engine_js_dir is not None:
                        self.reset_backup_dir(engine_js_dir)

    def _get_required_vs_version(self, proj_file):
        # get the VS version required by the project
        # file_obj = open(proj_file)
        # pattern = re.compile(r"^# Visual Studio.+(\d{4})")
        # num = None
        # for line in file_obj:
        #     match = pattern.match(line)
        #     if match is not None:
        #         num = match.group(1)
        #         break
        #
        # if num is not None:
        #     if num == "2012":
        #         ret = "11.0"
        #     elif num == "2013":
        #         ret = "12.0"
        #     else:
        #         ret = None
        # else:
        #     ret = None

        if self._platforms.is_wp8_active() or self._platforms.is_wp8_1_active() or self._platforms.is_metro_active():
            # WP8 project required VS 2013
            return "12.0"
        else:
            # win32 project required VS 2012
            return "11.0"

    def _get_vs_path(self, require_version):
        # find the VS in register, if system is 64bit, should find vs in both 32bit & 64bit register
        if cocos.os_is_32bit_windows():
            reg_flag_list = [ _winreg.KEY_WOW64_32KEY ]
        else:
            reg_flag_list = [ _winreg.KEY_WOW64_64KEY, _winreg.KEY_WOW64_32KEY ]

        needUpgrade = False
        find_Path = None
        find_ver = 0
        version_pattern = re.compile(r'(\d+)\.(\d+)')
        for reg_flag in reg_flag_list:
            cocos.Logging.info("find vs in reg : %s" % ("32bit" if reg_flag == _winreg.KEY_WOW64_32KEY else "64bit"))
            try:
                vs = _winreg.OpenKey(
                    _winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\VisualStudio",
                    0,
                    _winreg.KEY_READ | reg_flag
                )
            except:
                continue

            i = 0
            while True:
                # enum the keys in vs reg
                try:
                    version = _winreg.EnumKey(vs, i)
                except:
                    break
                i += 1

                match = re.match(version_pattern, version)
                if match is None:
                    continue

                # find the vs which version >= required version
                try:
                    ver_float = float('%s.%s' % (match.group(1), match.group(2)))
                    if ver_float >= float(require_version):
                        key = _winreg.OpenKey(vs, r"SxS\VS7")
                        vsPath, type = _winreg.QueryValueEx(key, version)
                        if os.path.exists(vsPath):
                            if (find_Path is None) or (ver_float > find_ver):
                                find_Path = vsPath
                                find_ver = ver_float
                except:
                    pass

        if find_ver > float(require_version):
            needUpgrade = True

        return (needUpgrade, find_Path)

    def _get_msbuild_version(self):
        try:
            reg_path = r'SOFTWARE\Microsoft\MSBuild'

            reg_key = _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                reg_path
            )

            try:
                i = 0
                while True:
                    reg_subkey = _winreg.EnumKey(reg_key, i)
                    yield reg_subkey
                    i += 1
            except:
                pass

        except WindowsError as e:
            message = "MSBuild is not installed yet!"
            print(e)
            raise cocos.CCPluginError(message)

    def _get_newest_msbuild_version(self):
        newest_version = None
        newest_version_number = 0

        version_pattern = re.compile('(\\d+)\\.(\\d+)')
        for version in self._get_msbuild_version():
            if version:
                match = version_pattern.match(version)
                if match:
                    version_number = int(match.group(1)) * 10 + int(match.group(2))
                    if version_number > newest_version_number:
                        newest_version_number = version_number
                        newest_version = version

        return newest_version

    def _get_msbuild_path(self):
        newest_msbuild_version = self._get_newest_msbuild_version()
        if newest_msbuild_version:
            reg_path = r'SOFTWARE\Microsoft\MSBuild\ToolsVersions\%s' % newest_msbuild_version
            reg_key = _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                reg_path
            )

            reg_value, reg_value_type = _winreg.QueryValueEx(reg_key, 'MSBuildToolsPath')
            return reg_value

        else:
            return None

    def build_vs_project(self, sln_file, project_name, build_mode):
        # get the required VS version
        required_vs_version = self._get_required_vs_version(sln_file)
        if required_vs_version is None:
            raise cocos.CCPluginError("Can't parse the sln file to find required VS version")

        cocos.Logging.info("Required VS version : %s" % required_vs_version)

        # get the correct available VS path
        needUpgrade, vsPath = self._get_vs_path(required_vs_version)

        if vsPath is None:
            message = "Can't find correct Visual Studio's path in the regedit"
            raise cocos.CCPluginError(message)

        cocos.Logging.info("Find VS path : %s" % vsPath)

        commandPath = os.path.join(vsPath, "Common7", "IDE", "devenv.com")

        if os.path.exists(commandPath):
            # upgrade projects
            if needUpgrade:
                commandUpgrade = ' '.join([
                    "\"%s\"" % commandPath,
                    "\"%s\"" % sln_file,
                    "/Upgrade"
                ])
                self._run_cmd(commandUpgrade)

            # build the project
            commands = ' '.join([
                "\"%s\"" % commandPath,
                "\"%s\"" % sln_file,
                "/Build \"%s\"" % build_mode,
                "/Project \"%s\"" % project_name
            ])

            self._run_cmd(commands)
        else:
            cocos.Logging.info('Not found devenv. Try to use msbuild instead.')

            msbuild_path = self._get_msbuild_path()

            if msbuild_path:
                msbuild_path = os.path.join(msbuild_path, 'MSBuild.exe')
                cocos.Logging.info('Found msbuild path: %s' % msbuild_path)

                job_number = 2
                build_command = ' '.join([
                    '\"%s\"' % msbuild_path,
                    '\"%s\"' % sln_file,
                    '/target:%s' % project_name,
                    '/property:Configuration=%s' % build_mode,
                    '/maxcpucount:%s' % job_number
                    ])

                self._run_cmd(build_command)

        cocos.Logging.info("build succeeded.")

    def build_win32(self):
        if not self._platforms.is_win32_active():
            return

        if not cocos.os_is_win32():
            raise cocos.CCPluginError("Please build on winodws")

        win32_projectdir = self._platforms.project_path()
        output_dir = self._output_dir

        cocos.Logging.info("building")

        # get the solution file & project name
        cfg_obj = self._platforms.get_current_config()
        if cfg_obj.sln_file is not None:
            sln_name = cfg_obj.sln_file
            if cfg_obj.project_name is None:
                raise cocos.CCPluginError("Must specified \"%s\" when \"%s\" is specified in file \"%s\"") % \
                      (cocos_project.Win32Config.KEY_PROJECT_NAME, cocos_project.Win32Config.KEY_SLN_FILE, cocos_project.Project.CONFIG)
            else:
                name = cfg_obj.project_name
        else:
            name, sln_name = self.checkFileByExtention(".sln", win32_projectdir)
            if not sln_name:
                message = "Can't find the \".sln\" file"
                raise cocos.CCPluginError(message)

        # build the project
        self.project_name = name
        projectPath = os.path.join(win32_projectdir, sln_name)
        build_mode = 'Debug' if self._is_debug_mode() else 'Release'
        self.build_vs_project(projectPath, self.project_name, build_mode)

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
            cocos.copy_files_with_config(cfg, build_cfg_path, output_dir)

        # check the project config & compile the script files
        if self._project._is_js_project():
            self.compile_js_scripts(output_dir, output_dir)

        if self._project._is_lua_project():
            self.compile_lua_scripts(output_dir, output_dir)

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

        output_dir = CCPluginCompile.OUTPUT_DIR_SCRIPT_RELEASE
        if self._is_debug_mode():
            output_dir = CCPluginCompile.OUTPUT_DIR_SCRIPT_DEBUG
            if not self._web_advanced:
                return

        self.sub_url = '%s%s/%s/' % (self.sub_url, output_dir, CCPluginCompile.WEB_PLATFORM_FOLDER_NAME)

        f = open(os.path.join(project_dir, "project.json"))
        project_json = json.load(f)
        f.close()
        engine_dir = os.path.join(project_json["engineDir"])
        realEngineDir = os.path.normpath(os.path.join(project_dir, engine_dir))
        publish_dir = os.path.normpath(os.path.join(project_dir, output_dir, CCPluginCompile.WEB_PLATFORM_FOLDER_NAME))

        # need to config in options of command
        buildOpt = {
                "outputFileName" : "game.min.js",
                "debug": "true" if self._is_debug_mode() else "false",
                "compilationLevel" : "advanced" if self._web_advanced else "simple",
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

        # copy to the output directory if necessary
        pub_dir = os.path.normcase(publish_dir)
        out_dir = os.path.normcase(os.path.normpath(self._output_dir))
        if pub_dir != out_dir:
            cpy_cfg = {
                "from" : pub_dir,
                "to" : out_dir
            }
            cocos.copy_files_with_config(cpy_cfg, pub_dir, out_dir)

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
            build_mode = 'Debug' if self._is_debug_mode() else 'Release'
            debug_state = 'ON' if self._is_debug_mode() else 'OFF'
            self._run_cmd('cmake -DCMAKE_BUILD_TYPE=%s -DDEBUG_MODE=%s %s' % (build_mode, debug_state, os.path.relpath(cmakefile_dir, build_dir)))

        with cocos.pushd(build_dir):
            self._run_cmd('make -j%s' % self._jobs)

        # move file
        output_dir = self._output_dir

        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(output_dir)

        if cfg_obj.build_result_dir is not None:
            result_dir = os.path.join(build_dir, 'bin', cfg_obj.build_result_dir)
        else:
            result_dir = os.path.join(build_dir, 'bin')
        cocos.copy_files_in_dir(result_dir, output_dir)

        self.run_root = output_dir

        if self._no_res:
            res_dir = os.path.join(output_dir, "Resources")
            self._remove_res(res_dir)

        if self._project._is_script_project() and self._compile_script:
            cocos.Logging.warning("Warning: Now script compiling is not supported for linux.")

        cocos.Logging.info('Build successed!')

    def get_wp8_product_id(self, manifest_file):
        # get the product id from manifest
        from xml.dom import minidom

        ret = None
        try:
            doc_node = minidom.parse(manifest_file)
            root_node = doc_node.documentElement
            app_node = root_node.getElementsByTagName("App")[0]
            ret = app_node.attributes["ProductID"].value
            ret = ret.strip("{}")
        except:
            raise cocos.CCPluginError("Can't parse manifest file %s." % manifest_file)

        return ret


    def build_wp8(self):
        if not self._platforms.is_wp8_active():
            return

        proj_path = self._project.get_project_dir()
        sln_path = self._platforms.project_path()
        output_dir = self._output_dir

        cocos.Logging.info("building")

        # get the solution file & project name
        cfg_obj = self._platforms.get_current_config()
        if cfg_obj.sln_file is not None:
            sln_name = cfg_obj.sln_file
            if cfg_obj.project_name is None:
                raise cocos.CCPluginError("Must specified \"%s\" when \"%s\" is specified in file \"%s\"") % \
                      (cocos_project.Win32Config.KEY_PROJECT_NAME, cocos_project.Win32Config.KEY_SLN_FILE, cocos_project.Project.CONFIG)
            else:
                name = cfg_obj.project_name
        else:
            name, sln_name = self.checkFileByExtention(".sln", sln_path)
            if not sln_name:
                message = "Can't find the \".sln\" file"
                raise cocos.CCPluginError(message)

        wp8_projectdir = cfg_obj.wp8_proj_path

        # build the project
        self.project_name = name
        projectPath = os.path.join(sln_path, sln_name)
        build_mode = 'Debug' if self._is_debug_mode() else 'Release'
        self.build_vs_project(projectPath, self.project_name, build_mode)

        # copy files
        build_folder_path = os.path.join(wp8_projectdir, cfg_obj.build_folder_path, build_mode)
        if not os.path.isdir(build_folder_path):
            message = "Can not find the directory %s" % build_folder_path
            raise cocos.CCPluginError(message)

        # create output dir if it not existed
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # copy xap
        files = os.listdir(build_folder_path)
        proj_xap_name = "%s_%s_x86.xap" % (self.project_name, build_mode)
        for filename in files:
            if filename == proj_xap_name:
                file_path = os.path.join(build_folder_path, filename)
                cocos.Logging.info("Copying %s" % filename)
                shutil.copy(file_path, output_dir)
                break

        # get the manifest file path
        manifest_file = os.path.join(wp8_projectdir, cfg_obj.manifest_path)
        self.product_id = self.get_wp8_product_id(manifest_file)
        self.run_root = output_dir
        self.xap_file_name = proj_xap_name

    def build_wp8_1(self):
        if not self._platforms.is_wp8_1_active():
            return

        wp8_1_projectdir = self._platforms.project_path()
        output_dir = self._output_dir

        cocos.Logging.info("building")

        # get the solution file & project name
        cfg_obj = self._platforms.get_current_config()
        if cfg_obj.sln_file is not None:
            sln_name = cfg_obj.sln_file
            if cfg_obj.project_name is None:
                raise cocos.CCPluginError("Must specified \"%s\" when \"%s\" is specified in file \"%s\"") % \
                      (cocos_project.Win32Config.KEY_PROJECT_NAME, cocos_project.Win32Config.KEY_SLN_FILE, cocos_project.Project.CONFIG)
            else:
                name = cfg_obj.project_name
        else:
            name, sln_name = self.checkFileByExtention(".sln", wp8_1_projectdir)
            if not sln_name:
                message = "Can't find the \".sln\" file"
                raise cocos.CCPluginError(message)
            name = "%s.WindowsPhone" % name

        # build the project
        self.project_name = name
        projectPath = os.path.join(wp8_1_projectdir, sln_name)
        build_mode = 'Debug' if self._is_debug_mode() else 'Release'
        self.build_vs_project(projectPath, self.project_name, build_mode)

    def build_metro(self):
        if not self._platforms.is_metro_active():
            return

        metro_projectdir = self._platforms.project_path()
        output_dir = self._output_dir

        cocos.Logging.info("building")

        # get the solution file & project name
        cfg_obj = self._platforms.get_current_config()
        if cfg_obj.sln_file is not None:
            sln_name = cfg_obj.sln_file
            if cfg_obj.project_name is None:
                raise cocos.CCPluginError("Must specified \"%s\" when \"%s\" is specified in file \"%s\"") % \
                      (cocos_project.Win32Config.KEY_PROJECT_NAME, cocos_project.Win32Config.KEY_SLN_FILE, cocos_project.Project.CONFIG)
            else:
                name = cfg_obj.project_name
        else:
            name, sln_name = self.checkFileByExtention(".sln", metro_projectdir)
            if not sln_name:
                message = "Can't find the \".sln\" file"
                raise cocos.CCPluginError(message)
            name = "%s.Windows" % name

        # build the project
        self.project_name = name
        projectPath = os.path.join(metro_projectdir, sln_name)
        build_mode = 'Debug' if self._is_debug_mode() else 'Release'
        self.build_vs_project(projectPath, self.project_name, build_mode)

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

        target_platform = self._platforms.get_current_platform()
        args_build_copy = self._custom_step_args.copy()

        language = self._project.get_language()
        action_str = 'compile_%s' % language
        target_str = 'compile_for_%s' % target_platform
        cocos.DataStatistic.stat_event('compile', action_str, target_str)

        # invoke the custom step: pre-build
        self._project.invoke_custom_step_script(cocos_project.Project.CUSTOM_STEP_PRE_BUILD, target_platform, args_build_copy)

        self.build_android()
        self.build_ios()
        self.build_mac()
        self.build_win32()
        self.build_web()
        self.build_linux()
        self.build_wp8()
        self.build_wp8_1()
        self.build_metro()

        # invoke the custom step: post-build
        self._project.invoke_custom_step_script(cocos_project.Project.CUSTOM_STEP_POST_BUILD, target_platform, args_build_copy)

        if len(self.end_warning) > 0:
            cocos.Logging.warning(self.end_warning)
