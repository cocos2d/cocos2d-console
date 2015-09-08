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
import subprocess
from MultiLanguage import MultiLanguage

class CCPluginPackage(cocos.CCPlugin):
    @staticmethod
    def plugin_name():
        return "package"

    @staticmethod
    def brief_description():
        return MultiLanguage.get_string('PACKAGE_BRIEF')

    def parse_args(self, argv):
        return {"command": argv[0]}

    def run(self, argv, dependencies):
        cmd ='sdkbox ' + ' '.join(argv)
        self._run_cmd(cmd)

    def _run_cmd(self, command, cwd=None):
        # cocos.CMDRunner.run_cmd(command, False, cwd=cwd)
        subprocess.call(command, shell=True, cwd=cwd)

    def print_help(self):
            print(MultiLanguage.get_string('PACKAGE_HELP'))
