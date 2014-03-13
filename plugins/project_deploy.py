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

import cocos

class CCPluginDeploy(cocos.CCPlugin):
    """
    Install a project
    """

    @staticmethod
    def plugin_name():
      return "deploy"

    @staticmethod
    def brief_description():
        return "Depoly a project to the target"

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


    def deploy_android(self):
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

        project_name = self._xml_attr(android_project_dir, 'build.xml', 'project', 'name')
        
        if self._mode == 'release':
           apk_name = '%s-%s-unsigned.apk' % (project_name, self._mode)
        else:
           apk_name = '%s-%s-unaligned.apk' % (project_name, self._mode)

        if self._project._is_script_project():
            apk_dir = os.path.join(project_dir, 'runtime', 'android')
        else:
            apk_dir = os.path.join(project_dir, 'bin', self._mode, 'android')

        apk_path = os.path.join(apk_dir, apk_name)

        #TODO detect if the application is installed before running this
        adb_uninstall = "adb uninstall %s" % self.package
        self._run_cmd(adb_uninstall)
        adb_install = "adb install \"%s\"" % apk_path
        self._run_cmd(adb_install)

    def deploy_ios(self):
        if not self._platforms.is_ios_active():
            return
        project_dir = self._project.get_project_dir()

        if self._project._is_script_project():
            app_dir = os.path.join(project_dir, 'runtime', 'ios')
        else:
            app_dir = os.path.join(project_dir, 'bin', self._mode, 'ios')

        app_name = self.get_filename_by_extention(".app", app_dir)

        if not app_name:
            message = "app not found in %s " % app_dir
            raise cocos.CCPluginError(message)

        # not really deploy to somewhere, only remember the app path
        self._iosapp_path = os.path.join(app_dir, app_name)

    def deploy_mac(self):
        if not self._platforms.is_mac_active():
            return
        project_dir = self._project.get_project_dir()

        if self._project._is_script_project():
            app_dir = os.path.join(project_dir, 'runtime', 'mac')
        else:
            app_dir = os.path.join(project_dir, 'bin', self._mode, 'mac')

        app_name = self.get_filename_by_extention(".app", app_dir)
        if not app_name:
            message = "app not found in %s " % app_dir
            raise cocos.CCPluginError(message)

        # not really deploy to somewhere, only remember the app path
        self._macapp_path = os.path.join(app_dir, app_name)
        
    def deploy_web(self):
        if not self._platforms.is_web_active():
            return
        
        if self._is_debug_mode():
            return
        
        cocos.Logging.info("do mini js files..")
        
        pass

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
        self.deploy_android()
        self.deploy_ios()
        self.deploy_mac()
        self.deploy_web()

