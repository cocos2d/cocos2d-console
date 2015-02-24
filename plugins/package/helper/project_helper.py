
import os
import os.path

import cocos

from functions import *
from package_helper import PackageHelper
from zip_unpacker import ZipUnpacker
from add_framework_helper import AddFrameworkHelper
from remove_framework_helper import RemoveFrameworkHelper
from create_framework_helper import CreateFrameworkHelper
from set_framework_helper import SetFrameworkHelper

class ProjectHelper:
    SUPPORTED_PLATFORMS = ("proj.android", "proj.ios_mac", "proj.win32")
    PACKAGES_DIRNAME = "packages"

    @classmethod
    def get_current_project(cls):
        cwd = os.path.realpath(os.getcwd())
        prefix = cwd

        project = {}
        project["path"] = prefix

        project["classes_dir"] = "Classes"
        if os.path.exists(prefix + os.sep + project["classes_dir"]):
            project["type"] = "cpp"
            prefix = ""
        else:
            prefix = "frameworks" + os.sep + "runtime-src" + os.sep
            project["classes_dir"] = prefix + os.sep + "Classes"
            if os.path.exists(cwd + os.sep + project["classes_dir"]):
                project["type"] = "script"

        if not "type" in project:
            message = "Fatal: you must run `cocos add-framework` at project root dir"
            raise cocos.CCPluginError(message)

        for platform in cls.SUPPORTED_PLATFORMS:
            path = project["path"] + os.sep + prefix + platform
            if os.path.exists(path):
                project[platform] = path

        project["packages_dir"] = project["path"] + os.sep + cls.PACKAGES_DIRNAME
        return project

    @classmethod
    def add_framework(cls, project, package_name):
        package_data = PackageHelper.get_installed_package_data(package_name)
        if package_data is None:
            print "[PACKAGE] not found package '%s'" % package_name
            return

        print "[PROJECT] > project path: %s" % project["path"]
        print "[PROJECT] > project type: %s" % project["type"]
        print "[PROJECT] > Adding '%s %s (%s)' ..." % (
            package_data["name"], package_data["version"], package_data["author"])

        # unpacking files
        ensure_directory(project["packages_dir"])
        unpacker = ZipUnpacker(PackageHelper.get_installed_package_zip_path(package_data))
        unpacker.unpack(project["packages_dir"])

        # execute install.json
        install_helper = AddFrameworkHelper(project, package_data)
        install_helper.run()

    @classmethod
    def remove_framework(cls, project, package_name):
        print "[PROJECT] > project path: %s" % project["path"]
        print "[PROJECT] > project type: %s" % project["type"]
        packages_dir = project["packages_dir"]
        if not os.path.isdir(packages_dir):
            print "[PROJECT] > Not found any packages."
            return

        name_len = len(package_name)
        dirs = os.listdir(packages_dir)
        for dir in dirs:
            dir_path = packages_dir + os.sep + dir
            if not os.path.isdir(dir_path):
                continue

            if dir == package_name:
                print "[PROJECT] > Removing '%s' ..." % dir
                uninstall_helper = RemoveFrameworkHelper(project, dir_path)
                uninstall_helper.run()
            elif dir[0:name_len+1] == package_name + '-':
                print "[PROJECT] > Removing '%s' ..." % dir
                uninstall_helper = RemoveFrameworkHelper(project, dir_path)
                uninstall_helper.run()

    @classmethod
    def create_framework(cls, project, package_name):
        print "[PROJECT] > project path: %s" % project["path"]
        print "[PROJECT] > project type: %s" % project["type"]

        ensure_directory(project["packages_dir"])
        create_helper = CreateFrameworkHelper(project, package_name)
        create_helper.run()

    @classmethod
    def set_framework(cls, project, package_name, version):
        print "[PROJECT] > project path: %s" % project["path"]
        print "[PROJECT] > project type: %s" % project["type"]
        packages_dir = project["packages_dir"]
        if not os.path.isdir(packages_dir):
            print "[PROJECT] > Not found any packages."
            return

        set_helper = SetFrameworkHelper(project, package_name, version)
        set_helper.run()
