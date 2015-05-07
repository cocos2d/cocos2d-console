# ----------------------------------------------------------------------------
# cocos "package" plugin
#
# Copyright 2014 (C) cocos2d-x.org
#
# License: MIT
# ----------------------------------------------------------------------------
'''
"framework" plugins
'''

__docformat__ = 'restructuredtext'

import cocos


class CCPluginFramework(cocos.CCPlugin):
    @staticmethod
    def plugin_name():
        return "framework"

    @staticmethod
    def brief_description():
        return cocos.MultiLanguage.get_string('FRAMEWORK_BRIEF')

    def parse_args(self, argv):
        if len(argv) < 1:
            print "usage: cocos framework [-h] COMMAND arg [arg ...]"
            print cocos.MultiLanguage.get_string('FRAMEWORK_ERROR_TOO_FEW_ARGS')
            return None

        return {"command": argv[0]}

    def run(self, argv, dependencies):
        args = self.parse_args(argv)
        if args is None:
            return

        command = args["command"]

        if command == "add":
            from framework_add import FrameworkAdd
            CommandClass = FrameworkAdd
        elif command == "remove":
            from framework_remove import FrameworkRemove
            CommandClass = FrameworkRemove
        elif command == "update":
            from framework_update import FrameworkUpdate
            CommandClass = FrameworkUpdate
        elif command == "create":
            from framework_create import FrameworkCreate
            CommandClass = FrameworkCreate
        elif command == "set":
            from framework_set import FrameworkSet
            CommandClass = FrameworkSet
        else:
            message = cocos.MultiLanguage.get_string('FRAMEWORK_ERROR_INVALID_CMD_FMT') % command
            raise cocos.CCPluginError(message)

        commandObject = CommandClass()
        commandObject.run(argv[1:])
