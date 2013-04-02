#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos2d "dist" plugin
#
# Author: Ricardo Quesada
# Copyright 2013 (C) Zynga, Inc
#
# License: MIT
# ----------------------------------------------------------------------------
'''
"dist" plugin for cocos2d command line tool
'''

__docformat__ = 'restructuredtext'


# python
import cocos2d


#
# Plugins should be a sublass of CCJSPlugin
#
class CCPluginDist(cocos2d.CCPlugin):

    @staticmethod
    def help():
        return "dist\tcreates a package ready to be distributed"

    def run(self, argv):
        print "dist called!"
        print argv
