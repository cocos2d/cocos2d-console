
import time

from helper import PackageHelper


class PackageInfo(object):
    @staticmethod
    def plugin_name():
        return "info"

    @staticmethod
    def brief_description():
        return "Search packages by keywords in remote repo"

    def parse_args(self, argv):
        from argparse import ArgumentParser

        parser = ArgumentParser(prog="cocos package %s" % self.__class__.plugin_name(),
                                description=self.__class__.brief_description())
        parser.add_argument("name", metavar="NAME", help="Specifies the package name")
        return parser.parse_args(argv)

    def run(self, argv):
        args = self.parse_args(argv)
        name = args.name
        package_data = PackageHelper.query_package_data(name)
        if package_data is None:
            print "[PACKAGE] can't find package '%s'" % name
            return

        print "[PACKAGE] > getting info for package '%s' ... ok" % name
        print ""
        print "name: %s" % package_data["name"]
        print "version: %s" % package_data["version"]
        print "updated: %s" % time.strftime("%Y-%m-%d %H:%I:%S", time.gmtime(int(package_data["filetime"])))
        print "author: %s" % package_data["author"]
        print "size: %d KB" % (int(package_data["filesize"]) / 1024)
        print ""
        print package_data["description"]
        print ""
