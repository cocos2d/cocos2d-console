
import time

from helper import PackageHelper

import cocos

class PackageInfo(object):
    @staticmethod
    def plugin_name():
        return "info"

    @staticmethod
    def brief_description():
        return cocos.MultiLanguage.get_string('PACKAGE_INFO_BRIEF')

    def parse_args(self, argv):
        from argparse import ArgumentParser

        parser = ArgumentParser(prog="cocos package %s" % self.__class__.plugin_name(),
                                description=self.__class__.brief_description())
        parser.add_argument("name", metavar="NAME", help=cocos.MultiLanguage.get_string('PACKAGE_INFO_ARG_NAME'))
        return parser.parse_args(argv)

    def run(self, argv):
        args = self.parse_args(argv)
        name = args.name
        package_data = PackageHelper.query_package_data(name)
        if package_data is None:
            print cocos.MultiLanguage.get_string('PACKAGE_INFO_ERROR_NO_PKG_FMT') % name
            return

        print cocos.MultiLanguage.get_string('PACKAGE_INFO_PKG_FMT') % \
              (name, package_data["name"], package_data["version"],
               time.strftime("%Y-%m-%d %H:%I:%S", time.gmtime(int(package_data["filetime"]))),
               package_data["author"], (int(package_data["filesize"]) / 1024),
               package_data["description"])
