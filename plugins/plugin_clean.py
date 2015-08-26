#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos "clean" plugin
#
# License: MIT
# ----------------------------------------------------------------------------
'''
"clean" plugin for cocos command line tool
'''

__docformat__ = 'restructuredtext'

import os
import re
import shutil
import cocos
import cocos_project
from MultiLanguage import MultiLanguage
from project_compile import CCPluginCompile

class CCPluginClean(cocos.CCPlugin):
    """
    cleans a project
    """

    @staticmethod
    def plugin_name():
      return "clean"

    @staticmethod
    def brief_description():
        return "removes files produced by compilation"

    def _add_custom_options(self, parser):
        self.ccompile._add_custom_options(parser)

    def _check_custom_options(self, args):
        self.ccompile._check_custom_options(args)

    def clean_android(self, dependencies):
        if not self._platforms.is_android_active():
            return
        project_dir = self._platforms.project_path()

        cocos.Logging.info("cleaning native")
        obj_path = os.path.join(project_dir, 'obj')
        self._rmdir(obj_path)
        cocos.Logging.info("cleaning java")
        self._run_cmd("cd \"%s\" && ant clean" % project_dir)

    def clean_win32(self, dependencies):
        if not self._platforms.is_win32_active():
            return
        cocos.Logging.info("Clean not supported for this platform yet.")

    def clean_web(self,dependencies):
        if not self._platforms.is_web_active():
            return
        cocos.Logging.info("Clean not supported for this platform yet.")

    def clean_linux(self,dependencies):
        if not self._platforms.is_linux_active():
            return
        cocos.Logging.info("Clean not supported for this platform yet.")

    def clean_wp8(self,dependencies):
        if not self._platforms.is_wp8_active():
            return
        cocos.Logging.info("Clean not supported for this platform yet.")

    def clean_wp8_1(self,dependencies):
        if not self._platforms.is_wp8_active():
            return
        cocos.Logging.info("Clean not supported for this platform yet.")

    def clean_metro(self,dependencies):
        if not self._platforms.is_wp8_active():
            return
        cocos.Logging.info("Clean not supported for this platform yet.")

    def clean_ios(self, dependencies):
        if not self._platforms.is_ios_active():
            return
 
        self.ccompile.setup_ios_mac_build_vars()
        output_dir = self.ccompile._output_dir
        target_name = self.ccompile.target_name
        mode = self.ccompile._mode
        use_sdk = self.ccompile.use_sdk
        xcodeproj_path = self.ccompile.xcodeproj_path
        target_app_dir = os.path.join(output_dir, "%s.app" % target_name)

        cocos.Logging.info("Cleaning iOS " + target_name)

        command = ' '.join([
                "xcodebuild clean",
                "-project",
                "\"%s\"" % xcodeproj_path,
                "-configuration",
                "%s" % 'Debug' if mode == 'debug' else 'Release',
                "-target",
                "\"%s\"" % target_name,
                "%s" % "-arch i386" if use_sdk == 'iphonesimulator' else '',
                "-sdk",
                "%s" % use_sdk,
                "CONFIGURATION_BUILD_DIR=\"%s\"" % (output_dir),
                "%s" % "VALID_ARCHS=\"i386\"" if use_sdk == 'iphonesimulator' else ''
                ])

        self._run_cmd(command)

        cocos.Logging.info("Removing " + target_app_dir)
        self._rmdir(target_app_dir)

    def clean_mac(self, dependencies):
        if not self._platforms.is_mac_active():
            return

        self.ccompile.setup_ios_mac_build_vars()
        output_dir = self.ccompile._output_dir
        target_name = self.ccompile.target_name
        mode = self.ccompile._mode
        xcodeproj_path = self.ccompile.xcodeproj_path
        target_app_dir = os.path.join(output_dir, "%s.app" % target_name)

        cocos.Logging.info("Cleaning Mac " + target_name)

        command = ' '.join([
            "xcodebuild clean",
            "-project",
            "\"%s\"" % xcodeproj_path,
            "-configuration",
            "%s" % 'Debug' if mode == 'debug' else 'Release',
            "-target",
            "\"%s\"" % target_name,
            "CONFIGURATION_BUILD_DIR=\"%s\"" % (output_dir)
            ])

        self._run_cmd(command)

        cocos.Logging.info("Removing " + target_app_dir)
        self._rmdir(target_app_dir)


    def _rmdir(self, path):
        if os.path.exists(path):
            try:
                shutil.rmtree(path)
            except OSError as e:
                raise cocos.CCPluginError("Error removing directory: " + str(e.args))


    def run(self, argv, dependencies):
        self.ccompile = CCPluginCompile()
        self.ccompile.parse_args(argv)

        self.parse_args(argv)
        
        self.clean_android(dependencies)
        self.clean_ios(dependencies)
        self.clean_mac(dependencies)

        self.clean_win32(dependencies)
        self.clean_web(dependencies)
        self.clean_linux(dependencies)
        self.clean_wp8(dependencies)
        self.clean_wp8_1(dependencies)
        self.clean_metro(dependencies)
