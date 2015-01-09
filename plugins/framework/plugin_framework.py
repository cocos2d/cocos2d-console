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
        return "Do a framework operation"

    def parse_args(self, argv):
        if len(argv) < 1:
            print "usage: cocos framework [-h] COMMAND arg [arg ...]"
            print "cocos package: error: too few arguments"
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
        else:
            message = "Fatal: invalid command 'cocos framework %s'" % command
            raise cocos.CCPluginError(message)

        commandObject = CommandClass()
        commandObject.run(argv[1:])
