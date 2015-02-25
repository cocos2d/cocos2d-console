
import cocos

from package.helper import ProjectHelper


class FrameworkSet(cocos.CCPlugin):
    @staticmethod
    def plugin_name():
        return "set-framework"

    @staticmethod
    def brief_description():
        return "Setts install.json for a framework"

    # parse arguments
    def parse_args(self, argv):
        from argparse import ArgumentParser

        parser = ArgumentParser(prog="cocos %s" % self.__class__.plugin_name(),
                                description=self.__class__.brief_description())
        parser.add_argument("name", metavar="NAME", help="Specifies the package name")
        return parser.parse_args(argv)

    def run(self, argv):
        args = self.parse_args(argv)
        name = args.name

        project = ProjectHelper.get_current_project()
        ProjectHelper.set_framework(project, name, "1.0")
