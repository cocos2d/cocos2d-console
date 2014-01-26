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
import re
import ConfigParser
import os
import subprocess

COCOS2D_CONSOLE_VERSION = '0.1'


#
# Plugins should be a sublass of CCJSPlugin
#
class CCPlugin(object):

    def _run_cmd(self, command):
        print "\ncommand:"+command+"\n"
        ret = subprocess.call(command, shell=True)
        if ret != 0:
            raise Exception("Error running command")

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

    # Run it
    def run(self, argv):
        pass


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
        plugin = plugins[command]
        plugin().run(argv)
    else:
        print "Error: argument '%s' not found" % command
        print "Try with %s -h" % sys.argv[0]
