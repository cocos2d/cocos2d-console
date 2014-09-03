#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos2d "dgate" plugin
#
# Copyright 2014 (C) TAKUMA Kei
#
# License: MIT
# ----------------------------------------------------------------------------

"""
"Deploygate" plugin for cocos command line tool
"""

__docformat__ = 'restructuredtext'

import cocos

class CCPluginDgate(cocos.CCPlugin):
    """
    Push a iOS/Android app to http://deploygate.com
    """

    @staticmethod
    def depends_on():
        return ('compile',)

    @staticmethod
    def plugin_name():
        return "dgate"

    @staticmethod
    def brief_description():
        return "Push a iOS/Android app to http://deploygate.com"

    def _add_custom_options(self, parser):
        parser.add_argument("-m", "--mode", dest="mode", default="debug",
                help="Set the compile mode, should be debug|release, default is debug.")
        group = parser.add_argument_group("deploygate Options")
        parser.add_argument("--dgate-owner", dest="dgate_owner", help="deploygate owner/group name")
        parser.add_argument("--dgate-message", dest="dgate_message", help="deploygate message")

    def _check_custom_options(self, args):
        if args.mode != 'release':
            args.mode = 'debug'

        self._mode = 'debug'
        if 'release' == args.mode:
            self._mode = args.mode

        self._dgate_message = args.dgate_message
        self._dgate_owner = args.dgate_owner

    def run_android(self, dependencies):
        if not self._platforms.is_android_active():
            return

        compile_dep = dependencies['compile']
        self.run_dgate_push(compile_dep.apk_path)

        cocos.Logging.info("succeeded.")

    def run_ios(self, dependencies):
        if not self._platforms.is_ios_active():
            return

        compile_dep = dependencies['compile']

        if compile_dep.use_sdk != 'iphoneos':
            cocos.Logging.warning("The generated app is for simulator.")
            return

        self.run_dgate_push(compile_dep._iosipa_path)

        cocos.Logging.info("succeeded.")

    def run_dgate_push(self, pathname):
        owner = self._dgate_owner
        message = self._dgate_message
        command = ''.join([
            "dgate push",
            " \"%s\"" % owner if owner is not None else "",
            " \"%s\"" % pathname,
            " -m \"%s\"" % message if message is not None else ""
            ])
        self._run_cmd(command)

    def run(self, argv, dependencies):
        self.parse_args(argv)
        cocos.Logging.info('Building mode: %s' % self._mode)
        if self._dgate_owner is not None:
            cocos.Logging.info('dgate owner/group: %s' % self._dgate_owner)
        cocos.Logging.info('dgate message: %s' % self._dgate_message)
        self.run_android(dependencies)
        self.run_ios(dependencies)
