
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
        parser.add_argument('-v', '--version', default='all', help="Specifies the package version")
        return parser.parse_args(argv)

    def run(self, argv):
        args = self.parse_args(argv)
        name = args.name
        version = args.version
        force = args.force

        package_data = PackageHelper.query_package_data(name, version)
        if package_data is None:
            message = "Fatal: not found package '%s', version='%s'" % (name, version)
            raise cocos.CCPluginError(message)

        if isinstance(package_data, list):
            for data in package_data:
                self.download(force, data)
                return

        if package_data.has_key('err'):
            message = "Fatal: not found package '%s', version='%s'" % (name, version)
            raise cocos.CCPluginError(message)
            
        self.download(force, package_data)

    def download(self, force, package_data):
        PackageHelper.download_package_zip(package_data, force)
        PackageHelper.add_package(package_data)

        print ""
