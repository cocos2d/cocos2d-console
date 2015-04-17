
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
        parser.add_argument('-v', '--version', default='all', help="Specifies the package version")
        return parser.parse_args(argv)

    def run(self, argv):
        args = self.parse_args(argv)
        name = args.name
        version = args.version
        package_data = PackageHelper.query_package_data(name, version)
        if package_data is None:
            print "[PACKAGE] can't find package '%s', version='%s'" % (name, version)
            return

        if isinstance(package_data, list):
            for data in package_data:
                self.show_info(name, data)
                return

        if package_data.has_key('err'):
            print "[PACKAGE] can't find package '%s', version='%s'" % (name, version)
            return
            
        self.show_info(name, package_data)

    def show_info(self, name, package_data):
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
