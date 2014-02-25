#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos "new" plugin
#
# Copyright 2013 (C) cocos2d-x.org
#
# License: MIT
# ----------------------------------------------------------------------------
'''
"new" plugin for cocos command line tool
'''

__docformat__ = 'restructuredtext'

# python
import os
import sys
import getopt
import ConfigParser

import cocos
from core import CocosProject

#
# Plugins should be a sublass of CCJSPlugin
#
class CCPluginNew(cocos.CCPlugin):

    DEFAULT_PROJ_NAME = {
        CocosProject.CPP : 'MyCppGame',
        CocosProject.LUA : 'MyLuaGame',
        CocosProject.JS : 'MyJSGame'
    }

    @staticmethod
    def plugin_category():
      return "project"

    @staticmethod
    def plugin_name():
      return "new"

    @staticmethod
    def brief_description():
        return "creates a new project"

    # parse arguments
    def parse_args(self, argv):
        """Custom and check param list.
        """
        from optparse import OptionParser
        # set the parser to parse input params
        # the correspond variable name of "-x, --xxx" is parser.xxx
        name = CCPluginNew.plugin_name()
        category = CCPluginNew.plugin_category()
        parser = OptionParser(
            usage=
            "\n\t%%prog %s %s, start GUI version."
            "\n\t%%prog %s %s <PROJECT_NAME> -p <PACKAGE_NAME> -l <cpp|lua|javascript> -d <PROJECT_DIR>"
            "\nSample:"
            "\n\t%%prog %s %s MyGame -p com.MyCompany.AwesomeGame -l javascript -d c:/mycompany" \
                    % (category, name, category, name, category, name)
        )
        parser.add_option("-p", "--package", metavar="PACKAGE_NAME",help="Set a package name for project")
        parser.add_option("-l", "--language",metavar="PROGRAMMING_NAME",
                            type="choice",
                            choices=["cpp", "lua", "javascript"],
                            help="Major programming language you want to use, should be [cpp | lua | javascript]")
        parser.add_option("-d", "--directory", metavar="DIRECTORY",help="Set generate project directory for project")
        parser.add_option("--gui", action="store_true", help="Start GUI")
        parser.add_option("--has-native", action="store_true", dest="has_native", help="Has native support.")

        # parse the params
        (opts, args) = parser.parse_args(argv)

        if not opts.language:
            opts.language = CocosProject.CPP

        if len(args) == 0:
            self.project_name = CCPluginNew.DEFAULT_PROJ_NAME[opts.language]

        if not opts.directory:
            opts.directory = os.getcwd();

        return opts


    def _create_from_ui(self, opts):
        from ui import createTkCocosDialog
        createTkCocosDialog()

    def _create_from_cmd(self, opts):
        from core import create_platform_projects
        create_platform_projects(
                opts.language,
                self.project_name,
                opts.directory,
                opts.package,
                opts.has_native)

    # main entry point
    def run(self, argv, dependencies):
        opts = self.parse_args(argv);
        if opts.gui:
            self._create_from_ui(opts)
        else:
            self._create_from_cmd(opts)

