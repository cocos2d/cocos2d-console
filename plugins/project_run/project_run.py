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
    Compiles a project and runs it on the target
    """

    @staticmethod
    def depends_on():
        return ('deploy',)

    @staticmethod
    def plugin_name():
      return "run"

    @staticmethod
    def brief_description():
        return "Compiles & deploy project and then runs it on the target"

    def _add_custom_options(self, parser):
        parser.add_argument("-m", "--mode", dest="mode", default='debug',
                          help="Set the run mode, should be debug|release, default is debug.")

        group = parser.add_argument_group("web project arguments")
        group.add_argument("port", metavar="SERVER_PORT", nargs='?', default='8000',
                          help="Set the port of the local web server, defualt is 8000")

    def _check_custom_options(self, args):
        self._port = args.port
        self._mode = args.mode


    def run_ios_sim(self, dependencies):
        if not self._platforms.is_ios_active():
            return

        deploy_dep = dependencies['deploy']
        iossim_exe_path = os.path.join(os.path.dirname(__file__), 'bin', 'ios-sim')
        launch_sim = "%s launch %s &" % (iossim_exe_path, deploy_dep._iosapp_path)
        self._run_cmd(launch_sim)

    def run_mac(self, dependencies):
        if not self._platforms.is_mac_active():
            return

        deploy_dep = dependencies['deploy']
        launch_macapp = 'open %s &' % deploy_dep._macapp_path
        self._run_cmd(launch_macapp)

    def run_android_device(self, dependencies):
        if not self._platforms.is_android_active():
            return

        sdk_root = cocos.check_environment_variable('ANDROID_SDK_ROOT')
        adb_path = os.path.join(sdk_root, 'platform-tools', 'adb')
        deploy_dep = dependencies['deploy']
        startapp = "%s shell am start -n \"%s/%s\"" % (adb_path, deploy_dep.package, deploy_dep.activity)
        self._run_cmd(startapp)
        pass

    def run_web(self, dependencies):
        if not self._platforms.is_web_active():
            return

        from SimpleHTTPServer import SimpleHTTPRequestHandler
        HandlerClass = SimpleHTTPRequestHandler
        ServerClass  = BaseHTTPServer.HTTPServer
        Protocol     = "HTTP/1.0"

        port = int(self._port)
        server_address = ('127.0.0.1', port)

        HandlerClass.protocol_version = Protocol
        httpd = ServerClass(server_address, HandlerClass)

        sa = httpd.socket.getsockname()

        from threading import Thread
        deploy_dep = dependencies['deploy']
        sub_url = deploy_dep.sub_url
        url = 'http://127.0.0.1:%s%s' % (port, sub_url)
        thread = Thread(target = open_webbrowser, args = (url,))
        thread.start()

        run_root = deploy_dep.run_root
        with cocos.pushd(run_root):
            cocos.Logging.info("Serving HTTP on %s, port %s ..." % (sa[0], sa[1]))
            httpd.serve_forever()

    def run_win32(self, dependencies):
        if not self._platforms.is_win32_active():
            return

        deploy_dep = dependencies['deploy']
        run_root = deploy_dep.run_root
        exe = deploy_dep.project_name
        with cocos.pushd(run_root):
            self._run_cmd(os.path.join(run_root, exe))

    def run_linux(self, dependencies):
        if not self._platforms.is_linux_active():
            return

        deploy_dep = dependencies['deploy']
        run_root = deploy_dep.run_root
        exe = deploy_dep.project_name
        with cocos.pushd(run_root):
            self._run_cmd(os.path.join(run_root, exe))



    def run(self, argv, dependencies):
        self.parse_args(argv)
        cocos.Logging.info("starting application")
        self.run_android_device(dependencies)
        self.run_ios_sim(dependencies)
        self.run_mac(dependencies)
        self.run_web(dependencies)
        self.run_win32(dependencies)
        self.run_linux(dependencies)

