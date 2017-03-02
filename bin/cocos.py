#!/usr/bin/env python2
# ----------------------------------------------------------------------------
# cocos-console: command line tool manager for cocos2d-x
#
# Author: Ricardo Quesada
# Copyright 2013 (C) Zynga, Inc
#
# License: MIT
# ----------------------------------------------------------------------------
'''
Command line tool manager for cocos
'''

__docformat__ = 'restructuredtext'


# python
import sys
import os
import subprocess
from contextlib import contextmanager
import cocos_project
import shutil
import string
import ConfigParser
from collections import OrderedDict

COCOS2D_CONSOLE_VERSION = '1.5'


class Cocos2dIniParser:
    def __init__(self):
        self._cp = ConfigParser.ConfigParser(allow_no_value=True)
        self._cp.optionxform = str

        # read global config file
        self.cocos2d_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        self._cp.read(os.path.join(self.cocos2d_path, "cocos2d.ini"))

        # XXXX: override with local config ??? why ???
        self._cp.read("~/.cocos2d-js/cocos2d.ini")

    def parse_plugins(self):
        classes = {}

        for s in self._cp.sections():
            if s == 'plugins':
                for classname in self._cp.options(s):
                    plugin_class = get_class(classname)
                    category = plugin_class.plugin_category()
                    name = plugin_class.plugin_name()
                    if name is None:
                        print(
                            "Warning: plugin '%s' does not return a plugin name" % classname)
                    if len(category) == 0:
                        key = name
                    else:
                        # combine category & name as key
                        # eg. 'project_new'
                        key = category + '_' + name
                    classes[key] = plugin_class
        _check_dependencies(classes)
        return classes

    def _sanitize_path(self, path):
        if len(path) == 0:
            return None
        path = os.path.expanduser(path)
        path = os.path.abspath(os.path.join(self.cocos2d_path, path))
        if not os.path.isdir(path):
            Logging.warning("Warning: Invalid directory defined in cocos2d.ini: %s" % path)
            return None
        return path

    def get_plugins_path(self):
        path = self._cp.get('paths', 'plugins')

        if not os.path.isabs(path):
            path = os.path.join(os.path.dirname(__file__), path)

        path = self._sanitize_path(path)
        return path

    def get_cocos2dx_path(self):
        cocos2d_x = self._cp.get('paths', 'cocos2d_x')
        cocos2d_x = self._sanitize_path(cocos2d_x)
        return cocos2d_x

    def get_templates_path(self):
        templates = self._cp.get('paths', 'templates')
        templates = self._sanitize_path(templates)
        return templates

    def get_cocos2dx_mode(self):
        mode = self._cp.get('global', 'cocos2d_x_mode')
        if mode is None or len(mode) == 0:
            mode = 'source'

        if mode not in ('source', 'precompiled', 'distro'):
            Logging.warning("Warning: Invalid cocos2d-x mode: %s. Using 'source' as default." % mode)
            mode = 'source'

        return mode


class Logging:
    # TODO maybe the right way to do this is to use something like colorama?
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    MAGENTA = '\033[35m'
    RESET = '\033[0m'

    @staticmethod
    def _print(s, color=None):
        if color and sys.stdout.isatty() and sys.platform != 'win32':
            print(color + s + Logging.RESET)
        else:
            print(s)

    @staticmethod
    def debug(s):
        Logging._print(s, Logging.MAGENTA)

    @staticmethod
    def info(s):
        Logging._print(s, Logging.GREEN)

    @staticmethod
    def warning(s):
        Logging._print(s, Logging.YELLOW)

    @staticmethod
    def error(s):
        Logging._print(s, Logging.RED)


class CCPluginError(Exception):
    pass


