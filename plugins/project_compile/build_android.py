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

def select_toolchain_version(ndk_root):
    '''Because ndk-r8e uses gcc4.6 as default. gcc4.6 doesn't support c++11. So we should select gcc4.7 when
    using ndk-r8e. But gcc4.7 is removed in ndk-r9, so we should determine whether gcc4.7 exist.
    Conclution:
    ndk-r8e  -> use gcc4.7
    ndk-r9   -> use gcc4.8
    '''

    if os.path.isdir(os.path.join(ndk_root,"toolchains", "arm-linux-androideabi-4.8")):
        os.environ['NDK_TOOLCHAIN_VERSION'] = '4.8'
        cocos.Logging.info("The Selected NDK toolchain version was 4.8 !")
    elif os.path.isdir(os.path.join(ndk_root,"toolchains", "arm-linux-androideabi-4.7")):
        os.environ['NDK_TOOLCHAIN_VERSION'] = '4.7'
        cocos.Logging.info("The Selected NDK toolchain version was 4.7 !")
    else:
        message = "Couldn't find the gcc toolchain."
        raise cocos.CCPluginError(message)

class AndroidBuilder(object):

    CFG_KEY_COPY_TO_ASSETS = "copy_to_assets"
    CFG_KEY_MUST_COPY_TO_ASSERTS = "must_copy_to_assets"
    CFG_KEY_STORE = "key_store"
    CFG_KEY_STORE_PASS = "key_store_pass"
    CFG_KEY_ALIAS = "alias"
    CFG_KEY_ALIAS_PASS = "alias_pass"

    def __init__(self, verbose, cocos_root, app_android_root, no_res, proj_obj):
        self._verbose = verbose

        self.cocos_root = cocos_root
        self.app_android_root = app_android_root
        self._no_res = no_res
        self._project = proj_obj

        self._parse_cfg()

    def _run_cmd(self, command):
        cocos.CMDRunner.run_cmd(command, self._verbose)

    def _convert_path_to_cmd(self, path):
        """ Convert path which include space to correct style which bash(mac) and cmd(windows) can treat correctly.
        
            eg: on mac: convert '/usr/xxx/apache-ant 1.9.3' to '/usr/xxx/apache-ant\ 1.9.3'
            eg: on windows: convert '"c:\apache-ant 1.9.3"\bin' to '"c:\apache-ant 1.9.3\bin"'
        """
        ret = path
        if cocos.os_is_mac():
            ret = path.replace("\ ", " ").replace(" ", "\ ")

        if cocos.os_is_win32():
            ret = "\"%s\"" % (path.replace("\"", ""))

        # print("!!!!! Convert %s to %s\n" % (path, ret))
        return ret
   
    def _convert_path_to_python(self, path):
        """ COnvert path which include space to correct style which python can treat correctly.

            eg: on mac: convert '/usr/xxx/apache-ant\ 1.9.3' to '/usr/xxx/apache-ant 1.9.3'
            eg: on windows: convert '"c:\apache-ant 1.9.3"\bin' to 'c:\apache-ant 1.9.3\bin'
        """
        ret = path
        if cocos.os_is_mac():
            ret = path.replace("\ ", " ")

        if cocos.os_is_win32():
            ret = ret.replace("\"", "")

        # print("!!!!! Convert %s to %s\n" % (path, ret))
        return ret

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

    def _write_ant_properties(self, cfg):
        ant_cfg_file = os.path.join(self.app_android_root, "ant.properties")
        file_obj = open(ant_cfg_file, "a")
        for key in cfg.keys():
            str_cfg = "%s=%s\n" % (key, cfg[key])
            file_obj.write(str_cfg)

        file_obj.close()

    def _move_cfg(self, cfg):
        # add into ant.properties
        ant_cfg_file = os.path.join(self.app_android_root, "ant.properties")
        file_obj = open(ant_cfg_file)
        pattern = re.compile(r"^key\.store=(.+)")
        keystore = None
        for line in file_obj:
            str1 = line.replace(' ', '')
            str2 = str1.replace('\t', '')
            match = pattern.match(str2)
            if match is not None:
                keystore = match.group(1)
                break

        file_obj.close()

        if keystore is None:
            # ant.properties not have the config for sign
            self._write_ant_properties(cfg)

    def remove_c_libs(self, libs_dir):
        for file_name in os.listdir(libs_dir):
            lib_file = os.path.join(libs_dir,  file_name)
            if os.path.isfile(lib_file):
                ext = os.path.splitext(lib_file)[1]
                if ext == ".a" or ext == ".so":
                    os.remove(lib_file)
                    
                    
    def do_ndk_build(self, ndk_build_param, build_mode):
        cocos.Logging.info('NDK build mode: %s' % build_mode)
        ndk_root = cocos.check_environment_variable('NDK_ROOT')
        select_toolchain_version(ndk_root)

        app_android_root = self.app_android_root
        cocos_root = self.cocos_root
        ndk_path = os.path.join(ndk_root, "ndk-build")
        module_paths = [os.path.join(app_android_root, path) for path in self.ndk_module_paths]

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

        if ndk_build_param == None:
            ndk_build_cmd = '%s -C %s %s' % (ndk_path, app_android_root, ndk_module_path)
        else:
            ndk_build_cmd = '%s -C %s %s %s' % (ndk_path, app_android_root, ''.join(str(e) for e in ndk_build_param), ndk_module_path)

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
                    api_level = self.check_android_platform(sdk_root, android_platform, abs_lib_path, True)
                    str_api_level = "android-" + str(api_level)
                    command = "%s update lib-project -p %s -t %s" % (self._convert_path_to_cmd(sdk_tool_path), abs_lib_path, str_api_level)
                    self._run_cmd(command)

    def get_target_config(self, proj_path):
        property_file = os.path.join(proj_path, "project.properties")
        if not os.path.isfile(property_file):
            raise cocos.CCPluginError("Can't find file \"%s\"" % property_file)

        patten = re.compile(r'^target=android-(\d+)')
        for line in open(property_file):
            str1 = line.replace(' ', '')
            str2 = str1.replace('\t', '')
            match = patten.match(str2)
            if match is not None:
                target = match.group(1)
                target_num = int(target)
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
            ret = cocos.select_default_android_platform(min_platform)
        else:
            # check whether it's larger than min_platform
            if android_platform < min_platform:
                if auto_select:
                    # select one for project
                    ret = cocos.select_default_android_platform(min_platform)
                else:
                    # raise error
                    raise cocos.CCPluginError("The android-platform of project \"%s\" should be equal/larger than %d, but %d is specified." % (proj_path, min_platform, android_platform))

        if ret is None:
            raise cocos.CCPluginError("Can't find right android-platform for project : \"%s\". The android-platform should be equal/larger than %d" % (proj_path, min_platform))

        platform_path = "android-%d" % ret
        ret_path = os.path.join(self._convert_path_to_python(sdk_root), "platforms", platform_path)
        if not os.path.isdir(ret_path):
            raise cocos.CCPluginError("The directory \"%s\" can't be found in android SDK" % platform_path)

        return ret

                
    def do_build_apk(self, sdk_root, ant_root, android_platform, build_mode, output_dir, custom_step_args, compile_obj):
        sdk_tool_path = os.path.join(sdk_root, "tools", "android")
        cocos_root = self.cocos_root
        app_android_root = self.app_android_root

        # check the android platform
        api_level = self.check_android_platform(sdk_root, android_platform, app_android_root, False)

        # update project
        str_api_level = "android-" + str(api_level)
        command = "%s update project -t %s -p %s" % (self._convert_path_to_cmd(sdk_tool_path), str_api_level, app_android_root)
        self._run_cmd(command)

        # update lib-projects
        self.update_lib_projects(sdk_root, sdk_tool_path, android_platform)

        # copy resources
        self._copy_resources(custom_step_args)

        # check the project config & compile the script files
        assets_dir = os.path.join(app_android_root, "assets")
        compile_obj.compile_scripts(assets_dir, assets_dir)

        # run ant build
        ant_path = os.path.join(ant_root, 'ant')
        buildfile_path = os.path.join(app_android_root, "build.xml")

        # generate paramters for custom step
        args_ant_copy = custom_step_args.copy()
        target_platform = cocos_project.Platforms.ANDROID

        # invoke custom step: pre-ant-build
        self._project.invoke_custom_step_script(cocos_project.Project.CUSTOM_STEP_PRE_ANT_BUILD, target_platform, args_ant_copy)

        command = "%s clean %s -f %s -Dsdk.dir=%s" % (self._convert_path_to_cmd(ant_path), build_mode, buildfile_path, self._convert_path_to_cmd(sdk_root))
        self._run_cmd(command)

        # invoke custom step: post-ant-build
        self._project.invoke_custom_step_script(cocos_project.Project.CUSTOM_STEP_POST_ANT_BUILD, target_platform, args_ant_copy)

        if output_dir:
            project_name = self._xml_attr(app_android_root, 'build.xml', 'project', 'name')
            if build_mode == 'release':
               apk_name = '%s-%s-unsigned.apk' % (project_name, build_mode)
            else:
               apk_name = '%s-%s.apk' % (project_name, build_mode)
            #TODO 'bin' is hardcoded, take the value from the Ant file
            apk_path = os.path.join(app_android_root, 'bin', apk_name)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            shutil.copy(apk_path, output_dir)
            cocos.Logging.info("Move apk to %s" % output_dir)

            # check whether the apk is signed in release mode
            if build_mode == 'release':
                signed_name = '%s-%s-signed.apk' % (project_name, build_mode)
                apk_path = os.path.join(output_dir, signed_name)
                check_file_name = "%s-%s.apk" % (project_name, build_mode)
                check_full_path = os.path.join(app_android_root, 'bin', check_file_name)
                if os.path.isfile(check_full_path):
                    # Ant already signed the apk
                    shutil.copy(check_full_path, output_dir)
                    if os.path.exists(apk_path):
                        os.remove(apk_path)
                    os.rename(os.path.join(output_dir, check_file_name), apk_path)
                else:
                    # sign the apk
                    self._sign_release_apk(os.path.join(output_dir, apk_name), apk_path)
                    # align the apk
                    aligned_file = os.path.join(output_dir, "%s-%s-aligned.apk" % (project_name, build_mode))
                    self._zipalign_apk(apk_path, aligned_file, sdk_root)
            else:
                apk_path = os.path.join(output_dir, apk_name)

            return apk_path
        else:
            raise cocos.CCPluginError("Not specified the output directory!")

    def _sign_release_apk(self, unsigned_path, signed_path):
        # get the properties for the signning
        user_cfg = {}
        if self.key_store is None:
            while True:
                inputed = self._get_user_input("Please input the absolute/relative path of \".keystore\" file:")
                if not os.path.isabs(inputed):
                    abs_path = os.path.join(self.app_android_root, inputed)
                else:
                    abs_path = inputed

                if os.path.isfile(abs_path):
                    self.key_store = abs_path
                    user_cfg["key.store"] = inputed
                    break
                else:
                    cocos.Logging.warning("The string inputed is not a file!")
        elif not os.path.isabs(self.key_store):
            self.key_store = os.path.join(self.app_android_root, self.key_store)

        if self.key_store_pass is None:
            self.key_store_pass = self._get_user_input("Please input the password of key store:")
            user_cfg["key.store.password"] = self.key_store_pass

        if self.alias is None:
            self.alias = self._get_user_input("Please input the alias:")
            user_cfg["key.alias"] = self.alias

        if self.alias_pass is None:
            self.alias_pass = self._get_user_input("Please input the password of alias:")
            user_cfg["key.alias.password"] = self.alias_pass

        # sign the apk
        sign_cmd = "jarsigner -sigalg SHA1withRSA -digestalg SHA1 "
        sign_cmd += "-keystore \"%s\" " % self.key_store
        sign_cmd += "-storepass %s " % self.key_store_pass
        sign_cmd += "-keypass %s " % self.alias_pass
        sign_cmd += "-signedjar \"%s\" \"%s\" %s" % (signed_path, unsigned_path, self.alias)
        self._run_cmd(sign_cmd)

        if len(user_cfg) > 0:
            self._write_ant_properties(user_cfg)

        # output tips
        cocos.Logging.warning("\nThe release apk was signed, the signed apk path is %s" % signed_path)
        cocos.Logging.warning("\nkeystore file : %s" % self.key_store)
        cocos.Logging.warning("password of keystore file : %s" % self.key_store_pass)
        cocos.Logging.warning("alias : %s" % self.alias)
        cocos.Logging.warning("password of alias : %s\n" % self.alias_pass)
        cocos.Logging.warning("The properties for sign was stored in file %s\n" % os.path.join(self.app_android_root, "ant.properties"))

    def _zipalign_apk(self, apk_file, aligned_file, sdk_root):
        align_path = os.path.join(sdk_root, "tools", "zipalign")
        align_cmd = "%s 4 %s %s" % (self._convert_path_to_cmd(align_path), apk_file, aligned_file)
        if os.path.exists(aligned_file):
            os.remove(aligned_file)
        self._run_cmd(align_cmd)
        # remove the unaligned apk
        os.remove(apk_file)
        # rename the aligned apk
        os.rename(aligned_file, apk_file)

    def _get_user_input(self, tip_msg):
        cocos.Logging.warning(tip_msg)
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
