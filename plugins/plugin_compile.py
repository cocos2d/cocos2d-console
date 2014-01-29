#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos2d "compile" plugin
#
# Copyright 2013 (C) Luis Parravicini
#
# License: MIT
# ----------------------------------------------------------------------------
'''
"compile" plugin for cocos2d command line tool
'''

__docformat__ = 'restructuredtext'

import sys
import os
import json
import inspect

import cocos2d

class CCPluginCompile(cocos2d.CCPlugin):
    """
    compiles a project
    """

    @staticmethod
    def plugin_name():
      return "compile"

    @staticmethod
    def brief_description():
        return "compiles a project in debug mode"

    def _build_project_dir(self, project_name, display_name):
        project_dir = os.path.join(self._src_dir, 'proj.android')
        found = os.path.isdir(project_dir)

        if not found:
            cocos2d.Logging.warning("No %s project found at %s" % (display_name, project_dir))
            return None

        return project_dir

    def build_android(self):
        project_dir = self._build_project_dir('proj.android', 'Android')
        if project_dir is None:
            return
        cocos2d.Logging.info("building native")
        self._run_cmd("cd \"%s\" && ./build_native.sh" % project_dir)
        cocos2d.Logging.info("building apk")
        self._run_cmd("cd \"%s\" && ant debug" % project_dir)

    def build_ios(self):
        project_dir = self._build_project_dir('proj.ios', 'iOS')
        if project_dir is None:
            return
        #TODO do it

    def run(self, argv, dependencies):
        self.parse_args(argv)
        self.build_android()
        self.build_ios()