class CMDRunner(object):

    @staticmethod
    def run_cmd(command, verbose):
        if verbose:
            Logging.debug("running: '%s'\n" % ''.join(command))
        else:
            log_path = CCPlugin._log_path()
            command += ' >"%s" 2>&1' % log_path
        ret = subprocess.call(command, shell=True)
        if ret != 0:
            message = "Error running command, return code: %s" % str(ret)
            if not verbose:
                message += ". Check the log file at %s" % log_path
            raise CCPluginError(message)

    @staticmethod
    def output_for(command, verbose):
        if verbose:
            Logging.debug("running: '%s'\n" % command)
        else:
            log_path = CCPlugin._log_path()

        try:
            return subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError as e:
            output = e.output
            message = "Error running command"

            if not verbose:
                with open(log_path, 'w') as f:
                    f.write(output)
                message += ". Check the log file at %s" % log_path
            else:
                Logging.error(output)

            raise CCPluginError(message)

    @staticmethod
    def convert_path_to_cmd(path):
        """ Convert path which include space to correct style which bash(mac) and cmd(windows) can treat correctly.

            eg: on mac: convert '/usr/xxx/apache-ant 1.9.3' to '/usr/xxx/apache-ant\ 1.9.3'
            eg: on windows: convert '"c:\apache-ant 1.9.3"\bin' to '"c:\apache-ant 1.9.3\bin"'
        """
        ret = path
        if os_is_mac():
            ret = path.replace("\ ", " ").replace(" ", "\ ")

        if os_is_win32():
            ret = "\"%s\"" % (path.replace("\"", ""))

        # print("!!!!! Convert %s to %s\n" % (path, ret))
        return ret

    @staticmethod
    def convert_path_to_python(path):
        """ Convert path which include space to correct style which python can treat correctly.

            eg: on mac: convert '/usr/xxx/apache-ant\ 1.9.3' to '/usr/xxx/apache-ant 1.9.3'
            eg: on windows: convert '"c:\apache-ant 1.9.3"\bin' to 'c:\apache-ant 1.9.3\bin'
        """
        ret = path
        if os_is_mac():
            ret = path.replace("\ ", " ")

        if os_is_win32():
            ret = ret.replace("\"", "")

        # print("!!!!! Convert %s to %s\n" % (path, ret))
        return ret


