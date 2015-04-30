
import cocos

from helper import PackageHelper

class PackageList(cocos.CCPlugin):
    @staticmethod
    def plugin_name():
        return "list"

    @staticmethod
    def brief_description():
        return cocos.MultiLanguage.get_string('PACKAGE_LIST_BRIEF')

    def run(self, argv):
        packages = PackageHelper.get_installed_packages()
        keys = packages.keys()
        if len(keys) == 0:
            print cocos.MultiLanguage.get_string('PACKAGE_LIST_NOT_FOUND')
            return

        print cocos.MultiLanguage.get_string('PACKAGE_LIST_TIP')
        keys.sort()
        for k in keys:
            package_data = PackageHelper.get_installed_package_data(packages[k]["name"])
            print cocos.MultiLanguage.get_string('PACKAGE_ITEM_FMT')\
                  % (package_data["name"], package_data["version"], package_data["author"])

        print ""
