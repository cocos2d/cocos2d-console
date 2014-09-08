#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos2d "dgate" plugin
#
# Copyright 2014 (C) TAKUMA Kei
#
# License: MIT
# ----------------------------------------------------------------------------

"""
"Deploygate" plugin for cocos command line tool
"""

__docformat__ = 'restructuredtext'

import os
import re
import cocos

class CCPluginDgate(cocos.CCPlugin):
    """
    Push a iOS/Android app to http://deploygate.com
    """

    @staticmethod
    def depends_on():
        return ('compile',)

    @staticmethod
    def plugin_name():
        return "dgate"

    @staticmethod
    def brief_description():
        return "Push a iOS/Android app to http://deploygate.com"

    def _add_custom_options(self, parser):
        parser.add_argument("-m", "--mode", dest="mode", default="debug",
                help="Set the compile mode, should be debug|release, default is debug.")
        group = parser.add_argument_group("android debug Options")
        parser.add_argument("--sign-debug-apk", dest="sign_debug_apk", action="store_true", help="re-sign the debug apk")
        group = parser.add_argument_group("deploygate Options")
        parser.add_argument("--dgate-owner", dest="dgate_owner", help="deploygate owner/group name")
        parser.add_argument("--dgate-message", dest="dgate_message", help="deploygate message")

    def _check_custom_options(self, args):
        if args.mode != 'release':
            args.mode = 'debug'

        self._mode = 'debug'
        if 'release' == args.mode:
            self._mode = args.mode

        self._sign_debug_apk = args.sign_debug_apk
        self._dgate_message = args.dgate_message
        self._dgate_owner = args.dgate_owner

    def run_android(self, dependencies):
        if not self._platforms.is_android_active():
            return

        compile_dep = dependencies['compile']
        self.app_android_root = compile_dep._platforms.project_path()
        apk_path = compile_dep.apk_path

        if self._mode == 'debug' and self._sign_debug_apk:
            apk_path = self._run_sign_apk(apk_path)

        self.run_dgate_push(apk_path)

        cocos.Logging.info("succeeded.")

    def _run_sign_apk(self, apk_path):
        signed_path = "%s-signed%s" % os.path.splitext(apk_path)
        self._read_ant_properties()
        self._run_sign_debug_apk(apk_path, signed_path)
        self._zipalign_apk(signed_path)
        return signed_path

    def _read_ant_properties(self):
        self.key_store = None
        self.key_store_pass = None
        self.alias = None
        self.alias_pass = None
        props = {}
        ant_props = os.path.join(self.app_android_root, "ant.properties")
        try:
            parser = re.compile("\s*([^#=][^=]*)=(.*)")
            with open(ant_props) as f:
                for line in f:
                    kv = parser.match(line)
                    if kv is not None:
                        props[kv.group(1)] = kv.group(2)
            self.key_store = props["key.store"]
            self.key_store_pass = props["key.store.password"]
            self.alias = props["key.alias"]
            self.alias_pass = props["key.alias.password"]
        except:
            cocos.Logging.info("%s not found" % ant_props)

    def _run_sign_debug_apk(self, unsigned_path, signed_path):
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
        cocos.Logging.warning("\nThe debug apk was signed, the signed apk path is %s" % signed_path)
        cocos.Logging.warning("\nkeystore file : %s" % self.key_store)
        cocos.Logging.warning("password of keystore file : %s" % self.key_store_pass)
        cocos.Logging.warning("alias : %s" % self.alias)
        cocos.Logging.warning("password of alias : %s\n" % self.alias_pass)
        cocos.Logging.warning("The properties for sign was stored in file %s\n" % os.path.join(self.app_android_root, "ant.properties"))

    def _write_ant_properties(self, cfg):
        ant_cfg_file = os.path.join(self.app_android_root, "ant.properties")
        file_obj = open(ant_cfg_file, "a")
        for key in cfg.keys():
            str_cfg = "%s=%s\n" % (key, cfg[key])
            file_obj.write(str_cfg)

        file_obj.close()

    def _zipalign_apk(self, apk_file):
        aligned_file = "%s-aligned%s" % os.path.splitext(apk_file)
        sdk_root = cocos.check_environment_variable('ANDROID_SDK_ROOT')
        align_path = os.path.join(sdk_root, "bin", "zipalign")
        align_cmd = "%s 4 %s %s" % (cocos.CMDRunner.convert_path_to_cmd(align_path), apk_file, aligned_file)
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

    def run_ios(self, dependencies):
        if not self._platforms.is_ios_active():
            return

        compile_dep = dependencies['compile']

        if compile_dep.use_sdk != 'iphoneos':
            cocos.Logging.warning("The generated app is for simulator.")
            return

        self.run_dgate_push(compile_dep._iosipa_path)

        cocos.Logging.info("succeeded.")

    def run_dgate_push(self, pathname):
        owner = self._dgate_owner
        message = self._dgate_message
        command = ''.join([
            "dgate push",
            " \"%s\"" % owner if owner is not None else "",
            " \"%s\"" % pathname,
            " -m \"%s\"" % message if message is not None else ""
            ])
        self._run_cmd(command)

    def run(self, argv, dependencies):
        self.parse_args(argv)
        cocos.Logging.info('Building mode: %s' % self._mode)
        if self._dgate_owner is not None:
            cocos.Logging.info('dgate owner/group: %s' % self._dgate_owner)
        cocos.Logging.info('dgate message: %s' % self._dgate_message)
        self.run_android(dependencies)
        self.run_ios(dependencies)
