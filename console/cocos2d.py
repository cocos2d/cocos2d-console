#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos2d-console: command line tool manager for cocos2d
#
# Author: Ricardo Quesada
# Copyright 2013 (C) Zynga, Inc
#
# License: MIT
# ----------------------------------------------------------------------------
'''
Command line tool manager for cocos2d
'''

__docformat__ = 'restructuredtext'


# python
import sys
import ConfigParser
import os
import subprocess
import inspect

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
        if color:
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


#
# Plugins should be a sublass of CCPlugin
#
class CCPlugin(object):

    def _run_cmd(self, command):
        if self._verbose:
            Logging.debug("running: '%s'\n" % command)
        else:
            log_path = CCPlugin._log_path()
            command += ' >"%s" 2>&1' % log_path
        ret = subprocess.call(command, shell=True)
        if ret != 0:
            message = "Error running command"
            if not self._verbose:
                message += ". Check the log file at %s" % log_path
            raise CCPluginError(message)

    @staticmethod
    def _log_path():
        log_dir = os.path.expanduser("~/.cocos2d")
        if not os.path.exists(log_dir):
            os.mkdir(log_dir)
        return os.path.join(log_dir, "cocos2d.log")

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
    def init(self, options, working_dir):
        self._src_dir = os.path.normpath(options.src_dir)
        self._workingdir = working_dir
        self._verbose = options.verbose

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
    def _check_custom_options(self, options):
        pass

    def parse_args(self, argv):
        from optparse import OptionParser

        parser = OptionParser("usage: %%prog %s -s src_dir -h -v" % self.__class__.plugin_name())
        parser.add_option("-s", "--src",
                          dest="src_dir",
                          help="project base directory")
        parser.add_option("-v", "--verbose",
                          action="store_true",
                          dest="verbose",
                          help="verbose output")
        self._add_custom_options(parser)

        (options, args) = parser.parse_args(argv)

        if options.src_dir == None:
            raise cocos2d.CCPluginError("Please set source folder with \"-s\" or \"-src\", use -h for the usage ")
        else:
            if os.path.exists(options.src_dir) == False:
              raise cocos2d.CCPluginError("Error: dir (%s) doesn't exist..." % (options.src_dir))

        self._check_custom_options(options)
        workingdir = os.path.dirname(inspect.getfile(inspect.currentframe()))
        self.init(options, workingdir)


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
                key = plugin_class.plugin_name()
                if key is None:
                    print "Warning: plugin '%s' does not return a plugin name" % classname
                classes[key] = plugin_class
    return classes


def help():
    print "\n%s %s - cocos2d console: A command line tool for cocos2d" % (sys.argv[0], COCOS2D_CONSOLE_VERSION)
    print "\nAvailable commands:"
    classes = parse_plugins()
    max_name = max(len(classes[key].plugin_name()) for key in classes.keys())
    max_name += 4
    for key in classes.keys():
        plugin_class = classes[key]
        name = plugin_class.plugin_name()
        print "\t%s%s%s" % (name,
                            ' ' * (max_name - len(name)),
                            plugin_class.brief_description())
    print "\t"
    print "\nExample:"
    print "\t%s new --help" % sys.argv[0]
    print "\t%s jscompile --help" % sys.argv[0]
    sys.exit(-1)

if __name__ == "__main__":
    if len(sys.argv) == 1 or sys.argv[1] == '-h':
        help()

    command = sys.argv[1]
    argv = sys.argv[2:]
    plugins = parse_plugins()
    if command in plugins:
        try:
            plugin = plugins[command]()
            plugin.run(argv)
        except Exception as e:
            #FIXME don't know how to handle this. Can't catch cocos2d.CCPluginError
            #as it's not defined that way in this file, but the plugins raise it
            #with that name.
            if e.__class__.__name__ == 'CCPluginError':
                Logging.error(' '.join(e.args))
            else:
                raise
    else:
        print "Error: argument '%s' not found" % command
        print "Try with %s -h" % sys.argv[0]
