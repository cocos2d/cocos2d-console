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

    def _show_versions(self):
    	with open(os.path.join(self._src_dir, "cocos2dx/cocos2d.cpp"), 'r')  as f:
    		data = f.read()
    		match = re.search('cocos2dVersion\(\)\s*{\s*return\s+"([^"]+)"\s*;', data)
    		if match:
    			print 'cocos2d %s' % match.group(1)
    		else:
    			raise cocos2d.CCPluginError("Couldn't find version info")

    def run(self, argv):
    	self.parse_args(argv)
        self._show_versions()

