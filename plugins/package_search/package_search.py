#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos "package search" plugin
#
# Copyright 2014 (C) cocos2d-x.org
#
# License: MIT
# ----------------------------------------------------------------------------
'''
"package search" plugin for cocos command line tool
'''

__docformat__ = 'restructuredtext'

# python
import cocos
from package_common import PackageHelper

#
# Plugins should be a sublass of CCPlugin
#
class CCPluginPackageSearch(cocos.CCPlugin):
    @staticmethod
    def plugin_name():
        return "search"

    @staticmethod
    def brief_description():
        return "Search packages by keywords in remote repo"

    # parse arguments
    def parse_args(self, argv):
        """Custom and check param list.
        """
        from argparse import ArgumentParser
        # set the parser to parse input params
        # the correspond variable name of "-x, --xxx" is parser.xxx
        parser = ArgumentParser(prog="cocos %s" % self.__class__.plugin_name(),
                                description=self.__class__.brief_description())
        parser.add_argument("keyword", metavar="KEYWORDS", nargs='?', help="Specifies the search keywords")

        # parse the params
        args = parser.parse_args(argv)

        if args.keyword is None:
            message = "Fatal: not specifies search keyword"
            raise cocos.CCPluginError(message)

        return args

    # main entry point
    def run(self, argv, dependencies):
        args = self.parse_args(argv)
        keyword = args.keyword
        packages = PackageHelper.search_keyword(keyword)
        keys = packages.keys()
        if len(keys) == 0:
            print "[PACKAGE] not found packages for keyword '%s'" % keyword
            return

        print "[PACKAGE] list all packages for keyword '%s'" % keyword
        keys.sort()
        for k in keys:
            package_data = packages[k]
            print "[PACKAGE] > %s version: %s" % (package_data["name"], package_data["version"])

        print ""