#
# Plugins should be a sublass of CCPlugin
#
class CCPlugin(object):

    def _run_cmd(self, command):
        CMDRunner.run_cmd(command, self._verbose)

    def _output_for(self, command):
        return CMDRunner.output_for(command, self._verbose)

    @classmethod
    def get_cocos2d_path(cls):
        """returns the path where cocos2d-x is installed"""

        #
        # 1: Check for config.ini
        #
        parser = Cocos2dIniParser()
        cocos2dx_path = parser.get_cocos2dx_path()

        if cocos2dx_path is not None:
            return cocos2dx_path

        #
        # 2: default engine path
        #
        # possible path of console
        # /Users/myself/cocos2d-x/tools/cocos2d-console/bin
        # if so, we have to remove the last 3 segments
        path = cls.get_console_path()
        path = os.path.abspath(path)
        components = path.split(os.sep)
        if len(components) > 3 and \
                components[-3] == 'tools' and \
                components[-2] == 'cocos2d-console' and \
                components[-1] == 'bin':
            components = components[:-3]
            return string.join(components, os.sep)

        if cls.get_cocos2d_mode() is not "distro":
            # In 'distro' mode this is not a warning since
            # the source code is not expected to be installed
            Logging.warning("Warning: cocos2d-x path not found")
        return None

    @classmethod
    def get_console_path(cls):
        """returns the path where cocos console is installed"""
        run_path = unicode(os.path.abspath(os.path.dirname(__file__)), "utf-8")
        return run_path

    @classmethod
    def get_templates_paths(cls):
        """returns a set of paths where templates are installed"""

        parser = Cocos2dIniParser()
        templates_path = parser.get_templates_path()

        paths = []

        #
        # 1: Check for config.ini
        #
        if templates_path is not None:
            paths.append(templates_path)

        #
        # 2: Path defined by walking the cocos2d path
        #
        path = cls.get_cocos2d_path()

        if path is not None:
            # Try one: cocos2d-x/templates (assuming it is using cocos2d-x's setup.py)
            # Try two: cocos2d-x/../../templates
            possible_paths = [['templates'], ['..', '..', 'templates']]
            for p in possible_paths:
                p = string.join(p, os.sep)
                template_path = os.path.abspath(os.path.join(path, p))
                try:
                    if os.path.isdir(template_path):
                        paths.append(template_path)
                except Exception as e:
                    Logging.info("Check templates path %s failed:" % template_path)
                    Logging.info("%s" % e)
                    pass

        #
        # 3: Templates can be in ~/.cocos2d/templates as well
        #
        user_path = os.path.expanduser("~/.cocos/templates")
        if os.path.isdir(user_path):
            paths.append(user_path)

        if len(paths) == 0:
            raise CCPluginError("Tempalte path not found")

        # remove duplicates
        ordered = OrderedDict.fromkeys(paths)
        paths = ordered.keys()
        return paths

    @classmethod
    def get_cocos2d_mode(cls):
        parser = Cocos2dIniParser()
        return parser.get_cocos2dx_mode()

    @staticmethod
    def _log_path():
        log_dir = os.path.expanduser("~/.cocos")
        if not os.path.exists(log_dir):
            os.mkdir(log_dir)
        return os.path.join(log_dir, "cocos.log")

    # the list of plugins this plugin needs to run before itself.
    # ie: if it returns ('a', 'b'), the plugin 'a' will run first, then 'b'
    # and after that, the plugin itself.
    # they all share the same command line arguments
    @staticmethod
    def depends_on():
        return None

    # returns the plugin category,
    # default is empty string.
    @staticmethod
    def plugin_category():
        return ""

    # returns the plugin name
    @staticmethod
    def plugin_name():
        pass

    # returns help
    @staticmethod
    def brief_description(self):
        pass

    # Constructor
    def __init__(self):
        pass

    # Setup common options. If a subclass needs custom options,
    # override this method and call super.
    def init(self, args):
        self._verbose = (not args.quiet)
        self._platforms = cocos_project.Platforms(self._project, args.platform)
        if self._platforms.none_active():
            self._platforms.select_one()

    # Run it
    def run(self, argv):
        pass

    # If a plugin needs to add custom parameters, override this method.
    # There's no need to call super
    def _add_custom_options(self, parser):
        pass

    # If a plugin needs to check custom parameters values after parsing them,
    # override this method.
    # There's no need to call super
    def _check_custom_options(self, args):
        pass

    def parse_args(self, argv):
        from argparse import ArgumentParser

        parser = ArgumentParser(prog="cocos %s" % self.__class__.plugin_name(),
                                description=self.__class__.brief_description())
        parser.add_argument("-s", "--src",
                            dest="src_dir",
                            help="project base directory")
        parser.add_argument("-q", "--quiet",
                            action="store_true",
                            dest="quiet",
                            help="less output")
        platform_list = cocos_project.Platforms.list_for_display()
        parser.add_argument("-p", "--platform",
                            dest="platform",
                            help="select a platform (%s)" % ', '.join(platform_list))
        self._add_custom_options(parser)

        (args, unkonw) = parser.parse_known_args(argv)

        if args.src_dir is None:
            self._project = cocos_project.Project(os.path.abspath(os.getcwd()))
        else:
            self._project = cocos_project.Project(
                os.path.abspath(args.src_dir))

        args.src_dir = self._project.get_project_dir()
        if args.src_dir is None:
            raise CCPluginError("No directory supplied and found no project at your current directory.\n" +
                                "You can set the folder as a parameter with \"-s\" or \"--src\",\n" +
                                "or change your current working directory somewhere inside the project.\n"
                                "(-h for the usage)")

        if args.platform:
            args.platform = args.platform.lower()
            if args.platform not in platform_list:
                raise CCPluginError("Unknown platform: %s" % args.platform)

        self.init(args)
        self._check_custom_options(args)


# get_class from: http://stackoverflow.com/a/452981
def get_class(kls):
    parts = kls.split('.')
    module = ".".join(parts[:-1])
    if len(parts) == 1:
        m = sys.modules[__name__]
        m = getattr(m, parts[0])
    else:
        m = __import__(module)
        for comp in parts[1:]:
            m = getattr(m, comp)
    return m


def _check_dependencies_exist(dependencies, classes, plugin_name):
    for dep in dependencies:
        if dep not in classes:
            raise CCPluginError("Plugin '%s' lists non existant plugin '%s' as dependency" %
                                (plugin_name, dep))


def _check_dependencies(classes):
    for k in classes:
        plugin = classes[k]
        dependencies = plugin.depends_on()
        if dependencies is not None:
            _check_dependencies_exist(dependencies, classes, k)


# common functions

def check_environment_variable(var):
    ''' Checking the environment variable, if found then return it's value, else raise error
    '''
    try:
        value = os.environ[var]
    except Exception:
        raise CCPluginError(
            "%s not defined. Please define it in your environment" % var)

    return value


