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
import ConfigParser
import os
import subprocess
import inspect
import json
from contextlib import contextmanager
import re

COCOS2D_CONSOLE_VERSION = '0.1'


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
            print color + s + Logging.RESET
        else:
            print s

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
        self._platforms = Platforms(self._project, args.platform)
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
        platform_list = Platforms.list_for_display()
        parser.add_argument("-p", "--platform",
                          dest="platform",
                          help="select a platform (%s)" % ', '.join(platform_list))
        self._add_custom_options(parser)

        (args, unkonw) = parser.parse_known_args(argv)

        if args.src_dir is None:
            self._project = Project(os.path.abspath(os.getcwd()))
        else:
            self._project = Project(os.path.abspath(args.src_dir))

        args.src_dir = self._project.get_project_dir()
        if args.src_dir is None:
            raise CCPluginError("No directory supplied and found no project at your current directory.\n" +
                "You can set the folder as a parameter with \"-s\" or \"--src\",\n" +
                "or change your current working directory somewhere inside the project.\n"
                "(-h for the usage)")

        if args.platform and not args.platform in platform_list:
            raise CCPluginError("Unknown platform: %s" % args.platform)

        self._check_custom_options(args)
        self.init(args)

class Project(object):
    CPP = 'cpp'
    LUA = 'lua'
    JS = 'js'
    CONFIG = '.cocos-project.json'
    KEY_PROJ_TYPE = 'project_type'
    KEY_HAS_NATIVE = 'has_native'

    @staticmethod
    def list_for_display():
        return [x.lower() for x in Platforms.list()]

    @staticmethod
    def list():
        return (Platforms.ANDROID, Platforms.IOS, Platforms.MAC, Platforms.WEB)

    def __init__(self, project_dir):
        self._parse_project_json(project_dir)

    def _parse_project_json(self, src_dir):
        proj_path = self._find_project_dir(src_dir)
        # config file is not found
        if proj_path == None:
            raise CCPluginError("Can't find config file %s in path %s" % (Project.CONFIG, src_dir))

        # parse the config file
        project_json = os.path.join(proj_path, Project.CONFIG)
        f = open(project_json)
        project_info = json.load(f)
        lang = project_info[Project.KEY_PROJ_TYPE]

        # The config is invalide
        if not (lang in (Project.CPP, Project.LUA, Project.JS)):
            raise CCPluginError("The value of \"%s\" must be one of (%s)" % (Project.KEY_PROJ_TYPE, ', '.join(Project.list_for_display())))

        # record the dir & language of the project
        self._project_dir = proj_path
        self._project_lang = lang
        # if is script project, record whether it has native or not
        self._has_native = False
        if (self._is_script_project() and project_info.has_key(Project.KEY_HAS_NATIVE)):
            self._has_native = project_info[Project.KEY_HAS_NATIVE]

        return project_info

    # Tries to find the project's base path
    def _find_project_dir(self, start_path):
        path = start_path
        while True:
            if sys.platform == 'win32':
                # windows root path, eg. c:\
                if re.match(".+:\\\\$", path):
                    break
            else:
                # unix like use '/' as root path
                if path == '/' :
                    break
            cfg_path = os.path.join(path, Project.CONFIG)
            if (os.path.exists(cfg_path) and os.path.isfile(cfg_path)):
                return path

            path = os.path.dirname(path)

        return None

    def get_project_dir(self):
        return self._project_dir

    def get_language(self):
        return self._project_lang

    def _is_native_support(self):
        return self._has_native

    def _is_script_project(self):
        return self._is_lua_project() or self._is_js_project()

    def _is_cpp_project(self):
        return self._project_lang == Project.CPP

    def _is_lua_project(self):
        return self._project_lang == Project.LUA

    def _is_js_project(self):
        return self._project_lang == Project.JS


