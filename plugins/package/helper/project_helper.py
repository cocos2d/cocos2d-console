
import os
import os.path

import cocos

from functions import *
from package_helper import *
from zip_unpacker import ZipUnpacker
from add_framework_helper import AddFrameworkHelper
from remove_framework_helper import RemoveFrameworkHelper
from create_framework_helper import CreateFrameworkHelper
from set_framework_helper import SetFrameworkHelper

def get_engine_of_project(project):
    ver_str = None
    x_ver_file = os.path.join(project["path"], 'frameworks/cocos2d-x/cocos/cocos2d.cpp')
    pattern = r".*return[ \t]+\"cocos2d-x (.*)\";"

    f = open(x_ver_file)
    for line in f.readlines():
        match = re.match(pattern, line)
        if match:
            ver_str = match.group(1)
            break
    f.close()

    return ver_str

class ProjectHelper:
    SUPPORTED_PLATFORMS = ("proj.android", "proj.ios_mac", "proj.win32")
    PACKAGES_DIRNAME = "packages"
    PACKAGE_INFO_FILE = "package.json"

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
            message = cocos.MultiLanguage.get_string('PACKAGE_ERROR_WRONG_DIR')
            raise cocos.CCPluginError(message)

        for platform in cls.SUPPORTED_PLATFORMS:
            path = project["path"] + os.sep + prefix + platform
            if os.path.exists(path):
                project[platform] = path

        project["packages_dir"] = project["path"] + os.sep + cls.PACKAGES_DIRNAME
        return project

    @classmethod
    def get_added_packages(cls, project):
        packages_dir = project["packages_dir"]
        if not os.path.isdir(packages_dir):
            return

        packages = []
        dirs = os.listdir(packages_dir)
        for dir in dirs:
            dir_path = packages_dir + os.sep + dir
            if not os.path.isdir(dir_path):
                continue
            info_file = dir_path + os.sep + cls.PACKAGE_INFO_FILE
            if not os.path.isfile(info_file):
                continue
            import json
            f = open(info_file, "rb")
            package_info = json.load(f)
            f.close()
            package_info["dir_path"] = dir_path
            packages.append(package_info)

        return packages

    @classmethod
    def show_project_info(cls, project):
        print cocos.MultiLanguage.get_string('PACKAGE_PROJ_PATH_FMT') % project["path"]
        print cocos.MultiLanguage.get_string('PACKAGE_PROJ_TYPE_FMT') % project["type"]

    @classmethod
    def add_framework(cls, project, package_name):
        package_data = PackageHelper.get_installed_package_data(package_name)
        if package_data is None:
            print cocos.MultiLanguage.get_string('PACKAGE_NOT_FOUND_PKG_FMT') % package_name
            return

        cls.show_project_info(project)
        print cocos.MultiLanguage.get_string('PACKAGE_PKG_ADD_FMT') %\
              (package_data["name"], package_data["version"], package_data["author"])

        # unpacking files
        ensure_directory(project["packages_dir"])
        unpacker = ZipUnpacker(PackageHelper.get_installed_package_zip_path(package_data))
        unpacker.unpack(project["packages_dir"])

        # execute install.json
        install_helper = AddFrameworkHelper(project, package_data)
        install_helper.run()

    @classmethod
    def remove_framework(cls, project, package_name):
        cls.show_project_info(project)
        packages = cls.get_added_packages(project)
        if packages is None:
            print cocos.MultiLanguage.get_string('PACKAGE_NO_PKG_FOUND')
            return

        package_data = PackageHelper.get_installed_package_data(package_name)
        if package_data is None:
            print "[PACKAGE] not found package '%s'" % package_name
            return

        for package in packages:
            dir = package["dir_path"]
            if package["name"] == package_name:
                print cocos.MultiLanguage.get_string('PACKAGE_PKG_REMOVE_FMT') % dir
                uninstall_helper = RemoveFrameworkHelper(project, dir)
                uninstall_helper.run()
                print "[PROJECT] > Remove OK"

    @classmethod
    def update_framework(cls, project, package_name):
        cls.show_project_info(project)
        packages = cls.get_added_packages(project)
        if packages is None:
            print "[PROJECT] > Not found any packages."
            return

        engine = get_engine_of_project(project)
        if engine is None:
            print "[PROJECT] > Unknow version of engine."
            return

        newest_version = PackageHelper.get_installed_package_newest_version(package_name, engine)
        if newest_version is None:
            print "[PACKAGE] not found package '%s'" % package_name
            return
        package_data = PackageHelper.get_installed_package_data(package_name, newest_version)
        if package_data is None:
            print "[PACKAGE] not found package '%s'" % package_name
            return

        for package in packages:
            dir = package["dir_path"]
            if package["name"] == package_name:
                if compare_version(newest_version, package["version"]) < 1:
                    print "[PROJECT] > The package '%s' is newest version." % package_name
                    return
                cls.remove_framework(project, package_name)
                cls.add_framework(project, package_name)
                print "[PROJECT] > Update OK"
                return

        print "[PROJECT] > Not found package '%s'." % package_name

    @classmethod
    def create_framework(cls, project, package_name):
        cls.show_project_info(project)

        ensure_directory(project["packages_dir"])
        create_helper = CreateFrameworkHelper(project, package_name)
        create_helper.run()

    @classmethod
    def set_framework(cls, project, package_name, version):
        cls.show_project_info(project)
        packages_dir = project["packages_dir"]
        if not os.path.isdir(packages_dir):
            print cocos.MultiLanguage.get_string('PACKAGE_NO_PKG_FOUND')
            return

        set_helper = SetFrameworkHelper(project, package_name, version)
        set_helper.run()