def get_xcode_version():
    commands = [
        "xcodebuild",
        "-version"
    ]
    child = subprocess.Popen(commands, stdout=subprocess.PIPE)

    xcode = None
    version = None
    for line in child.stdout:
        if 'Xcode' in line:
            xcode, version = str.split(line, ' ')

    child.wait()

    if xcode is None:
        message = "Xcode wasn't installed"
        raise CCPluginError(message)

    return version


def copy_files_in_dir(src, dst):

    for item in os.listdir(src):
        path = os.path.join(src, item)
        if os.path.isfile(path):
            path = add_path_prefix(path)
            copy_dst = add_path_prefix(dst)
            shutil.copy(path, copy_dst)
        if os.path.isdir(path):
            new_dst = os.path.join(dst, item)
            if not os.path.isdir(new_dst):
                os.makedirs(add_path_prefix(new_dst))
            copy_files_in_dir(path, new_dst)


def copy_files_with_config(config, src_root, dst_root):
    src_dir = config["from"]
    dst_dir = config["to"]

    src_dir = os.path.join(src_root, src_dir)
    dst_dir = os.path.join(dst_root, dst_dir)

    include_rules = None
    if "include" in config:
        include_rules = config["include"]
        include_rules = convert_rules(include_rules)

    exclude_rules = None
    if "exclude" in config:
        exclude_rules = config["exclude"]
        exclude_rules = convert_rules(exclude_rules)

    copy_files_with_rules(
        src_dir, src_dir, dst_dir, include_rules, exclude_rules)


def copy_files_with_rules(src_rootDir, src, dst, include=None, exclude=None):
    if os.path.isfile(src):
        if not os.path.exists(dst):
            os.makedirs(add_path_prefix(dst))

        copy_src = add_path_prefix(src)
        copy_dst = add_path_prefix(dst)
        shutil.copy(copy_src, copy_dst)
        return

    if (include is None) and (exclude is None):
        if not os.path.exists(dst):
            os.makedirs(add_path_prefix(dst))
        copy_files_in_dir(src, dst)
    elif (include is not None):
        # have include
        for name in os.listdir(src):
            abs_path = os.path.join(src, name)
            rel_path = os.path.relpath(abs_path, src_rootDir)
            if os.path.isdir(abs_path):
                sub_dst = os.path.join(dst, name)
                copy_files_with_rules(
                    src_rootDir, abs_path, sub_dst, include=include)
            elif os.path.isfile(abs_path):
                if _in_rules(rel_path, include):
                    if not os.path.exists(dst):
                        os.makedirs(add_path_prefix(dst))

                    abs_path = add_path_prefix(abs_path)
                    copy_dst = add_path_prefix(dst)
                    shutil.copy(abs_path, copy_dst)
    elif (exclude is not None):
        # have exclude
        for name in os.listdir(src):
            abs_path = os.path.join(src, name)
            rel_path = os.path.relpath(abs_path, src_rootDir)
            if os.path.isdir(abs_path):
                sub_dst = os.path.join(dst, name)
                copy_files_with_rules(
                    src_rootDir, abs_path, sub_dst, exclude=exclude)
            elif os.path.isfile(abs_path):
                if not _in_rules(rel_path, exclude):
                    if not os.path.exists(dst):
                        os.makedirs(add_path_prefix(dst))

                    abs_path = add_path_prefix(abs_path)
                    copy_dst = add_path_prefix(dst)
                    shutil.copy(abs_path, copy_dst)


def _in_rules(rel_path, rules):
    import re
    ret = False
    path_str = rel_path.replace("\\", "/")
    for rule in rules:
        if re.match(rule, path_str):
            ret = True

    return ret


def convert_rules(rules):
    ret_rules = []
    for rule in rules:
        ret = rule.replace('.', '\\.')
        ret = ret.replace('*', '.*')
        ret = "%s" % ret
        ret_rules.append(ret)

    return ret_rules


def os_is_win32():
    return sys.platform == 'win32'


def os_is_32bit_windows():
    if not os_is_win32():
        return False

    arch = os.environ['PROCESSOR_ARCHITECTURE'].lower()
    archw = "PROCESSOR_ARCHITEW6432" in os.environ
    return (arch == "x86" and not archw)


def os_is_mac():
    return sys.platform == 'darwin'


