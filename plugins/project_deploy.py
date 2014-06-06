#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos "install" plugin
#
# Copyright 2013 (C) Luis Parravicini
#
# License: MIT
# ----------------------------------------------------------------------------
'''
"install" plugin for cocos command line tool
'''

__docformat__ = 'restructuredtext'

import sys
import os
import json
import inspect
from xml.dom import minidom
import shutil
import cocos


class CCPluginDeploy(cocos.CCPlugin):
    """
    Install a project
    """

    @staticmethod
    def depends_on():
        return ('compile',)

    @staticmethod
    def plugin_name():
        return "deploy"

    @staticmethod
    def brief_description():
        return "Deploy a project to the target"

    def _add_custom_options(self, parser):
        parser.add_argument("-m", "--mode", dest="mode", default='debug',
                          help="Set the deploy mode, should be debug|release, default is debug.")

    def _check_custom_options(self, args):

        if args.mode != 'release':
            args.mode = 'debug'

        self._mode = 'debug'
        if 'release' == args.mode:
            self._mode = args.mode

    def _is_debug_mode(self):
        return self._mode == 'debug'

    def _xml_attr(self, dir, file_name, node_name, attr):
        doc = minidom.parse(os.path.join(dir, file_name))
        return doc.getElementsByTagName(node_name)[0].getAttribute(attr)

    def deploy_ios(self, dependencies):
        if not self._platforms.is_ios_active():
            return

        compile_dep = dependencies['compile']
        self._iosapp_path = compile_dep._iosapp_path
        self._mode = compile_dep._mode

    def deploy_mac(self, dependencies):
        if not self._platforms.is_mac_active():
            return

        compile_dep = dependencies['compile']
        self._macapp_path = compile_dep._macapp_path
        self.target_name = compile_dep.target_name

    def deploy_web(self, dependencies):
        if not self._platforms.is_web_active():
            return

        compile_dep = dependencies['compile']
        self.sub_url = compile_dep.sub_url
        self.run_root = compile_dep.run_root

    def deploy_win32(self, dependencies):
        if not self._platforms.is_win32_active():
            return

        compile_dep = dependencies['compile']
        self.run_root = compile_dep.run_root
        self.project_name = compile_dep.project_name

    def deploy_linux(self, dependencies):
        if not self._platforms.is_linux_active():
            return

        compile_dep = dependencies['compile']
        self.run_root = compile_dep.run_root
        self.project_name = compile_dep.project_name

    def deploy_android(self, dependencies):
        if not self._platforms.is_android_active():
            return

        project_dir = self._project.get_project_dir()
        android_project_dir = self._platforms.project_path()

        cocos.Logging.info("installing on device")
        self.package = self._xml_attr(android_project_dir, 'AndroidManifest.xml', 'manifest', 'package')
        activity_name = self._xml_attr(android_project_dir, 'AndroidManifest.xml', 'activity', 'android:name')
        if activity_name.startswith('.'):
            self.activity = self.package + activity_name
        else:
            self.activity = activity_name

        compile_dep = dependencies['compile']
        apk_path = compile_dep.apk_path
        sdk_root = cocos.check_environment_variable('ANDROID_SDK_ROOT')
        adb_path = os.path.join(sdk_root, 'platform-tools', 'adb')

        #TODO detect if the application is installed before running this
        adb_uninstall = "%s uninstall %s" % (adb_path, self.package)
        self._run_cmd(adb_uninstall)
        adb_install = "%s install \"%s\"" % (adb_path, apk_path)
        self._run_cmd(adb_install)

    def get_filename_by_extention(self, ext, path):
        filelist = os.listdir(path)

        for fname in filelist:
            name, extention = os.path.splitext(fname)
            if extention == ext:
                return  fname
        return None

    def run(self, argv, dependencies):
        self.parse_args(argv)
        cocos.Logging.info('Deploying mode: %s' % self._mode)
        self.deploy_ios(dependencies)
        self.deploy_mac(dependencies)
        self.deploy_android(dependencies)
        self.deploy_web(dependencies)
        self.deploy_win32(dependencies)
        self.deploy_linux(dependencies)
