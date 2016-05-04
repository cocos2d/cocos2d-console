#!/usr/bin/python
# build_native.py
# Build native codes


import sys
import os, os.path
import shutil
from optparse import OptionParser
import cocos
from MultiLanguage import MultiLanguage
import cocos_project
import json
import re
from xml.dom import minidom

import project_compile

BUILD_CFIG_FILE="build-cfg.json"

class AndroidBuilder(object):

    CFG_KEY_COPY_TO_ASSETS = "copy_to_assets"
    CFG_KEY_MUST_COPY_TO_ASSERTS = "must_copy_to_assets"
    CFG_KEY_STORE = "key_store"
    CFG_KEY_STORE_PASS = "key_store_pass"
    CFG_KEY_ALIAS = "alias"
    CFG_KEY_ALIAS_PASS = "alias_pass"

    ANT_KEY_STORE = "key.store"
    ANT_KEY_ALIAS = "key.alias"
    ANT_KEY_STORE_PASS = "key.store.password"
    ANT_KEY_ALIAS_PASS = "key.alias.password"

    GRADLE_KEY_STORE = "RELEASE_STORE_FILE"
    GRADLE_KEY_ALIAS = "RELEASE_KEY_ALIAS"
    GRADLE_KEY_STORE_PASS = "RELEASE_STORE_PASSWORD"
    GRADLE_KEY_ALIAS_PASS = "RELEASE_KEY_PASSWORD"

    def __init__(self, verbose, app_android_root, no_res, proj_obj, use_studio=False):
        self._verbose = verbose

        self.app_android_root = app_android_root
        self._no_res = no_res
        self._project = proj_obj
        self.use_studio = use_studio

        # check environment variable
        if self.use_studio:
            self.ant_root = None
            self.sign_prop_file = os.path.join(self.app_android_root, 'app', "gradle.properties")
        else:
            self.ant_root = cocos.check_environment_variable('ANT_ROOT')
            self.sign_prop_file = os.path.join(self.app_android_root, "ant.properties")
        self.sdk_root = cocos.check_environment_variable('ANDROID_SDK_ROOT')

        self._parse_cfg()

    def _run_cmd(self, command, cwd=None):
        cocos.CMDRunner.run_cmd(command, self._verbose, cwd=cwd)

    def _parse_cfg(self):
        self.cfg_path = os.path.join(self.app_android_root, BUILD_CFIG_FILE)
        try:
            f = open(self.cfg_path)
            cfg = json.load(f, encoding='utf8')
            f.close()
        except Exception:
            raise cocos.CCPluginError(MultiLanguage.get_string('COMPILE_ERROR_PARSE_CFG_FAILED_FMT', self.cfg_path),
                                      cocos.CCPluginError.ERROR_PARSE_FILE)

        if cfg.has_key(project_compile.CCPluginCompile.CFG_KEY_MUST_COPY_RESOURCES):
            if self._no_res:
                self.res_files = cfg[project_compile.CCPluginCompile.CFG_KEY_MUST_COPY_RESOURCES]
            else:
                self.res_files = cfg[project_compile.CCPluginCompile.CFG_KEY_MUST_COPY_RESOURCES] + cfg[project_compile.CCPluginCompile.CFG_KEY_COPY_RESOURCES]
        else:
            self.res_files = cfg[project_compile.CCPluginCompile.CFG_KEY_COPY_RESOURCES]

        self.ndk_module_paths = cfg['ndk_module_path']

        # get the properties for sign release apk
        if self.use_studio:
            self.key_store_str = AndroidBuilder.GRADLE_KEY_STORE
            self.key_alias_str = AndroidBuilder.GRADLE_KEY_ALIAS
            self.key_store_pass_str = AndroidBuilder.GRADLE_KEY_STORE_PASS
            self.key_alias_pass_str = AndroidBuilder.GRADLE_KEY_ALIAS_PASS
        else:
            self.key_store_str = AndroidBuilder.ANT_KEY_STORE
            self.key_alias_str = AndroidBuilder.ANT_KEY_ALIAS
            self.key_store_pass_str = AndroidBuilder.ANT_KEY_STORE_PASS
            self.key_alias_pass_str = AndroidBuilder.ANT_KEY_ALIAS_PASS

        move_cfg = {}
        self.key_store = None
        if cfg.has_key(AndroidBuilder.CFG_KEY_STORE):
            self.key_store = cfg[AndroidBuilder.CFG_KEY_STORE]
            move_cfg[self.key_store_str] = self.key_store
            del cfg[AndroidBuilder.CFG_KEY_STORE]

        self.key_store_pass = None
        if cfg.has_key(AndroidBuilder.CFG_KEY_STORE_PASS):
            self.key_store_pass = cfg[AndroidBuilder.CFG_KEY_STORE_PASS]
            move_cfg[self.key_store_pass_str] = self.key_store_pass
            del cfg[AndroidBuilder.CFG_KEY_STORE_PASS]

        self.alias = None
        if cfg.has_key(AndroidBuilder.CFG_KEY_ALIAS):
            self.alias = cfg[AndroidBuilder.CFG_KEY_ALIAS]
            move_cfg[self.key_alias_str] = self.alias
            del cfg[AndroidBuilder.CFG_KEY_ALIAS]

        self.alias_pass = None
        if cfg.has_key(AndroidBuilder.CFG_KEY_ALIAS_PASS):
            self.alias_pass = cfg[AndroidBuilder.CFG_KEY_ALIAS_PASS]
            move_cfg[self.key_alias_pass_str] = self.alias_pass
            del cfg[AndroidBuilder.CFG_KEY_ALIAS_PASS]

        if len(move_cfg) > 0:
            # move the config into ant.properties
            self._move_cfg(move_cfg)
            with open(self.cfg_path, 'w') as outfile:
                json.dump(cfg, outfile, sort_keys = True, indent = 4)
                outfile.close()

    def has_keystore_in_signprops(self):
        keystore = None
        if self.use_studio:
            pattern = re.compile(r"^RELEASE_STORE_FILE=(.+)")
        else:
            pattern = re.compile(r"^key\.store=(.+)")

        try:
            file_obj = open(self.sign_prop_file)
            for line in file_obj:
                str1 = line.replace(' ', '')
                str2 = str1.replace('\t', '')
                match = pattern.match(str2)
                if match is not None:
                    keystore = match.group(1)
                    break
            file_obj.close()
        except:
            pass

        if keystore is None:
            return False
        else:
            return True

    def _write_sign_properties(self, cfg):
        file_obj = open(self.sign_prop_file, "a+")
        for key in cfg.keys():
            str_cfg = "%s=%s\n" % (key, cfg[key])
            file_obj.write(str_cfg)

        file_obj.close()

    def _move_cfg(self, cfg):
        if not self.has_keystore_in_signprops():
            self._write_sign_properties(cfg)

    def remove_c_libs(self, libs_dir):
        for file_name in os.listdir(libs_dir):
            lib_file = os.path.join(libs_dir,  file_name)
            if os.path.isfile(lib_file):
                ext = os.path.splitext(lib_file)[1]
                if ext == ".a" or ext == ".so":
                    os.remove(lib_file)
                    
    def update_project(self, android_platform):
        if self.use_studio:
            manifest_path = os.path.join(self.app_android_root, 'app')
        else:
            manifest_path = self.app_android_root

        sdk_tool_path = os.path.join(self.sdk_root, "tools", "android")

        # check the android platform
        target_str = self.check_android_platform(self.sdk_root, android_platform, manifest_path, False)

        # update project
        command = "%s update project -t %s -p %s" % (cocos.CMDRunner.convert_path_to_cmd(sdk_tool_path), target_str, manifest_path)
        self._run_cmd(command)

        # update lib-projects
        property_path = manifest_path
        self.update_lib_projects(self.sdk_root, sdk_tool_path, android_platform, property_path)

        if self.use_studio:
            # copy the local.properties to the app_android_root
            file_name = 'local.properties'
            src_path = os.path.normpath(os.path.join(manifest_path, file_name))
            dst_path = os.path.normpath(os.path.join(self.app_android_root, file_name))
            if src_path != dst_path:
                if os.path.isfile(dst_path):
                    os.remove(dst_path)
                shutil.copy(src_path, dst_path)

    def get_toolchain_version(self, ndk_root, compile_obj):
        # use the folder name in toolchains to check get gcc version
        toolchains_path = os.path.join(ndk_root, 'toolchains')
        dir_names = os.listdir(toolchains_path)
        # check if gcc 4.9 exists
        for dir_name in dir_names:
            if dir_name.endswith('4.9'):
                return 4.9

        # use gcc 4.8
        compile_obj.add_warning_at_end(MultiLanguage.get_string('COMPILE_WARNING_TOOLCHAIN_FMT', '4.8'))
        return '4.8'


    def do_ndk_build(self, ndk_build_param, build_mode, compile_obj):
        cocos.Logging.info(MultiLanguage.get_string('COMPILE_INFO_NDK_MODE', build_mode))
        ndk_root = cocos.check_environment_variable('NDK_ROOT')

        toolchain_version = self.get_toolchain_version(ndk_root, compile_obj)

        if self.use_studio:
            ndk_work_dir = os.path.join(self.app_android_root, 'app')
        else:
            ndk_work_dir = self.app_android_root
        reload(sys)
        sys.setdefaultencoding('utf8')
        ndk_path = cocos.CMDRunner.convert_path_to_cmd(os.path.join(ndk_root, "ndk-build"))

        module_paths = []
        for cfg_path in self.ndk_module_paths:
            if cfg_path.find("${COCOS_X_ROOT}") >= 0:
                cocos_root = cocos.check_environment_variable("COCOS_X_ROOT")
                module_paths.append(cfg_path.replace("${COCOS_X_ROOT}", cocos_root))
            elif cfg_path.find("${COCOS_FRAMEWORKS}") >= 0:
                cocos_frameworks = cocos.check_environment_variable("COCOS_FRAMEWORKS")
                module_paths.append(cfg_path.replace("${COCOS_FRAMEWORKS}", cocos_frameworks))
            else:
                module_paths.append(os.path.join(self.app_android_root, cfg_path))

        # delete template static and dynamic files
        obj_local_dir = os.path.join(ndk_work_dir, "obj", "local")
        if os.path.isdir(obj_local_dir):
            for abi_dir in os.listdir(obj_local_dir):
                static_file_path = os.path.join(ndk_work_dir, "obj", "local", abi_dir)
                if os.path.isdir(static_file_path):
                    self.remove_c_libs(static_file_path)
           	    
        # windows should use ";" to seperate module paths
        if cocos.os_is_win32():
            ndk_module_path = ';'.join(module_paths)
        else:
            ndk_module_path = ':'.join(module_paths)
        
        ndk_module_path= 'NDK_MODULE_PATH=' + ndk_module_path

        if ndk_build_param is None:
            ndk_build_cmd = '%s -C %s %s' % (ndk_path, ndk_work_dir, ndk_module_path)
        else:
            ndk_build_cmd = '%s -C %s %s %s' % (ndk_path, ndk_work_dir, ' '.join(ndk_build_param), ndk_module_path)

        ndk_build_cmd = '%s NDK_TOOLCHAIN_VERSION=%s' % (ndk_build_cmd, toolchain_version)

        if build_mode == 'debug':
            ndk_build_cmd = '%s NDK_DEBUG=1' % ndk_build_cmd

        self._run_cmd(ndk_build_cmd)


    def _xml_attr(self, dir, file_name, node_name, attr):
        doc = minidom.parse(os.path.join(dir, file_name))
        return doc.getElementsByTagName(node_name)[0].getAttribute(attr)

    def update_lib_projects(self, sdk_root, sdk_tool_path, android_platform, property_path):
        property_file = os.path.join(property_path, "project.properties")
        if not os.path.isfile(property_file):
            return

        patten = re.compile(r'^android\.library\.reference\.[\d]+=(.+)')
        for line in open(property_file):
            str1 = line.replace(' ', '')
            str2 = str1.replace('\t', '')
            match = patten.match(str2)
            if match is not None:
                # a lib project is found
                lib_path = match.group(1)
                abs_lib_path = os.path.join(property_path, lib_path)
                abs_lib_path = os.path.normpath(abs_lib_path)
                if os.path.isdir(abs_lib_path):
                    target_str = self.check_android_platform(sdk_root, android_platform, abs_lib_path, True)
                    command = "%s update lib-project -p %s -t %s" % (cocos.CMDRunner.convert_path_to_cmd(sdk_tool_path), abs_lib_path, target_str)
                    self._run_cmd(command)

                    self.update_lib_projects(sdk_root, sdk_tool_path, android_platform, abs_lib_path)

    def select_default_android_platform(self, min_api_level):
        ''' select a default android platform in SDK_ROOT
        '''

        sdk_root = cocos.check_environment_variable('ANDROID_SDK_ROOT')
        platforms_dir = os.path.join(sdk_root, "platforms")
        ret_num = -1
        ret_platform = ""
        if os.path.isdir(platforms_dir):
            for dir_name in os.listdir(platforms_dir):
                if not os.path.isdir(os.path.join(platforms_dir, dir_name)):
                    continue

                num = self.get_api_level(dir_name, raise_error=False)
                if num >= min_api_level:
                    if ret_num == -1 or ret_num > num:
                        ret_num = num
                        ret_platform = dir_name

        if ret_num != -1:
            return ret_platform
        else:
            return None


    def get_api_level(self, target_str, raise_error=True):
        special_targats_info = {
            "android-4.2" : 17,
            "android-L" : 20
        }

        if special_targats_info.has_key(target_str):
            ret = special_targats_info[target_str]
        else:
            match = re.match(r'android-(\d+)', target_str)
            if match is not None:
                ret = int(match.group(1))
            else:
                if raise_error:
                    raise cocos.CCPluginError(MultiLanguage.get_string('COMPILE_ERROR_NOT_VALID_AP_FMT', target_str),
                                              cocos.CCPluginError.ERROR_PARSE_FILE)
                else:
                    ret = -1

        return ret

    def get_target_config(self, proj_path):
        property_file = os.path.join(proj_path, "project.properties")
        if not os.path.isfile(property_file):
            raise cocos.CCPluginError(MultiLanguage.get_string('COMPILE_ERROR_FILE_NOT_FOUND_FMT', property_file),
                                      cocos.CCPluginError.ERROR_PATH_NOT_FOUND)

        patten = re.compile(r'^target=(.+)')
        for line in open(property_file):
            str1 = line.replace(' ', '')
            str2 = str1.replace('\t', '')
            match = patten.match(str2)
            if match is not None:
                target = match.group(1)
                target_num = self.get_api_level(target)
                if target_num > 0:
                    return target_num

        raise cocos.CCPluginError(MultiLanguage.get_string('COMPILE_ERROR_TARGET_NOT_FOUND_FMT', property_file),
                                  cocos.CCPluginError.ERROR_PARSE_FILE)

    # check the selected android platform
    def check_android_platform(self, sdk_root, android_platform, proj_path, auto_select):
        ret = android_platform
        min_platform = self.get_target_config(proj_path)
        if android_platform is None:
            # not specified platform, found one
            cocos.Logging.info(MultiLanguage.get_string('COMPILE_INFO_AUTO_SELECT_AP'))
            ret = self.select_default_android_platform(min_platform)
        else:
            # check whether it's larger than min_platform
            select_api_level = self.get_api_level(android_platform)
            if select_api_level < min_platform:
                if auto_select:
                    # select one for project
                    ret = self.select_default_android_platform(min_platform)
                else:
                    # raise error
                    raise cocos.CCPluginError(MultiLanguage.get_string('COMPILE_ERROR_AP_TOO_LOW_FMT',
                                                                       (proj_path, min_platform, select_api_level)),
                                              cocos.CCPluginError.ERROR_WRONG_ARGS)

        if ret is None:
            raise cocos.CCPluginError(MultiLanguage.get_string('COMPILE_ERROR_AP_NOT_FOUND_FMT',
                                                               (proj_path, min_platform)),
                                      cocos.CCPluginError.ERROR_PARSE_FILE)

        ret_path = os.path.join(cocos.CMDRunner.convert_path_to_python(sdk_root), "platforms", ret)
        if not os.path.isdir(ret_path):
            raise cocos.CCPluginError(MultiLanguage.get_string('COMPILE_ERROR_NO_AP_IN_SDK_FMT', ret),
                                      cocos.CCPluginError.ERROR_PATH_NOT_FOUND)

        special_platforms_info = {
            "android-4.2" : "android-17"
        }
        if special_platforms_info.has_key(ret):
            ret = special_platforms_info[ret]

        return ret

    def ant_build_apk(self, build_mode, custom_step_args):
        app_android_root = self.app_android_root

        # run ant build
        ant_path = os.path.join(self.ant_root, 'ant')
        buildfile_path = os.path.join(app_android_root, "build.xml")

        # generate paramters for custom step
        args_ant_copy = custom_step_args.copy()
        target_platform = cocos_project.Platforms.ANDROID

        # invoke custom step: pre-ant-build
        self._project.invoke_custom_step_script(cocos_project.Project.CUSTOM_STEP_PRE_ANT_BUILD,
                                                target_platform, args_ant_copy)

        command = "%s clean %s -f %s -Dsdk.dir=%s" % (cocos.CMDRunner.convert_path_to_cmd(ant_path),
                                                      build_mode, buildfile_path,
                                                      cocos.CMDRunner.convert_path_to_cmd(self.sdk_root))
        self._run_cmd(command)

        # invoke custom step: post-ant-build
        self._project.invoke_custom_step_script(cocos_project.Project.CUSTOM_STEP_POST_ANT_BUILD,
                                                target_platform, args_ant_copy)

    def gradle_build_apk(self, build_mode):
        # check the compileSdkVersion & buildToolsVersion
        check_file = os.path.join(self.app_android_root, 'app', 'build.gradle')
        f = open(check_file)
        lines = f.readlines()
        f.close()

        compile_sdk_ver = None
        build_tools_ver = None
        compile_sdk_pattern = r'compileSdkVersion[ \t]+([\d]+)'
        build_tools_pattern = r'buildToolsVersion[ \t]+"(.+)"'
        for line in lines:
            line_str = line.strip()
            match1 = re.match(compile_sdk_pattern, line_str)
            if match1:
                compile_sdk_ver = match1.group(1)

            match2 = re.match(build_tools_pattern, line_str)
            if match2:
                build_tools_ver = match2.group(1)

        if compile_sdk_ver is not None:
            # check the compileSdkVersion
            check_folder_name = 'android-%s' % compile_sdk_ver
            check_path = os.path.join(self.sdk_root, 'platforms', check_folder_name)
            if not os.path.isdir(check_path):
                cocos.Logging.warning(MultiLanguage.get_string('COMPILE_WARNING_COMPILE_SDK_FMT',
                                                               (compile_sdk_ver, check_path)))

        if build_tools_ver is not None:
            # check the buildToolsVersion
            check_path = os.path.join(self.sdk_root, 'build-tools', build_tools_ver)
            if not os.path.isdir(check_path):
                cocos.Logging.warning(MultiLanguage.get_string('COMPILE_WARNING_BUILD_TOOLS_FMT',
                                                               (build_tools_ver, check_path)))

        # invoke gradlew for gradle building
        if cocos.os_is_win32():
            gradle_path = os.path.join(self.app_android_root, 'gradlew.bat')
        else:
            gradle_path = os.path.join(self.app_android_root, 'gradlew')

        if not os.path.isfile(gradle_path):
            raise cocos.CCPluginError(MultiLanguage.get_string('COMPILE_ERROR_GRALEW_NOT_EXIST_FMT', gradle_path),
                                      cocos.CCPluginError.ERROR_PATH_NOT_FOUND)

        mode_str = 'Debug' if build_mode == 'debug' else 'Release'
        cmd = '"%s" --parallel --info assemble%s' % (gradle_path, mode_str)
        self._run_cmd(cmd, cwd=self.app_android_root)

    def do_build_apk(self, build_mode, no_apk, output_dir, custom_step_args, compile_obj):
        if self.use_studio:
            assets_dir = os.path.join(self.app_android_root, "app", "assets")
            project_name = None
            setting_file = os.path.join(self.app_android_root, 'settings.gradle')
            if os.path.isfile(setting_file):
                # get project name from settings.gradle
                f = open(setting_file)
                lines = f.readlines()
                f.close()

                pattern = r"project\(':(.*)'\)\.projectDir[ \t]*=[ \t]*new[ \t]*File\(settingsDir, 'app'\)"
                for line in lines:
                    line_str = line.strip()
                    match = re.match(pattern, line_str)
                    if match:
                        project_name = match.group(1)
                        break

            if project_name is None:
                # use default project name
                project_name = 'app'
            gen_apk_folder = os.path.join(self.app_android_root, 'app/build/outputs/apk')
        else:
            assets_dir = os.path.join(self.app_android_root, "assets")
            project_name = self._xml_attr(self.app_android_root, 'build.xml', 'project', 'name')
            gen_apk_folder = os.path.join(self.app_android_root, 'bin')

        # copy resources
        self._copy_resources(custom_step_args, assets_dir)

        # check the project config & compile the script files
        if self._project._is_lua_project():
            compile_obj.compile_lua_scripts(assets_dir, assets_dir)

        if self._project._is_js_project():
            compile_obj.compile_js_scripts(assets_dir, assets_dir)

        if not no_apk:
            # gather the sign info if necessary
            if build_mode == "release" and not self.has_keystore_in_signprops():
                self._gather_sign_info()

            # build apk
            if self.use_studio:
                self.gradle_build_apk(build_mode)
            else:
                self.ant_build_apk(build_mode, custom_step_args)

            # copy the apk to output dir
            if output_dir:
                apk_name = '%s-%s.apk' % (project_name, build_mode)
                gen_apk_path = os.path.join(gen_apk_folder, apk_name)
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                shutil.copy(gen_apk_path, output_dir)
                cocos.Logging.info(MultiLanguage.get_string('COMPILE_INFO_MOVE_APK_FMT', output_dir))

                if build_mode == "release":
                    signed_name = "%s-%s-signed.apk" % (project_name, build_mode)
                    apk_path = os.path.join(output_dir, signed_name)
                    if os.path.exists(apk_path):
                        os.remove(apk_path)
                    os.rename(os.path.join(output_dir, apk_name), apk_path)
                else:
                    apk_path = os.path.join(output_dir, apk_name)

                return apk_path
            else:
                raise cocos.CCPluginError(MultiLanguage.get_string('COMPILE_ERROR_NOT_SPECIFY_OUTPUT'),
                                          cocos.CCPluginError.ERROR_WRONG_ARGS)

    def _gather_sign_info(self):
        user_cfg = {}
        # get the path of keystore file
        while True:
            inputed = self._get_user_input(MultiLanguage.get_string('COMPILE_TIP_INPUT_KEYSTORE'))
            inputed = inputed.strip()
            if not os.path.isabs(inputed):
                if self.use_studio:
                    start_path = os.path.join(self.app_android_root, 'app')
                else:
                    start_path = self.app_android_root
                abs_path = os.path.join(start_path, inputed)
            else:
                abs_path = inputed

            if os.path.isfile(abs_path):
                user_cfg[self.key_store_str] = inputed.replace('\\', '/')
                break
            else:
                cocos.Logging.warning(MultiLanguage.get_string('COMPILE_INFO_NOT_A_FILE'))

        # get the alias of keystore file
        user_cfg[self.key_alias_str] = self._get_user_input(MultiLanguage.get_string('COMPILE_TIP_INPUT_ALIAS'))

        # get the keystore password
        user_cfg[self.key_store_pass_str] = self._get_user_input(MultiLanguage.get_string('COMPILE_TIP_INPUT_KEY_PASS'))

        # get the alias password
        user_cfg[self.key_alias_pass_str] = self._get_user_input(MultiLanguage.get_string('COMPILE_TIP_INPUT_ALIAS_PASS'))

        # write the config into ant.properties
        self._write_sign_properties(user_cfg)

    def _get_user_input(self, tip_msg):
        cocos.Logging.warning(tip_msg)
        ret = None
        while True:
            ret = raw_input()
            break

        return ret

    def _copy_resources(self, custom_step_args, assets_dir):
        app_android_root = self.app_android_root
        res_files = self.res_files

        # remove app_android_root/assets if it exists
        if os.path.isdir(assets_dir):
            shutil.rmtree(assets_dir)

        # generate parameters for custom steps
        target_platform = cocos_project.Platforms.ANDROID
        cur_custom_step_args = custom_step_args.copy()
        cur_custom_step_args["assets-dir"] = assets_dir

        # make dir
        os.mkdir(assets_dir)
 
        # invoke custom step : pre copy assets
        self._project.invoke_custom_step_script(cocos_project.Project.CUSTOM_STEP_PRE_COPY_ASSETS, target_platform, cur_custom_step_args)

        # copy resources
        for cfg in res_files:
            cocos.copy_files_with_config(cfg, app_android_root, assets_dir)

        # invoke custom step : post copy assets
        self._project.invoke_custom_step_script(cocos_project.Project.CUSTOM_STEP_POST_COPY_ASSETS, target_platform, cur_custom_step_args)

    def get_apk_info(self):
        if self.use_studio:
            manifest_path = os.path.join(self.app_android_root, 'app')
            gradle_cfg_path = os.path.join(manifest_path, 'build.gradle')
            package = None
            if os.path.isfile(gradle_cfg_path):
                # get package name from build.gradle
                f = open(gradle_cfg_path)
                for line in f.readlines():
                    line_str = line.strip()
                    pattern = r'applicationId[ \t]+"(.*)"'
                    match = re.match(pattern, line_str)
                    if match:
                        package = match.group(1)
                        break

            if package is None:
                # get package name from AndroidManifest.xml
                package = self._xml_attr(manifest_path, 'AndroidManifest.xml', 'manifest', 'package')
        else:
            manifest_path = self.app_android_root
            package = self._xml_attr(manifest_path, 'AndroidManifest.xml', 'manifest', 'package')

        activity_name = self._xml_attr(manifest_path, 'AndroidManifest.xml', 'activity', 'android:name')
        if activity_name.startswith('.'):
            activity = package + activity_name
        else:
            activity = activity_name
        ret = (package, activity)

        return ret