def os_is_linux():
    return 'linux' in sys.platform


def add_path_prefix(path_str):
    if not os_is_win32():
        return path_str

    if path_str.startswith("\\\\?\\"):
        return path_str

    ret = "\\\\?\\" + os.path.abspath(path_str)
    ret = ret.replace("/", "\\")
    return ret


# get from http://stackoverflow.com/questions/6194499/python-os-system-pushd
@contextmanager
def pushd(newDir):
    previousDir = os.getcwd()
    os.chdir(newDir)
    yield
    os.chdir(previousDir)


def help():
    print("\n%s %s - cocos console: A command line tool for cocos2d-x" %
          (sys.argv[0], COCOS2D_CONSOLE_VERSION))
    print("\nAvailable commands:")
    parse = Cocos2dIniParser()
    classes = parse.parse_plugins()
    max_name = max(len(classes[key].plugin_name(
    ) + classes[key].plugin_category()) for key in classes.keys())
    max_name += 4
    for key in classes.keys():
        plugin_class = classes[key]
        category = plugin_class.plugin_category()
        category = (category + ' ') if len(category) > 0 else ''
        name = plugin_class.plugin_name()
        print("\t%s%s%s%s" % (category, name,
                              ' ' * (max_name - len(name + category)),
                              plugin_class.brief_description()))

    print("\nAvailable arguments:")
    print("\t-h, --help\tShow this help information")
    print("\t-v, --version\tShow the version of this command tool")
    print("\nExample:")
    print("\t%s new --help" % sys.argv[0])
    print("\t%s run --help" % sys.argv[0])


def run_plugin(command, argv, plugins):
    run_directly = False
    if len(argv) > 0:
        if argv[0] in ['--help', '-h']:
            run_directly = True

    plugin = plugins[command]()

    if run_directly:
        plugin.run(argv, None)
    else:
        dependencies = plugin.depends_on()
        dependencies_objects = {}
        if dependencies is not None:
            for dep_name in dependencies:
                # FIXME check there's not circular dependencies
                dependencies_objects[dep_name] = run_plugin(
                    dep_name, argv, plugins)
        Logging.info("Running command: %s" % plugin.__class__.plugin_name())
        plugin.run(argv, dependencies_objects)
        return plugin


def _check_python_version():
    major_ver = sys.version_info[0]
    if major_ver > 2:
        print ("The python version is %d.%d. But Python 2.7 is required.\n"
               "Download it here: https://www.python.org/"
               % (major_ver, sys.version_info[1]))
        return False

    return True


if __name__ == "__main__":
    if not _check_python_version():
        exit()

    parser = Cocos2dIniParser()
    plugins_path = parser.get_plugins_path()
    sys.path.append(plugins_path)

    if len(sys.argv) == 1 or sys.argv[1] in ('-h', '--help'):
        help()
        exit(0)

    if len(sys.argv) > 1 and sys.argv[1] in ('-v', '--version'):
        print("%s" % COCOS2D_CONSOLE_VERSION)
        exit(0)

    try:
        plugins = parser.parse_plugins()
        command = sys.argv[1]
        argv = sys.argv[2:]
        # try to find plugin by name
        if command in plugins:
            run_plugin(command, argv, plugins)
        else:
            # try to find plguin by caetegory_name, so the len(sys.argv) at
            # least 3.
            if len(sys.argv) > 2:
                # combine category & name as key
                # eg. 'project_new'
                command = sys.argv[1] + '_' + sys.argv[2]
                argv = sys.argv[3:]
                if command in plugins:
                    run_plugin(command, argv, plugins)
                else:
                    Logging.error(
                        "Error: argument '%s' not found" % ' '.join(sys.argv[1:]))
                    Logging.error("Try with %s -h" % sys.argv[0])
            else:
                Logging.error("Error: argument '%s' not found" % command)
                Logging.error("Try with %s -h" % sys.argv[0])

    except Exception as e:
        # FIXME don't know how to handle this. Can't catch cocos2d.CCPluginError
        # as it's not defined that way in this file, but the plugins raise it
        # with that name.
        if e.__class__.__name__ == 'CCPluginError':
            Logging.error(' '.join(e.args))
            # import traceback
            # print '-' * 60
            # traceback.print_exc(file=sys.stdout)
            # print '-' * 60
            sys.exit(1)
        else:
            raise
