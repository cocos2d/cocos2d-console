#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos-console: command line tool manager for cocos2d
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

COCOS2D_CONSOLE_VERSION = '0.7'


class Logging:
    # TODO maybe the right way to do this is to use something like colorama?
    RED     = '\033[31m'
    GREEN   = '\033[32m'
    YELLOW  = '\033[33m'
    MAGENTA = '\033[35m'
    RESET   = '\033[0m'

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


#
# Plugins should be a sublass of CCPlugin
#
class CCPlugin(object):

    def _run_cmd(self, command):
        CMDRunner.run_cmd(command, self._verbose)

    def _output_for(self, command):
        return CMDRunner.output_for(command, self._verbose)

    @staticmethod
    def _log_path():
        log_dir = os.path.expanduser("~/.cocos2d")
        if not os.path.exists(log_dir):
            os.mkdir(log_dir)
        return os.path.join(log_dir, "cocos2d.log")

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
            self._project = cocos_project.Project(os.path.abspath(args.src_dir))

        args.src_dir = self._project.get_project_dir()
        if args.src_dir is None:
            raise CCPluginError("No directory supplied and found no project at your current directory.\n" +
                "You can set the folder as a parameter with \"-s\" or \"--src\",\n" +
                "or change your current working directory somewhere inside the project.\n"
                "(-h for the usage)")

        if args.platform:
            args.platform = args.platform.lower()
            if not args.platform in platform_list:
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
        if not dep in classes:
            raise CCPluginError("Plugin '%s' lists non existant plugin '%s' as dependency" %
                (plugin_name, dep))

def _check_dependencies(classes):
    for k in classes:
        plugin = classes[k]
        dependencies = plugin.depends_on()
        if dependencies is not None:
            _check_dependencies_exist(dependencies, classes, k)


### common functions ###

def check_environment_variable(var):
    ''' Checking the environment variable, if found then return it's value, else raise error
    '''
    try:
        value = os.environ[var]
    except Exception:
        raise CCPluginError("%s not defined. Please define it in your environment" % var)

    return value


def select_default_android_platform(min_api_level):
    ''' selec a default android platform in SDK_ROOT, support platforms 10-19
    '''

    sdk_root = check_environment_variable('ANDROID_SDK_ROOT')
    platforms_dir = os.path.join(sdk_root, "platforms")
    if os.path.isdir(platforms_dir):
       for num in range (min_api_level, 19+1):
           android_platform = 'android-%s' % num
           if os.path.isdir(os.path.join(platforms_dir, android_platform)):
               Logging.info('%s is found' % android_platform)
               return num
    return None


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
    if config.has_key("include"):
        include_rules = config["include"]
        include_rules = convert_rules(include_rules)

    exclude_rules = None
    if config.has_key("exclude"):
        exclude_rules = config["exclude"]
        exclude_rules = convert_rules(exclude_rules)

    copy_files_with_rules(src_dir, src_dir, dst_dir, include_rules, exclude_rules)

def copy_files_with_rules(src_rootDir, src, dst, include = None, exclude = None):
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
                copy_files_with_rules(src_rootDir, abs_path, sub_dst, include = include)
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
                copy_files_with_rules(src_rootDir, abs_path, sub_dst, exclude = exclude)
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


def parse_plugins():
    import ConfigParser
    classes = {}
    cp = ConfigParser.ConfigParser(allow_no_value=True)
    cp.optionxform = str

    # read global config file
    cocos2d_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    cp.read(os.path.join(cocos2d_path, "cocos2d.ini"))

    # override it with local config
    cp.read("~/.cocos2d-js/cocos2d.ini")

    for s in cp.sections():
        if s == 'plugins':
            for classname in cp.options(s):
                plugin_class = get_class(classname)
                category = plugin_class.plugin_category()
                name = plugin_class.plugin_name()
                if name is None:
                    print("Warning: plugin '%s' does not return a plugin name" % classname)
                if len(category) == 0:
                    key = name
                else:
                    # combine category & name as key
                    # eg. 'project_new'
                    key = category + '_' + name
                classes[key] = plugin_class

    _check_dependencies(classes)

    return classes

def help():
    print("\n%s %s - cocos console: A command line tool for cocos2d" % (sys.argv[0], COCOS2D_CONSOLE_VERSION))
    print("\nAvailable commands:")
    classes = parse_plugins()
    max_name = max(len(classes[key].plugin_name() + classes[key].plugin_category()) for key in classes.keys())
    max_name += 4
    for key in classes.keys():
        plugin_class = classes[key]
        category = plugin_class.plugin_category()
        category = (category +' ') if len(category) > 0 else ''
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
    sys.exit(-1)

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
                #FIXME check there's not circular dependencies
                dependencies_objects[dep_name] = run_plugin(dep_name, argv, plugins)
        Logging.info("Running command: %s" % plugin.__class__.plugin_name())
        plugin.run(argv, dependencies_objects)
        return plugin

def _check_python_version():
    major_ver = sys.version_info[0]
    if major_ver > 2:
        print ("The python version is %d.%d. But python 2.x is required. (Version 2.7 is well tested)\n"
               "Download it here: https://www.python.org/" % (major_ver, sys.version_info[1]))
        return False

    return True


if __name__ == "__main__":
    if not _check_python_version():
        exit()

    plugins_path = os.path.join(os.path.dirname(__file__), '..', 'plugins')
    sys.path.append(plugins_path)

    if len(sys.argv) == 1 or sys.argv[1] in ('-h', '--help'):
        help()

    if len(sys.argv) == 1 or sys.argv[1] in ('-v', '--version'):
        print("%s" % COCOS2D_CONSOLE_VERSION)
        exit(0)

    try:
        plugins = parse_plugins()
        command =sys.argv[1]
        argv = sys.argv[2:]
        # try to find plugin by name
        if command in plugins:
            run_plugin(command, argv, plugins)
        else:
            # try to find plguin by caetegory_name, so the len(sys.argv) at least 3.
            if len(sys.argv) > 2:
                # combine category & name as key
                # eg. 'project_new'
                command = sys.argv[1] + '_' + sys.argv[2]
                argv = sys.argv[3:]
                if command in plugins:
                    run_plugin(command, argv, plugins)
                else:
                    Logging.error("Error: argument '%s' not found" % ' '.join(sys.argv[1:]))
                    Logging.error("Try with %s -h" % sys.argv[0])
            else:
                Logging.error("Error: argument '%s' not found" % command)
                Logging.error("Try with %s -h" % sys.argv[0])

    except Exception as e:
        #FIXME don't know how to handle this. Can't catch cocos2d.CCPluginError
        #as it's not defined that way in this file, but the plugins raise it
        #with that name.
        if e.__class__.__name__ == 'CCPluginError':
            Logging.error(' '.join(e.args))
            sys.exit(1)
        else:
            raise
