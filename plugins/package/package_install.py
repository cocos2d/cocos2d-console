
import cocos

from helper import PackageHelper

class PackageInstall(cocos.CCPlugin):
    @staticmethod
    def plugin_name():
        return "install"

    @staticmethod
    def brief_description():
        return cocos.MultiLanguage.get_string('PACKAGE_INSTALL_BRIEF')

    # parse arguments
    def parse_args(self, argv):
        from argparse import ArgumentParser
        parser = ArgumentParser(prog="cocos package %s" % self.__class__.plugin_name(),
                                description=self.__class__.brief_description())
        parser.add_argument("name", metavar="PACKAGE_NAME",
                            help=cocos.MultiLanguage.get_string('PACKAGE_INSTALL_ARG_NAME'))
        parser.add_argument("-f", action="store_true", dest="force",
                            help=cocos.MultiLanguage.get_string('PACKAGE_INSTALL_ARG_FORCE'))
        parser.add_argument('-v', '--version', default='all',
                            help=cocos.MultiLanguage.get_string('PACKAGE_INFO_ARG_VERSION'))
        return parser.parse_args(argv)

    def run(self, argv):
        args = self.parse_args(argv)
        name = args.name
        version = args.version
        force = args.force

        package_data = PackageHelper.query_package_data(name, version)
        if package_data is None:
            message = cocos.MultiLanguage.get_string('PACKAGE_INSTALL_ERROR_NO_PKG_FMT') % (name, version)
            raise cocos.CCPluginError(message)

        if isinstance(package_data, list):
            for data in package_data:
                self.download(force, data)
                return

        if package_data.has_key('err'):
            message = cocos.MultiLanguage.get_string('PACKAGE_INSTALL_ERROR_NO_PKG_FMT') % (name, version)
            raise cocos.CCPluginError(message)
            
        self.download(force, package_data)

    def download(self, force, package_data):
        PackageHelper.download_package_zip(package_data, force)
        PackageHelper.add_package(package_data)

        print ""
