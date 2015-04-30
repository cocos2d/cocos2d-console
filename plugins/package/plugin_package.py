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
        return cocos.MultiLanguage.get_string('PACKAGE_BRIEF')

    def parse_args(self, argv):
        if len(argv) < 1:
            self.print_help()
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
        elif command == "-h":
            self.print_help()
            return
        else:
            message = cocos.MultiLanguage.get_string('PACKAGE_ERROR_INVALID_CMD_FMT') % command
            raise cocos.CCPluginError(message)

        commandObject = CommandClass()
        commandObject.run(argv[1:])

    def print_help(self):
            print(cocos.MultiLanguage.get_string('PACKAGE_HELP'))
