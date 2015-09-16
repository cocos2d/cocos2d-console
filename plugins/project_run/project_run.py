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
        group.add_argument("-b", "--browser", dest="browser",
                          help="Specify the browser to open the url. Use the system default browser if not specified.")
        group.add_argument("port", metavar="SERVER_PORT", nargs='?',
                          help="Set the port of the local web server, default is 8000")
        group.add_argument("--host", dest="host", metavar="SERVER_HOST", nargs='?', default='127.0.0.1',
                          help="Set the host of the local web server, default is 127.0.0.1")

    def _check_custom_options(self, args):
        self._port = args.port
        self._mode = args.mode
        self._host = args.host
        self._browser = args.browser

    def get_ios_sim_name(self):
        # get the version of xcodebuild
        ver = cocos.get_xcode_version()

        if ver.startswith("5"):
            ret = "ios-sim-xcode5"
        else:
            ret = "ios-sim-xcode6"

        return ret

    def run_ios_sim(self, dependencies):
        if not self._platforms.is_ios_active():
            return

        deploy_dep = dependencies['deploy']
        if deploy_dep._use_sdk == 'iphoneos':
            cocos.Logging.warning("The generated app is for device. Can't run it on simulator.")
            cocos.Logging.warning("The signed app & ipa are generated in path : %s" % os.path.dirname(deploy_dep._iosapp_path))
        else:
            iossim_exe_path = os.path.join(os.path.dirname(__file__), 'bin', self.get_ios_sim_name())
            launch_sim = "%s launch \"%s\" &" % (iossim_exe_path, deploy_dep._iosapp_path)
            self._run_cmd(launch_sim)

    def run_mac(self, dependencies):
        if not self._platforms.is_mac_active():
            return

        deploy_dep = dependencies['deploy']
        launch_macapp = '\"%s/Contents/MacOS/%s\"' % (deploy_dep._macapp_path, deploy_dep.target_name)
        self._run_cmd(launch_macapp)

    def run_android_device(self, dependencies):
        if not self._platforms.is_android_active():
            return

        sdk_root = cocos.check_environment_variable('ANDROID_SDK_ROOT')
        adb_path = cocos.CMDRunner.convert_path_to_cmd(os.path.join(sdk_root, 'platform-tools', 'adb'))
        deploy_dep = dependencies['deploy']
        startapp = "%s shell am start -n \"%s/%s\"" % (adb_path, deploy_dep.package, deploy_dep.activity)
        self._run_cmd(startapp)
        pass

    def open_webbrowser(self, url):
        if self._browser is None:
            threading.Event().wait(1)
            webbrowser.open_new(url)
        else:
            if cocos.os_is_mac():
                url_cmd = "open -a \"%s\" \"%s\"" % (self._browser, url)
            else:
                url_cmd = "\"%s\" %s" % (self._browser, url)
            self._run_cmd(url_cmd)

    def run_web(self, dependencies):
        if not self._platforms.is_web_active():
            return

        from SimpleHTTPServer import SimpleHTTPRequestHandler
        HandlerClass = SimpleHTTPRequestHandler
        ServerClass  = BaseHTTPServer.HTTPServer
        Protocol     = "HTTP/1.0"
        HandlerClass.protocol_version = Protocol

        host = self._host
        if self._port is None:
            port = 8000
            port_max_add = 2000
        else:
            port = int(self._port)
            port_max_add = 0

        deploy_dep = dependencies['deploy']
        run_root = deploy_dep.run_root

        i = 0
        httpd = None
        while (i <= port_max_add):
            port += i
            i += 1
            server_address = (host, port)
            try:
                cocos.Logging.info("Try start server on {0}:{1}".format(host, port))
                httpd = ServerClass(server_address, HandlerClass)
            except Exception as e:
                httpd = None
                cocos.Logging.warning("Start server {0}:{1} error : {2}".format(host, port, e))

            if httpd is not None:
                break

        if httpd is None:
            raise cocos.CCPluginError("Start server failed.")

        from threading import Thread
        sub_url = deploy_dep.sub_url
        url = 'http://%s:%s%s' % (host, port, sub_url)
        thread = Thread(target = self.open_webbrowser, args = (url,))
        thread.start()

        sa = httpd.socket.getsockname()
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

    def run_wp8(self, dependencies):
        if not self._platforms.is_wp8_active():
            return

        deploy_dep = dependencies['deploy']
        xap_path = deploy_dep.xap_path
        deploy_tool = deploy_dep.deploy_tool
        cmd = '"%s" /installlaunch "%s" /targetDevice:xd' % (deploy_tool, xap_path)
        self._run_cmd(cmd)

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
        self.run_wp8(dependencies)

