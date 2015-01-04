#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos "package info" plugin
#
# Copyright 2014 (C) cocos2d-x.org
#
# License: MIT
# ----------------------------------------------------------------------------
'''
"package info" plugin for cocos command line tool
'''

__docformat__ = 'restructuredtext'

# python
import cocos
import time
from package_common import PackageHelper

#
# Plugins should be a sublass of CCPlugin
#
class CCPluginPackageInfo(cocos.CCPlugin):
    @staticmethod
    def plugin_name():
        return "info"

    @staticmethod
    def brief_description():
        return "Get package information in remote repo"

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
        package_data = PackageHelper.query_package_data(name)
        if package_data is None:
            print "[PACKAGE] not found package '%s'" % name
            return

        print "[PACKAGE] > get description for package '%s' ... ok" % name
        print ""
        print "name: %s" % package_data["name"]
        print "version: %s" % package_data["version"]
        print "updated: %s" % time.strftime("%Y-%m-%d %H:%I:%S", time.gmtime(int(package_data["filetime"])))
        print "author: %s" % package_data["author"]
        print "download size: %d KB" % (int(package_data["filesize"]) / 1024)
        print ""
        print package_data["description"]
        print ""
