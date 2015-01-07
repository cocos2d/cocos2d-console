#!/usr/bin/python
# build_native.py
# Build native codes


import sys
import os, os.path
import shutil
from optparse import OptionParser
import cocos
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

    def __init__(self, verbose, app_android_root, no_res, proj_obj):
        self._verbose = verbose

        self.app_android_root = app_android_root
        self._no_res = no_res
        self._project = proj_obj
        self.ant_cfg_file = os.path.join(self.app_android_root, "ant.properties")

        self._parse_cfg()

    def _run_cmd(self, command):
        cocos.CMDRunner.run_cmd(command, self._verbose)


    def _parse_cfg(self):
        self.cfg_path = os.path.join(self.app_android_root, BUILD_CFIG_FILE)
        try:
            f = open(self.cfg_path)
            cfg = json.load(f, encoding='utf8')
            f.close()
        except Exception:
            raise cocos.CCPluginError("Configuration file \"%s\" is not existed or broken!" % self.cfg_path)

        if cfg.has_key(project_compile.CCPluginCompile.CFG_KEY_MUST_COPY_RESOURCES):
            if self._no_res:
                self.res_files = cfg[project_compile.CCPluginCompile.CFG_KEY_MUST_COPY_RESOURCES]
            else:
                self.res_files = cfg[project_compile.CCPluginCompile.CFG_KEY_MUST_COPY_RESOURCES] + cfg[project_compile.CCPluginCompile.CFG_KEY_COPY_RESOURCES]
        else:
            self.res_files = cfg[project_compile.CCPluginCompile.CFG_KEY_COPY_RESOURCES]

        self.ndk_module_paths = cfg['ndk_module_path']

        # get the properties for sign release apk
        move_cfg = {}
        self.key_store = None
        if cfg.has_key(AndroidBuilder.CFG_KEY_STORE):
            self.key_store = cfg[AndroidBuilder.CFG_KEY_STORE]
            move_cfg["key.store"] = self.key_store
            del cfg[AndroidBuilder.CFG_KEY_STORE]

        self.key_store_pass = None
        if cfg.has_key(AndroidBuilder.CFG_KEY_STORE_PASS):
            self.key_store_pass = cfg[AndroidBuilder.CFG_KEY_STORE_PASS]
            move_cfg["key.store.password"] = self.key_store_pass
            del cfg[AndroidBuilder.CFG_KEY_STORE_PASS]

        self.alias = None
        if cfg.has_key(AndroidBuilder.CFG_KEY_ALIAS):
            self.alias = cfg[AndroidBuilder.CFG_KEY_ALIAS]
            move_cfg["key.alias"] = self.alias
            del cfg[AndroidBuilder.CFG_KEY_ALIAS]

        self.alias_pass = None
        if cfg.has_key(AndroidBuilder.CFG_KEY_ALIAS_PASS):
            self.alias_pass = cfg[AndroidBuilder.CFG_KEY_ALIAS_PASS]
            move_cfg["key.alias.password"] = self.alias_pass
            del cfg[AndroidBuilder.CFG_KEY_ALIAS_PASS]

        if len(move_cfg) > 0:
            # move the config into ant.properties
            self._move_cfg(move_cfg)
            with open(self.cfg_path, 'w') as outfile:
                json.dump(cfg, outfile, sort_keys = True, indent = 4)
                outfile.close()

    def has_keystore_in_antprops(self):
        keystore = None
        try:
            file_obj = open(self.ant_cfg_file)
            pattern = re.compile(r"^key\.store=(.+)")
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

    def _write_ant_properties(self, cfg):
        file_obj = open(self.ant_cfg_file, "a+")
        for key in cfg.keys():
            str_cfg = "%s=%s\n" % (key, cfg[key])
            file_obj.write(str_cfg)

        file_obj.close()

    def _move_cfg(self, cfg):
        if not self.has_keystore_in_antprops():
            self._write_ant_properties(cfg)

    def remove_c_libs(self, libs_dir):
        for file_name in os.listdir(libs_dir):
            lib_file = os.path.join(libs_dir,  file_name)
            if os.path.isfile(lib_file):
                ext = os.path.splitext(lib_file)[1]
                if ext == ".a" or ext == ".so":
                    os.remove(lib_file)
                    
    def update_project(self, sdk_root, android_platform):
        sdk_tool_path = os.path.join(sdk_root, "tools", "android")
        app_android_root = self.app_android_root

        # check the android platform
        target_str = self.check_android_platform(sdk_root, android_platform, app_android_root, False)

        # update project
        command = "%s update project -t %s -p %s" % (cocos.CMDRunner.convert_path_to_cmd(sdk_tool_path), target_str, app_android_root)
        self._run_cmd(command)

        # update lib-projects
        self.update_lib_projects(sdk_root, sdk_tool_path, android_platform)

    def get_toolchain_version(self, ndk_root, compile_obj):
        ret_version = "4.8"

        version_file_path = os.path.join(ndk_root, "RELEASE.TXT")
        try:
            versionFile = open(version_file_path)
            lines = versionFile.readlines()
            versionFile.close()

            version_num = None
            version_char = None
            pattern = r'^[a-zA-Z]+(\d+)(\w)'
            for line in lines:
                str_line = line.lstrip()
                match = re.match(pattern, str_line)
                if match:
                    version_num = int(match.group(1))
                    version_char = match.group(2)
                    break

            if version_num is None:
                cocos.Logging.warning("Parse NDK version from file %s failed." % version_file_path)
            else:
                version_char = version_char.lower()
                if version_num > 10 or (version_num == 10 and cmp(version_char, 'c') >= 0):
                    ret_version = "4.9"
                else:
                    compile_obj.add_warning_at_end(
                '''The NDK version is not r10c or above.
Your application may crash or freeze on Android L(5.0) when using BMFont and HttpClient.
For More information:
    https://github.com/cocos2d/cocos2d-x/issues/9114
    https://github.com/cocos2d/cocos2d-x/issues/9138\n''')
        except:
            cocos.Logging.warning("Parse NDK version from file %s failed." % version_file_path)

        cocos.Logging.info("NDK_TOOLCHAIN_VERSION: %s" % ret_version)
        if ret_version == "4.8":
            compile_obj.add_warning_at_end(
                "Your application may crash when using c++ 11 regular expression with NDK_TOOLCHAIN_VERSION %s" % ret_version)

        return ret_version

    def do_ndk_build(self, ndk_build_param, build_mode, compile_obj):
        cocos.Logging.info('NDK build mode: %s' % build_mode)
        ndk_root = cocos.check_environment_variable('NDK_ROOT')

        toolchain_version = self.get_toolchain_version(ndk_root, compile_obj)

        app_android_root = self.app_android_root
        reload(sys)
        sys.setdefaultencoding('utf8')
        ndk_path = cocos.CMDRunner.convert_path_to_cmd(os.path.join(ndk_root, "ndk-build"))

        module_paths = []
        for cfg_path in self.ndk_module_paths:
            if cfg_path.find("${ENGINE_ROOT}") >= 0:
                cocos_root = cocos.check_environment_variable("COCOS_X_ROOT")
                module_paths.append(cfg_path.replace("${ENGINE_ROOT}", cocos_root))
            elif cfg_path.find("${COCOS_FRAMEWORKS}") >= 0:
                cocos_frameworks = cocos.check_environment_variable("COCOS_FRAMEWORKS")
                module_paths.append(cfg_path.replace("${COCOS_FRAMEWORKS}", cocos_frameworks))
            else:
                module_paths.append(os.path.join(app_android_root, cfg_path))

        # delete template static and dynamic files
        obj_local_dir = os.path.join(self.app_android_root, "obj", "local")
        if os.path.isdir(obj_local_dir):
            for abi_dir in os.listdir(obj_local_dir):
                static_file_path = os.path.join(self.app_android_root, "obj", "local", abi_dir)
                if os.path.isdir(static_file_path):
                    self.remove_c_libs(static_file_path)
           	    
        # windows should use ";" to seperate module paths
        if cocos.os_is_win32():
            ndk_module_path = ';'.join(module_paths)
        else:
            ndk_module_path = ':'.join(module_paths)
        
        ndk_module_path= 'NDK_MODULE_PATH=' + ndk_module_path

        if ndk_build_param is None:
            ndk_build_cmd = '%s -C %s %s' % (ndk_path, app_android_root, ndk_module_path)
        else:
            ndk_build_cmd = '%s -C %s %s %s' % (ndk_path, app_android_root, ' '.join(ndk_build_param), ndk_module_path)

        ndk_build_cmd = '%s NDK_TOOLCHAIN_VERSION=%s' % (ndk_build_cmd, toolchain_version)

        if build_mode == 'debug':
            ndk_build_cmd = '%s NDK_DEBUG=1' % ndk_build_cmd

        self._run_cmd(ndk_build_cmd)


    def _xml_attr(self, dir, file_name, node_name, attr):
        doc = minidom.parse(os.path.join(dir, file_name))
        return doc.getElementsByTagName(node_name)[0].getAttribute(attr)

    def update_lib_projects(self, sdk_root, sdk_tool_path, android_platform):
        property_file = os.path.join(self.app_android_root, "project.properties")
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
                abs_lib_path = os.path.join(self.app_android_root, lib_path)
                if os.path.isdir(abs_lib_path):
                    target_str = self.check_android_platform(sdk_root, android_platform, abs_lib_path, True)
                    command = "%s update lib-project -p %s -t %s" % (cocos.CMDRunner.convert_path_to_cmd(sdk_tool_path), abs_lib_path, target_str)
                    self._run_cmd(command)


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
                    raise cocos.CCPluginError("%s is not a valid android target platform." % target_str)
                else:
                    ret = -1

        return ret

    def get_target_config(self, proj_path):
        property_file = os.path.join(proj_path, "project.properties")
        if not os.path.isfile(property_file):
            raise cocos.CCPluginError("Can't find file \"%s\"" % property_file)

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

        raise cocos.CCPluginError("Can't find \"target\" in file \"%s\"" % property_file)

    # check the selected android platform
    def check_android_platform(self, sdk_root, android_platform, proj_path, auto_select):
        ret = android_platform
        min_platform = self.get_target_config(proj_path)
        if android_platform is None:
            # not specified platform, found one
            cocos.Logging.info('Android platform not specified, searching a default one...')
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
                    raise cocos.CCPluginError("The android-platform of project \"%s\" should be equal/larger than %d, but %d is specified." % (proj_path, min_platform, select_api_level))

        if ret is None:
            raise cocos.CCPluginError("Can't find right android-platform for project : \"%s\". The android-platform should be equal/larger than %d" % (proj_path, min_platform))

        ret_path = os.path.join(cocos.CMDRunner.convert_path_to_python(sdk_root), "platforms", ret)
        if not os.path.isdir(ret_path):
            raise cocos.CCPluginError("The directory \"%s\" can't be found in android SDK" % ret)

        special_platforms_info = {
            "android-4.2" : "android-17"
        }
        if special_platforms_info.has_key(ret):
            ret = special_platforms_info[ret]

        return ret

                
    def do_build_apk(self, sdk_root, ant_root, build_mode, output_dir, custom_step_args, compile_obj):
        app_android_root = self.app_android_root

        # copy resources
        self._copy_resources(custom_step_args)

        # check the project config & compile the script files
        assets_dir = os.path.join(app_android_root, "assets")
        if self._project._is_lua_project():
            compile_obj.compile_lua_scripts(assets_dir, assets_dir)

        if self._project._is_js_project():
            compile_obj.compile_js_scripts(assets_dir, assets_dir)

        # gather the sign info if necessary
        if build_mode == "release" and not self.has_keystore_in_antprops():
            self._gather_sign_info()

        # run ant build
        ant_path = os.path.join(ant_root, 'ant')
        buildfile_path = os.path.join(app_android_root, "build.xml")

        # generate paramters for custom step
        args_ant_copy = custom_step_args.copy()
        target_platform = cocos_project.Platforms.ANDROID

        # invoke custom step: pre-ant-build
        self._project.invoke_custom_step_script(cocos_project.Project.CUSTOM_STEP_PRE_ANT_BUILD, target_platform, args_ant_copy)

        command = "%s clean %s -f %s -Dsdk.dir=%s" % (cocos.CMDRunner.convert_path_to_cmd(ant_path), build_mode, buildfile_path, cocos.CMDRunner.convert_path_to_cmd(sdk_root))
        self._run_cmd(command)

        # invoke custom step: post-ant-build
        self._project.invoke_custom_step_script(cocos_project.Project.CUSTOM_STEP_POST_ANT_BUILD, target_platform, args_ant_copy)

        if output_dir:
            project_name = self._xml_attr(app_android_root, 'build.xml', 'project', 'name')
            apk_name = '%s-%s.apk' % (project_name, build_mode)

            #TODO 'bin' is hardcoded, take the value from the Ant file
            gen_apk_path = os.path.join(app_android_root, 'bin', apk_name)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            shutil.copy(gen_apk_path, output_dir)
            cocos.Logging.info("Move apk to %s" % output_dir)

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
            raise cocos.CCPluginError("Not specified the output directory!")

    def _gather_sign_info(self):
        user_cfg = {}
        # get the path of keystore file
        while True:
            inputed = self._get_user_input("Please input the absolute/relative path of \".keystore\" file:")
            inputed = inputed.strip()
            if not os.path.isabs(inputed):
                abs_path = os.path.join(self.app_android_root, inputed)
            else:
                abs_path = inputed

            if os.path.isfile(abs_path):
                user_cfg["key.store"] = inputed
                break
            else:
                cocos.Logging.warning("The string inputed is not a file!")

        # get the alias of keystore file
        user_cfg["key.alias"] = self._get_user_input("Please input the alias:")

        # get the keystore password
        user_cfg["key.store.password"] = self._get_user_input("Please input the password of key store:")

        # get the alias password
        user_cfg["key.alias.password"] = self._get_user_input("Please input the password of alias:")

        # write the config into ant.properties
        self._write_ant_properties(user_cfg)

    def _get_user_input(self, tip_msg):
        cocos.Logging.warning(tip_msg)
        ret = None
        while True:
            ret = raw_input()
            break

        return ret

    def _copy_resources(self, custom_step_args):
        app_android_root = self.app_android_root
        res_files = self.res_files

        # remove app_android_root/assets if it exists
        assets_dir = os.path.join(app_android_root, "assets")
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
