#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos2d "version" plugin
#
# Author: Ricardo Quesada
# Copyright 2013 (C) Zynga, Inc
#
# License: MIT
# ----------------------------------------------------------------------------
'''
"version" plugin for cocos2d command line tool
'''

__docformat__ = 'restructuredtext'

import re
import os
import cocos2d
import inspect


#
# Plugins should be a sublass of CCJSPlugin
#
class CCPluginVersion(cocos2d.CCPlugin):

    @staticmethod
    def plugin_name():
    	return "version"

    @staticmethod
    def brief_description():
        return "prints the version of the installed components"

    # This is not the constructor, just an initializator
    def init(self, options, workingdir):
        self._src_dir = os.path.normpath(options.src_dir)
        super(CCPluginVersion, self).init(options, workingdir)

    def _show_versions(self):
    	with open(os.path.join(self._src_dir, "cocos2dx/cocos2d.cpp"), 'r')  as f:
    		data = f.read()
    		match = re.search('cocos2dVersion\(\)\s*{\s*return\s+"([^"]+)"\s*;', data)
    		if match:
    			print 'cocos2d %s' % match.group(1)
    		else:
    			raise cocos2d.CCPluginError("Couldn't find version info")

    # will be called from the cocos2d.py script
    def run(self, argv):
        self.parse_args(argv)
        self._show_versions()

    def parse_args(self, argv):
        from optparse import OptionParser

        parser = OptionParser("usage: %%prog %s -s src_dir -h -v" % CCPluginVersion.plugin_name())
        parser.add_option("-s", "--src",
                          dest="src_dir",
                          help="project base directory")
        self._add_common_options(parser)

        (options, args) = parser.parse_args(argv)

        if options.src_dir == None:
            raise cocos2d.CCPluginError("Please set source folder with \"-s\" or \"-src\", use -h for the usage ")
        else:
            if os.path.exists(options.src_dir) == False:
              raise cocos2d.CCPluginError("Error: dir (%s) doesn't exist..." % (options.src_dir))


        workingdir = os.path.dirname(inspect.getfile(inspect.currentframe()))

        self.init(options, workingdir)

