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

    def clean_android(self):
        project_dir = self._platforms.android_path
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
        project_dir = self._platforms.ios_path
        if project_dir is None:
            return
        #TODO do it

    def run(self, argv, dependencies):
        self.parse_args(argv)
        self.clean_android()
        self.clean_ios()
