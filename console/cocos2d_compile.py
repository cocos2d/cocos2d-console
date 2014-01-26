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
        # returns a short description of this module
        return "compiles a project in debug mode"

    # This is not the constructor, just an initializator
    def init(self, options, workingdir):
        self._src_dir = os.path.normpath(options.src_dir)
        self._workingdir = workingdir
        self._verbose = options.verbose

    def _build_project_dir(self, project_name, display_name):
        project_dir = os.path.join(self._src_dir, 'proj.android')
        found = os.path.isdir(project_dir)

        if not found:
            print "No %s project found at %s" % (display_name, project_dir)
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

    # will be called from the cocos2d.py script
    def run(self, argv):
        self.parse_args(argv)
        self.build_android()
        self.build_ios()

    def parse_args(self, argv):
        from optparse import OptionParser

        parser = OptionParser("usage: %%prog %s -s src_dir -h -v" % CCPluginCompile.plugin_name())
        parser.add_option("-s", "--src",
                          dest="src_dir",
                          help="project base directory")
        parser.add_option("-v", "--verbose",
                          action="store_true",
                          dest="verbose",
                          help="verbose output")

        (options, args) = parser.parse_args(argv)

        if options.src_dir == None:
            raise Exception("Please set source folder with \"-s\" or \"-src\", use -h for the usage ")
        else:
            if os.path.exists(options.src_dir) == False:
              raise Exception("Error: dir (%s) doesn't exist..." % (options.src_dir))


        workingdir = os.path.dirname(inspect.getfile(inspect.currentframe()))

        self.init(options, workingdir)

