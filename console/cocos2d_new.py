#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos2d "new" plugin
#
# Author: Ricardo Quesada
# Copyright 2013 (C) Zynga, Inc
#
# License: MIT
# ----------------------------------------------------------------------------
'''
"new" plugin for cocos2d command line tool
'''

__docformat__ = 'restructuredtext'


# python
import cocos2d


#
# Plugins should be a sublass of CCJSPlugin
#
class CCPluginNew(cocos2d.CCPlugin):

    @staticmethod
    def help():
        return "new project_name\tcreates a new project"

    def run(self, argv):
        print "new called!"
        print argv
