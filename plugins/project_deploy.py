#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos "install" plugin
#
# Copyright 2013 (C) Luis Parravicini
#
# License: MIT
# ----------------------------------------------------------------------------
'''
"install" plugin for cocos command line tool
'''

__docformat__ = 'restructuredtext'

import sys
import os
import json
import inspect
from xml.dom import minidom
import shutil
import cocos


def copy_files_in_dir(src, dst):

    for item in os.listdir(src):
        path = os.path.join(src, item)
        if os.path.isfile(path):
            shutil.copy(path, dst)
        if os.path.isdir(path):
            new_dst = os.path.join(dst, item)
            os.mkdir(new_dst)
            copy_files_in_dir(path, new_dst)

def copy_dir_into_dir(src, dst):
    normpath = os.path.normpath(src)
    dir_to_create = normpath[normpath.rfind(os.sep)+1:]
    dst_path = os.path.join(dst, dir_to_create)
    if os.path.isdir(dst_path):
        shutil.rmtree(dst_path)
    shutil.copytree(src, dst_path, True)

class CCPluginDeploy(cocos.CCPlugin):
    """
    Install a project
    """

    @staticmethod
    def plugin_name():
      return "deploy"

    @staticmethod
    def brief_description():
        return "Depoly a project to the target"

    def _add_custom_options(self, parser):
        parser.add_argument("-m", "--mode", dest="mode", default='debug',
                          help="Set the deploy mode, should be debug|release, default is debug.")

    def _check_custom_options(self, args):

        if args.mode != 'release':
            args.mode = 'debug'

        self._mode = 'debug'
        if 'release' == args.mode:
            self._mode = args.mode

    def _is_debug_mode(self):
        return self._mode == 'debug'

    def _xml_attr(self, dir, file_name, node_name, attr):
        doc = minidom.parse(os.path.join(dir, file_name))
        return doc.getElementsByTagName(node_name)[0].getAttribute(attr)


    def deploy_android(self):
        if not self._platforms.is_android_active():
            return

        project_dir = self._project.get_project_dir()
        android_project_dir = self._platforms.project_path()

        cocos.Logging.info("installing on device")
        self.package = self._xml_attr(android_project_dir, 'AndroidManifest.xml', 'manifest', 'package')
        activity_name = self._xml_attr(android_project_dir, 'AndroidManifest.xml', 'activity', 'android:name')
        if activity_name.startswith('.'):
            self.activity = self.package + activity_name
        else:
            self.activity = activity_name

        project_name = self._xml_attr(android_project_dir, 'build.xml', 'project', 'name')

        if self._mode == 'release':
           apk_name = '%s-%s-unsigned.apk' % (project_name, self._mode)
        else:
           apk_name = '%s-%s-unaligned.apk' % (project_name, self._mode)

        if self._project._is_script_project():
            apk_dir = os.path.join(project_dir, 'runtime', 'android')
        else:
            apk_dir = os.path.join(project_dir, 'bin', self._mode, 'android')

        apk_path = os.path.join(apk_dir, apk_name)

        #TODO detect if the application is installed before running this
        adb_uninstall = "adb uninstall %s" % self.package
        self._run_cmd(adb_uninstall)
        adb_install = "adb install \"%s\"" % apk_path
        self._run_cmd(adb_install)

    def deploy_ios(self):
        if not self._platforms.is_ios_active():
            return
        project_dir = self._project.get_project_dir()

        if self._project._is_script_project():
            app_dir = os.path.join(project_dir, 'runtime', 'ios')
        else:
            app_dir = os.path.join(project_dir, 'bin', self._mode, 'ios')

        app_name = self.get_filename_by_extention(".app", app_dir)

        if not app_name:
            message = "app not found in %s " % app_dir
            raise cocos.CCPluginError(message)

        # not really deploy to somewhere, only remember the app path
        self._iosapp_path = os.path.join(app_dir, app_name)

    def deploy_mac(self):
        if not self._platforms.is_mac_active():
            return
        project_dir = self._project.get_project_dir()

        if self._project._is_script_project():
            app_dir = os.path.join(project_dir, 'runtime', 'mac')
        else:
            app_dir = os.path.join(project_dir, 'bin', self._mode, 'mac')

        app_name = self.get_filename_by_extention(".app", app_dir)
        if not app_name:
            message = "app not found in %s " % app_dir
            raise cocos.CCPluginError(message)

        # not really deploy to somewhere, only remember the app path
        self._macapp_path = os.path.join(app_dir, app_name)

    def deploy_web(self):
        if not self._platforms.is_web_active():
            return

        project_dir = self._platforms.project_path()

        if self._is_debug_mode():
            self.run_root = project_dir
        else:
            self.run_root = os.path.join(project_dir, 'publish', 'html5')

        cocos.Logging.info("deploy to %s" % self.run_root)

        pass

    def deploy_win32(self):
        if not self._platforms.is_win32_active():
            return
        project_dir = self._project.get_project_dir()
        win32_projectdir = self._platforms.project_path()
        build_mode = self._mode
        if self._project._is_script_project():
            output_dir = os.path.join(project_dir, 'runtime', 'win32')
        else:
            output_dir = os.path.join(project_dir, 'bin', build_mode, 'win32')

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        self.run_root = output_dir;

        # copy files
        debug_folder_name = "Debug.win32"
        debug_folder_path = os.path.join(win32_projectdir, debug_folder_name)
        if not os.path.isdir(debug_folder_path):
            message = "Can not find the %s" % debug_folder_name
            raise cocos.CCPluginError(message)

        # copy dll & exe
        files = os.listdir(debug_folder_path)
        for filename in files:
            name, ext = os.path.splitext(filename)
            if ext == '.dll' or ext == '.exe':
                file_path = os.path.join(debug_folder_path, filename)
                print ("Copying %s" % filename)
                shutil.copy(file_path, output_dir)

        # copy lua files & res
        build_cfg = os.path.join(win32_projectdir, 'build-cfg.json')
        if not os.path.exists(build_cfg):
            message = "%s not found" % build_cfg
            raise cocos.CCPluginError(message)
        f = open(build_cfg)
        data = json.load(f)
        fileList = data["copy_files"]
        for res in fileList:
           resource = os.path.join(win32_projectdir, res)
           if os.path.isdir(resource):
               if res.endswith('/'):
                   copy_files_in_dir(resource, output_dir)
               else:
                   copy_dir_into_dir(resource, output_dir)
           elif os.path.isfile(resource):
               shutil.copy(resource, output_dir)

        cocos.Logging.info("Deploy succeeded")

    def get_filename_by_extention(self, ext, path):
        filelist = os.listdir(path)

        for fname in filelist:
            name, extention = os.path.splitext(fname)
            if extention == ext:
                return  fname
        return None


    def run(self, argv, dependencies):
        self.parse_args(argv)
        cocos.Logging.info('Deploying mode: %s' % self._mode)
        self.deploy_android()
        self.deploy_ios()
        self.deploy_mac()
        self.deploy_web()
        self.deploy_win32()

