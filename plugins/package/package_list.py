
import cocos

from helper import PackageHelper

class PackageList(cocos.CCPlugin):
    @staticmethod
    def plugin_name():
        return "list"

    @staticmethod
    def brief_description():
        return "List all installed packages"

    def run(self, argv):
        packages = PackageHelper.get_installed_packages()
        keys = packages.keys()
        if len(keys) == 0:
            print "[PACKAGE] not found installed packages"
            return

        print "[PACKAGE] installed packages:"
        keys.sort()
        for k in keys:
            package_data = PackageHelper.get_installed_package_data(packages[k]["name"])
            print "[PACKAGE] > %s %s (%s)" % (package_data["name"], package_data["version"], package_data["author"])

        print ""
