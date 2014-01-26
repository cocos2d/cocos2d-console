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
        # returns a short description of this module
        return "install a project in a device"

    # This is not the constructor, just an initializator
    def init(self, options, workingdir):
        self._src_dir = os.path.normpath(options.src_dir)
        super(CCPluginInstall, self).init(options, workingdir)

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


    # will be called from the cocos2d.py script
    def run(self, argv):
        self.parse_args(argv)
        self.install_android()

    def parse_args(self, argv):
        from optparse import OptionParser

        parser = OptionParser("usage: %%prog %s -s src_dir -h -v" % CCPluginInstall.plugin_name())
        parser.add_option("-s", "--src",
                          dest="src_dir",
                          help="project base directory")
        self._add_common_options(parser)

        (options, args) = parser.parse_args(argv)

        if options.src_dir == None:
            raise Exception("Please set source folder with \"-s\" or \"-src\", use -h for the usage ")
        else:
            if os.path.exists(options.src_dir) == False:
              raise Exception("Error: dir (%s) doesn't exist..." % (options.src_dir))


        workingdir = os.path.dirname(inspect.getfile(inspect.currentframe()))

        self.init(options, workingdir)

