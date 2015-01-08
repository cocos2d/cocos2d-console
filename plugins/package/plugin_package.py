# ----------------------------------------------------------------------------
# cocos "package" plugin
#
# Copyright 2014 (C) cocos2d-x.org
#
# License: MIT
# ----------------------------------------------------------------------------
'''
"package" plugins
'''

__docformat__ = 'restructuredtext'

import cocos


class CCPluginPackage(cocos.CCPlugin):
    @staticmethod
    def plugin_name():
        return "package"

    @staticmethod
    def brief_description():
        return "Do a package operation"

    def parse_args(self, argv):
        if len(argv) < 1:
            print "usage: cocos package [-h] COMMAND arg [arg ...]"
            print "cocos package: error: too few arguments"
            return None

        return {"command": argv[0]}

    def run(self, argv, dependencies):
        args = self.parse_args(argv)
        if args is None:
            return

        command = args["command"]

        if command == "search":
            from package_search import FrameworkAdd
            CommandClass = FrameworkAdd
        elif command == "info":
            from package_info import PackageInfo
            CommandClass = PackageInfo
        elif command == "install":
            from package_install import PackageInstall
            CommandClass = PackageInstall
        elif command == "list":
            from package_list import PackageList
            CommandClass = PackageList
        else:
            message = "Fatal: invalid command 'cocos package %s'" % command
            raise cocos.CCPluginError(message)

        commandObject = CommandClass()
        commandObject.run(argv[1:])
