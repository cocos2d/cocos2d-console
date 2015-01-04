#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos "package info" plugin
#
# Copyright 2014 (C) cocos2d-x.org
#
# License: MIT
# ----------------------------------------------------------------------------
'''
"add-framework" plugin for cocos command line tool
'''

__docformat__ = 'restructuredtext'

# python
import cocos
import time
from package_common import PackageHelper
from package_common import ProjectHelper

#
# Plugins should be a sublass of CCPlugin
#
class CCPluginFrameworkAdd(cocos.CCPlugin):
    @staticmethod
    def plugin_name():
        return "add-framework"

    @staticmethod
    def brief_description():
        return "Adds a new framework to an existing project"

    # parse arguments
    def parse_args(self, argv):
        """Custom and check param list.
        """
        from argparse import ArgumentParser
        # set the parser to parse input params
        # the correspond variable name of "-x, --xxx" is parser.xxx
        parser = ArgumentParser(prog="cocos %s" % self.__class__.plugin_name(),
                                description=self.__class__.brief_description())
        parser.add_argument("name", metavar="NAME", nargs='?', help="Specifies the package name")

        # parse the params
        args = parser.parse_args(argv)

        if args.name is None:
            message = "Fatal: not specifies package name"
            raise cocos.CCPluginError(message)

        return args

    # main entry point
    def run(self, argv, dependencies):
        args = self.parse_args(argv)
        name = args.name

        project = ProjectHelper.get_current_project()
        ProjectHelper.add_framework(project, name)
