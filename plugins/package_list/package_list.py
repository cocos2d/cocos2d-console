#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos "package list" plugin
#
# Copyright 2014 (C) cocos2d-x.org
#
# License: MIT
# ----------------------------------------------------------------------------
'''
"package list" plugin for cocos command line tool
'''

__docformat__ = 'restructuredtext'

# python
import cocos
from package_common import PackageHelper

#
# Plugins should be a sublass of CCPlugin
#
class CCPluginPackageList(cocos.CCPlugin):
    @staticmethod
    def plugin_name():
        return "list"

    @staticmethod
    def brief_description():
        return "List all installed packages"

    # main entry point
    def run(self, argv, dependencies):
        packages = PackageHelper.get_installed_packages()
        keys = packages.keys()
        if len(keys) == 0:
            print "[PACKAGE] not found installed packages"
            return

        print "[PACKAGE] installed packages:"
        keys.sort()
        for k in keys:
            package_data = PackageHelper.get_installed_package_data(packages[k]["name"])
            print "[PACKAGE] > %s %s (%s)" % (package_data["name"], package_data["version"], package_data["author"])

        print ""
