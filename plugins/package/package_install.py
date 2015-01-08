
import cocos

from helper import PackageHelper

class PackageInstall(cocos.CCPlugin):
    @staticmethod
    def plugin_name():
        return "install"

    @staticmethod
    def brief_description():
        return "Install a package"

    # parse arguments
    def parse_args(self, argv):
        from argparse import ArgumentParser
        parser = ArgumentParser(prog="cocos package %s" % self.__class__.plugin_name(),
                                description=self.__class__.brief_description())
        parser.add_argument("name", metavar="PACKAGE_NAME", help="Specifies the package name")
        parser.add_argument("-f", action="store_true", dest="force", help="Ignore exists file, force to download zip from remote repo")
        return parser.parse_args(argv)

    def run(self, argv):
        args = self.parse_args(argv)
        name = args.name
        force = args.force

        package_data = PackageHelper.query_package_data(name)
        if package_data is False:
            message = "Fatal: not found package '%s'" % name
            raise cocos.CCPluginError(message)

        PackageHelper.download_package_zip(package_data, force)
        PackageHelper.add_package(package_data)

        print ""
