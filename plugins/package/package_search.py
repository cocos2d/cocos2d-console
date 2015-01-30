
from helper import PackageHelper

class FrameworkAdd(object):
    @staticmethod
    def plugin_name():
        return "search"

    @staticmethod
    def brief_description():
        return "Search packages by name"

    def parse_args(self, argv):
        from argparse import ArgumentParser
        parser = ArgumentParser(
            prog="cocos package %s" % self.__class__.plugin_name(),
            description=self.__class__.brief_description())
        parser.add_argument("keyword", metavar="PACKAGE_NAME", help="Specifies the package name")
        return parser.parse_args(argv)

    def run(self, argv):
        args = self.parse_args(argv)
        keyword = args.keyword
        packages = PackageHelper.search_keyword(keyword)
        if packages is None:
            print "[PACKAGE] can't find package '%s'" % keyword
            return

        keys = packages.keys()
        print "[PACKAGE] all the packages matching '%s'" % keyword
        keys.sort()
        for k in keys:
            package_data = packages[k]
            print "[PACKAGE] > %s %s (%s)" % (package_data["name"], package_data["version"], package_data["author"])

        print ""
