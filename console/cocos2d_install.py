#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos2d "install" plugin
#
# Copyright 2013 (C) Luis Parravicini
#
# License: MIT
# ----------------------------------------------------------------------------
'''
"install" plugin for cocos2d command line tool
'''

__docformat__ = 'restructuredtext'

import sys
import os
import json
import inspect
from xml.dom import minidom

import cocos2d

class CCPluginInstall(cocos2d.CCPlugin):
    """
    Install a project
    """

    @staticmethod
    def plugin_name():
      return "install"

    @staticmethod
    def brief_description():
        return "install a project in a device"

    def _build_project_dir(self, project_name, display_name):
        project_dir = os.path.join(self._src_dir, 'proj.android')
        found = os.path.isdir(project_dir)

        if not found:
            cocos2d.Logging.warning("No %s project found at %s" % (display_name, project_dir))
            return None

        return project_dir

    def _xml_attr(self, dir, file_name, node_name, attr):
        doc = minidom.parse(os.path.join(dir, file_name))
        return doc.getElementsByTagName(node_name)[0].getAttribute(attr)

    def install_android(self):
        cocos2d.Logging.info("installing on device")

        project_dir = self._build_project_dir('proj.android', 'Android')
        if project_dir is None:
            return

        package = self._xml_attr(project_dir, 'AndroidManifest.xml', 'manifest', 'package')
        project_name = self._xml_attr(project_dir, 'build.xml', 'project', 'name')
        #TODO 'bin' is hardcoded, take the value from the Ant file
        apk_path = os.path.join(project_dir, 'bin', '%s-debug-unaligned.apk' % project_name)

        #TODO detect if the application is installed before running this
        self._run_cmd("adb uninstall \"%s\"" % package)
        self._run_cmd("adb install \"%s\"" % apk_path)

    def run(self, argv):
        self.parse_args(argv)
        self.install_android()


