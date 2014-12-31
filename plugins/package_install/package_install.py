#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos "package install" plugin
#
# Copyright 2014 (C) cocos2d-x.org
#
# License: MIT
# ----------------------------------------------------------------------------
'''
"package install" plugin for cocos command line tool
'''

__docformat__ = 'restructuredtext'

# python
import cocos
from package_common import PackageHelper

#
# Plugins should be a sublass of CCPlugin
#
class CCPluginPackageInstall(cocos.CCPlugin):
    @staticmethod
    def plugin_name():
        return "install"

    @staticmethod
    def brief_description():
        return "Install a package"

    # parse arguments
    def parse_args(self, argv):
        """Custom and check param list.
        """
        from argparse import ArgumentParser
        # set the parser to parse input params
        # the correspond variable name of "-x, --xxx" is parser.xxx
        parser = ArgumentParser(prog="cocos %s" % self.__class__.plugin_name(),
                                description=self.__class__.brief_description())
        parser.add_argument("name", metavar="PACKAGE_NAME", nargs='?', help="Specifies the package name")
        parser.add_argument("-f", action="store_true", dest="force", help="Ignore exists file, force to download zip from remote repo")

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
        force = args.force

        package_data = PackageHelper.query_package_data(name)
        if package_data == False:
            message = "Fatal: not found package '%s'" % name
            raise cocos.CCPluginError(message)

        PackageHelper.download_package_zip(package_data, force)
        PackageHelper.add_package(package_data)

        print ""
