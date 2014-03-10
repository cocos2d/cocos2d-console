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
import BaseHTTPServer
import webbrowser
import threading


def open_webbrowser(url):
        threading.Event().wait(1)
        webbrowser.open_new(url)


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

    def _add_custom_options(self, parser):
        from optparse import OptionGroup

        category = self.plugin_category()
        name = self.plugin_name()
        usage = "\n\t%%prog %s %s" \
                "\n\t%%prog %s %s 8080" \
                "\n\t%%prog %s %s -p <platform> [-s src_dir][-m <debug|release>]" \
                "\nSample:" \
                "\n\t%%prog %s %s -p android" % (category, name, category, name, category, name, category, name)

        parser.set_usage(usage)

    def _check_custom_options(self, options, args):
        self._args = args;


    def run_ios_sim(self, dependencies):
        if not self._platforms.is_ios_active():
            return

        deploy_dep = dependencies['project_deploy']
        iossim_exe_path = os.path.join(os.path.dirname(__file__), 'bin', 'ios-sim')
        launch_sim = "%s launch %s &" % (iossim_exe_path, deploy_dep._iosapp_path)
        self._run_cmd(launch_sim)

    def run_mac(self, dependencies):
        if not self._platforms.is_mac_active():
            return

        deploy_dep = dependencies['project_deploy']
        launch_macapp = 'open %s &' % deploy_dep._macapp_path
        self._run_cmd(launch_macapp)

    def run_android_device(self, dependencies):
        if not self._platforms.is_android_active():
            return

        deploy_dep = dependencies['project_deploy']
        startapp = "adb shell am start -n \"%s/%s\"" % (deploy_dep.package, deploy_dep.activity)
        self._run_cmd(startapp)
        pass

    def run_h5(self, dependencies):
        if not self._platforms.is_h5_active():
            return

        from SimpleHTTPServer import SimpleHTTPRequestHandler
        HandlerClass = SimpleHTTPRequestHandler
        ServerClass  = BaseHTTPServer.HTTPServer
        Protocol     = "HTTP/1.0"

        port = 8000
        if len(self._args) > 0:
            port = int(self._args[0])

        server_address = ('127.0.0.1', port)

        HandlerClass.protocol_version = Protocol
        httpd = ServerClass(server_address, HandlerClass)

        sa = httpd.socket.getsockname()

        from threading import Thread
        url = 'http://127.0.0.1:%s' % port
        thread = Thread(target = open_webbrowser, args = (url,))
        thread.start()

        with cocos.pushd(self._platforms.project_path()):
            cocos.Logging.info("Serving HTTP on %s, port %s ..." % (sa[0], sa[1]))
            httpd.serve_forever()


    def run(self, argv, dependencies):
        cocos.Logging.info("starting application")
        self.parse_args(argv)
        self.run_android_device(dependencies)
        self.run_ios_sim(dependencies)
        self.run_mac(dependencies)
        self.run_h5(dependencies)

