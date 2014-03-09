#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos "install" plugin
#
# Authr: Luis Parravicini
#
# License: MIT
# ----------------------------------------------------------------------------
'''
"run" plugin for cocos command line tool
'''

__docformat__ = 'restructuredtext'

import sys
import os
import cocos

class CCPluginRun(cocos.CCPlugin):
    """
    Compiles a project and install it on a device
    """

    @staticmethod
    def plugin_category():
      return "project"

    @staticmethod
    def depends_on():
        return ('project_compile', 'project_deploy')

    @staticmethod
    def plugin_name():
      return "run"

    @staticmethod
    def brief_description():
        return "compiles a project and install the files on a device"


    def run_ios_sim(self, argv, dependencies):
        if not self._platforms.is_ios_active():
            return

        deploy_dep = dependencies['project_deploy']
        iossim_exe_path = os.path.join(os.path.dirname(__file__), 'bin', 'ios-sim')
        launch_sim = "%s launch %s &" % (iossim_exe_path, deploy_dep._iosapp_path)
        self._run_cmd(launch_sim)

    def run_mac(self, argv,dependencies):
        if not self._platforms.is_mac_active():
            return

        deploy_dep = dependencies['project_deploy']
        launch_macapp = 'open %s &' % deploy_dep._macapp_path
        self._run_cmd(launch_macapp)

    def run_android_device(self, argv, dependencies):
        if not self._platforms.is_android_active():
            return

        deploy_dep = dependencies['project_deploy']
        startapp = "adb shell am start -n \"%s/%s\"" % (deploy_dep.package, deploy_dep.activity)
        self._run_cmd(startapp)
        pass

    def run(self, argv, dependencies):
        cocos.Logging.info("starting application")
        self.parse_args(argv)
        self.run_android_device(argv, dependencies)
        self.run_ios_sim(argv,dependencies)
        self.run_mac(argv,dependencies)