class Platforms(object):
    ANDROID = 'Android'
    IOS = 'iOS'
    MAC = 'Mac'
    WEB = 'Web'
    WIN32 = 'Win32'
    LINUX = 'Linux'

    @staticmethod
    def list_for_display():
        return [x.lower() for x in Platforms.list()]

    @staticmethod
    def list():
        return (Platforms.ANDROID, Platforms.IOS, Platforms.MAC, Platforms.WEB, Platforms.WIN32, Platforms.LINUX)

    def _check_native_support(self):
        if self._project._is_script_project():
            if self._project._is_native_support():
                # has native
                runtime_path = os.path.join(self._project.get_project_dir(), 'frameworks', 'runtime-src')
                if os.path.exists(runtime_path):
                    # has platforms dir
                    self._native_platforms_dir = runtime_path
                else:
                    # platforms dir not existed
                    raise CCPluginError("Can't find the projects directories in this project.")
            else:
                # not has native
                raise CCPluginError("The project doesn't has the native code.")
        else:
            self._native_platforms_dir = self._project.get_project_dir()

    def __init__(self, project, current):
        self._project = project

        self._native_platforms_dir = None
        self._check_native_support()

        self._platform_project_paths = dict()
        if current is not None:
            index = Platforms.list_for_display().index(current)
            self._current = Platforms.list()[index]
        else:
            self._current = None
        self._search()

    def _search(self):
        if self._native_platforms_dir is not None:
            self._add_native_project(Platforms.WIN32, 'proj.win32')
            self._add_native_project(Platforms.ANDROID, 'proj.android')
            self._add_native_project(Platforms.IOS, 'proj.ios_mac')
            self._add_native_project(Platforms.MAC, 'proj.ios_mac')
            self._add_native_project(Platforms.LINUX, 'proj.linux')

        if self._project._is_js_project():
            self._platform_project_paths[Platforms.WEB] = self._project.get_project_dir()


    def _add_native_project(self, platform, dir):
        path = self._build_native_project_dir(dir)
        if path:
            self._platform_project_paths[platform] = path

    def none_active(self):
        return self._current is None

    def is_android_active(self):
        return self._current == Platforms.ANDROID

    def is_ios_active(self):
        return self._current == Platforms.IOS

    def is_mac_active(self):
        return self._current == Platforms.MAC

    def is_web_active(self):
        return self._current == Platforms.WEB

    def is_win32_active(self):
        return self._current == Platforms.WIN32

    def is_linux_active(self):
        return self._current == Platforms.LINUX

    def project_path(self):
        if self._current is None:
            return None
        return self._platform_project_paths[self._current]

    def _build_native_project_dir(self, project_name):
        project_dir = os.path.join(self._native_platforms_dir, project_name)
        found = os.path.isdir(project_dir)

        if not found:
            return None

        return project_dir

    def _has_one(self):
        return len(self._platform_project_paths) == 1

    def select_one(self):
        if self._has_one():
            self._current = self._platform_project_paths.keys()[0]
            return

        p = self._platform_project_paths.keys()
        strPlatform = ""
        for i in range(len(p)):
            strPlatform += (p[i]).lower()
            if i < (len(p) - 1):
                strPlatform += ", "

        raise CCPluginError("The target platform is not specified.\n" +
            "You can specify a target platform with \"-p\" or \"--platform\".\n" +
            "Available platforms : %s" % (strPlatform))

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


def select_default_android_platform():
    ''' selec a default android platform in SDK_ROOT, support platforms 10-19
    '''

    sdk_root = check_environment_variable('ANDROID_SDK_ROOT')
    platforms_dir = os.path.join(sdk_root, "platforms")
    if os.path.isdir(platforms_dir):
       for num in range (10, 19+1):
           android_platform = 'android-%s' % num
           if os.path.isdir(os.path.join(platforms_dir, android_platform)):
               Logging.info('%s is found' % android_platform)
               return num
    return None

def os_is_win32():
    return sys.platform == 'win32'

def os_is_mac():
    return sys.platform == 'darwin'

def os_is_linux():
    return 'linux' in sys.platform

# get from http://stackoverflow.com/questions/6194499/python-os-system-pushd
@contextmanager
def pushd(newDir):
    previousDir = os.getcwd()
    os.chdir(newDir)
    yield
    os.chdir(previousDir)


def parse_plugins():
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
                    print "Warning: plugin '%s' does not return a plugin name" % classname
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
    print "\n%s %s - cocos console: A command line tool for cocos2d" % (sys.argv[0], COCOS2D_CONSOLE_VERSION)
    print "\nAvailable commands:"
    classes = parse_plugins()
    max_name = max(len(classes[key].plugin_name() + classes[key].plugin_category()) for key in classes.keys())
    max_name += 4
    for key in classes.keys():
        plugin_class = classes[key]
        category = plugin_class.plugin_category()
        category = (category +' ') if len(category) > 0 else ''
        name = plugin_class.plugin_name()
        print "\t%s%s%s%s" % (category, name,
                            ' ' * (max_name - len(name + category)),
                            plugin_class.brief_description())
    print "\t"
    print "\nExample:"
    print "\t%s new --help" % sys.argv[0]
    print "\t%s run --help" % sys.argv[0]
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
        Logging.info("Runing command: %s" % plugin.__class__.plugin_name())
        plugin.run(argv, dependencies_objects)
        return plugin



if __name__ == "__main__":
    plugins_path = os.path.join(os.path.dirname(__file__), '..', 'plugins')
    sys.path.append(plugins_path)

    if len(sys.argv) == 1 or sys.argv[1] in ('-h', '--help'):
        help()

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
