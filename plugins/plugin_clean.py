#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos2d "clean" plugin
#
# Author: Luis Parravicini
#
# License: MIT
# ----------------------------------------------------------------------------
'''
"clean" plugin for cocos2d command line tool
'''

__docformat__ = 'restructuredtext'

import sys
import os
import json
import shutil

import cocos2d

class CCPluginClean(cocos2d.CCPlugin):
    """
    cleans a project
    """

    @staticmethod
    def plugin_name():
      return "clean"

    @staticmethod
    def brief_description():
        return "removes files produced by compilation"

    #TODO this is copied from CCPluginCompile. refactor
    def _build_project_dir(self, project_name, display_name):
        project_dir = os.path.join(self._src_dir, 'proj.android')
        found = os.path.isdir(project_dir)

        if not found:
            cocos2d.Logging.warning("No %s project found at %s" % (display_name, project_dir))
            return None

        return project_dir

    def clean_android(self):
        project_dir = self._build_project_dir('proj.android', 'Android')
        if project_dir is None:
            return
        cocos2d.Logging.info("cleaning native")
        obj_path = os.path.join(project_dir, 'obj')
        if os.path.exists(obj_path):
            try:
                shutil.rmtree(obj_path)
            except OSError as e:
                raise cocos2d.CCPluginError("Error cleaning native: " + str(e.args))
        cocos2d.Logging.info("cleaning java")
        self._run_cmd("cd \"%s\" && ant clean" % project_dir)

    def clean_ios(self):
        project_dir = self._build_project_dir('proj.ios', 'iOS')
        if project_dir is None:
            return
        #TODO do it

    def run(self, argv, dependencies):
        self.parse_args(argv)
        self.clean_android()
        self.clean_ios()
