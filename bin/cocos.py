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

    # returns the plugin category
    @staticmethod
    def plugin_category():
      pass

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
    def init(self, options):
        self._src_dir = os.path.normpath(options.src_dir)
        self._verbose = options.verbose
        self._project = Project(self._src_dir)

        self._platforms = Platforms(self._src_dir, self._project_lang, options.platform)
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
    def _check_custom_options(self, options, args):
        pass

    # Tries to find the project's base path
    def _find_project_dir(self):
        path = os.getcwd()
        while path != '/':
            if os.path.exists(os.path.join(path, 'cocos2d/cocos/2d/cocos2d.cpp')):
                self._project_lang = "cpp"
                return path

            if os.path.exists(os.path.join(path, 'project.json')):
                self._project_lang = "js"
                return path

            if os.path.exists(os.path.join(path, 'src/main.lua')):
                self._project_lang = "lua"
                return path

            path = os.path.dirname(path)


        return None

    def _is_script_project(self):
        return self._project_lang in ('lua', 'js')

    def parse_args(self, argv):
        from optparse import OptionParser

        parser = OptionParser("usage: %%prog %s -s src_dir [-hvp]" % self.__class__.plugin_name())
        parser.add_option("-s", "--src",
                          dest="src_dir",
                          help="project base directory")
        parser.add_option("-v", "--verbose",
                          action="store_true",
                          dest="verbose",
                          help="verbose output")
        platform_list = Platforms.list_for_display()
        parser.add_option("-p", "--platform",
                          dest="platform",
                          help="select a platform (%s)" % ', '.join(platform_list))
        self._add_custom_options(parser)

        (options, args) = parser.parse_args(argv)

        if options.src_dir is None:
            options.src_dir = self._find_project_dir()

        if options.src_dir is None:
            raise CCPluginError("No directory supplied and found no project at your current directory.\n" +
                "You can set the folder as a parameter with \"-s\" or \"-src\",\n" +
                "or change your current working directory somewhere inside the project.\n"
                "(-h for the usage)")
        else:
            if os.path.exists(options.src_dir) == False:
              raise CCPluginError("Error: dir (%s) doesn't exist..." % (options.src_dir))

        if options.platform and not options.platform in platform_list:
            raise CCPluginError("Unknown platform: %s" % options.platform)

        self._check_custom_options(options, args)
        self.init(options)


class Project(object):
    CPP = 'cpp'
    LUA = 'lua'
    JS = 'javascript'

    def __init__(self, project_dir):
        self.project_dir = project_dir
        self._parse_project_json()

    def _parse_project_json(self):
        project_json = os.path.join(self.project_dir, 'project.json')
        found = os.path.isfile(project_json)

        if not found:
            return None

        f = open(project_json)
        project_info = json.load(f) 

        self._type = project_info["project_type"]

        return project_info

    def _is_script_project(self):
        return self._is_lua_project() or self._is_js_project()

    def _is_cpp_project(self):
        return self._current == Project.CPP

    def _is_lua_project(self):
        return self._current == Project.LUA

    def _is_js_project(self):
        return self._current == Project.JS

        
class Platforms(object):
    ANDROID = 'Android'
    IOS = 'iOS'
    MAC = 'Mac'
    HTML5 = 'H5'

    @staticmethod
    def list_for_display():
        return [x.lower() for x in Platforms.list()]

    @staticmethod
    def list():
        return (Platforms.ANDROID, Platforms.IOS, Platforms.MAC, Platforms.HTML5)

    def _is_script_project(self):
        return self._project_lang in ('lua', 'js')

    def _check_native_support(self):

        if self._is_script_project():
            runtime_path = os.path.join(self._project_path, 'frameworks', 'runtime-src')
            if os.path.exists(runtime_path):
                self._native_platforms_dir = runtime_path
        else:
            self._native_platforms_dir = self._project_path


    def __init__(self, path, lang, current):
        self._project_path = path
        self._project_lang = lang

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
            self._add_native_project(Platforms.ANDROID, 'proj.android')
            self._add_native_project(Platforms.IOS, 'proj.ios_mac')
            self._add_native_project(Platforms.MAC, 'proj.ios_mac')

        if self._project_lang == 'js':
            self._platform_project_paths[Platforms.HTML5] = self._project_path


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

    def is_h5_active(self):
        return self._current == Platforms.HTML5

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

        Logging.warning('Multiple platforms detected!')
        Logging.warning("You can select one via command line arguments (-h to see the options)")
        Logging.warning('Or choose one now:\n')

        p = self._platform_project_paths.keys()
        for i in range(len(p)):
            Logging.warning('%d. %s' % (i + 1, p[i]))
        Logging.warning("Select one (and press enter): ")
        while True:
            option = raw_input()
            if option.isdigit():
                option = int(option) - 1
                if option in range(len(p)):
                    break

        self._current = p[option]


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
    ''' selec a default android platform in SDK_ROOT
    '''
    sdk_root = check_environment_variable('ANDROID_SDK_ROOT')
    platforms_dir = os.path.join(sdk_root, "platforms")
    if os.path.isdir(platforms_dir):
       for num in range (10, 19):
           android_platform = 'android-%s' % num
           if os.path.isdir(os.path.join(platforms_dir, android_platform)):
               Logging.info('%s is found' % android_platform)
               return num
    return None

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
                if name is None or category is None:
                    print "Warning: plugin '%s' does not return a plugin name or category" % classname
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
    max_name = max(len(classes[key].plugin_name()) for key in classes.keys())
    max_name += 4
    for key in classes.keys():
        plugin_class = classes[key]
        category = plugin_class.plugin_category()
        name = plugin_class.plugin_name()
        print "\t%s %s%s%s" % (category, name,
                            ' ' * (max_name - len(name)),
                            plugin_class.brief_description())
    print "\t"
    print "\nExample:"
    print "\t%s project new --help" % sys.argv[0]
    print "\t%s project jscompile --help" % sys.argv[0]
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
        plugin.run(argv, dependencies_objects)
        return plugin



if __name__ == "__main__":
    plugins_path = os.path.join(os.path.dirname(__file__), '..', 'plugins')
    sys.path.append(plugins_path)

    if len(sys.argv) <= 2 or sys.argv[1] == '-h':
        help()

    # combine category & name as key
    # eg. 'project_new'
    command = sys.argv[1] + '_' + sys.argv[2]
    argv = sys.argv[3:]
    try:
        plugins = parse_plugins()
        if command in plugins:
            run_plugin(command, argv, plugins)
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
