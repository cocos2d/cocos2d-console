#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos2d-js command line tool manager
#
# Author: Ricardo Quesada
# Copyright 2013 (C) Zynga, Inc
#
# License: MIT
# ----------------------------------------------------------------------------
'''
Command line tool to manage cocos2d-JS
'''

__docformat__ = 'restructuredtext'


# python
import sys
import re
import ConfigParser

COCOS2D_JS_VERSION = '0.1'


#
# Plugins should be a sublass of CCJSPlugin
#
class CCPlugin(object):

    # returns help
    @staticmethod
    def help(self):
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
    cp = ConfigParser.ConfigParser()
    cp.read("cocos2d.ini")

    for s in cp.sections():
        if s.startswith('plugin '):
            pluginname = re.match('plugin\s+"?(\w+)"?', s)
            if pluginname:
                key = pluginname.group(1)
                for o in cp.options(s):
                    classname = cp.get(s, o)
                    classes[key] = get_class(classname)
    return classes


def help():
    print "%s %s - tool to manage cocos2d-js" % (sys.argv[0], COCOS2D_JS_VERSION)
    print "Usage:"
    classes = parse_plugins()
    for key in classes.keys():
        print "\t%s" % classes[key].help()
    print "\t"
    print "\nExample:"
    print "\t%s new \"My Game\"" % sys.argv[0]
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
