#!/usr/bin/python
# ----------------------------------------------------------------------------
# statistics: Statistics the user behaviors of cocos2d-console by google analytics
#
# Author: Bin Zhang
#
# License: MIT
# ----------------------------------------------------------------------------
'''
Statistics the user behaviors of cocos2d-console by google analytics
'''

import cocos
import uuid
import locale
import httplib
import urllib
import platform
import sys

from threading import Thread

# Constants

GA_HOST        = 'www.google-analytics.com'
GA_PATH        = '/collect'
GA_APIVERSION  = '1'
APPNAME     = 'CocosConcole'

# formal tracker ID
GA_TRACKERID = 'UA-60734607-1'

# debug tracker ID
# GA_TRACKERID = 'UA-60530469-4'

class Fields(object):
    API_VERSION     = 'v'
    TRACKING_ID     = 'tid'
    HIT_TYPE        = 't'
    CLIENT_ID       = 'cid'
    EVENT_CATEGORY  = 'ec'
    EVENT_ACTION    = 'ea'
    EVENT_LABEL     = 'el'
    EVENT_VALUE     = 'ev'
    APP_NAME        = 'an'
    APP_VERSION     = 'av'
    USER_LANGUAGE   = 'ul'
    USER_AGENT      = 'ua'
    SCREEN_NAME     = "cd"
    SCREEN_RESOLUTION = "sr"

class Statistic(object):

    def get_mac_address(self):
        node = uuid.getnode()
        mac = uuid.UUID(int = node).hex[-12:]
        return mac

    def get_language(self):
        lang, encoding = locale.getdefaultlocale()
        return lang

    def get_user_agent(self):
        ret_str = None
        if cocos.os_is_win32():
            ver_info = sys.getwindowsversion()
            ver_str = '%d.%d' % (ver_info[0], ver_info[1])
            if cocos.os_is_32bit_windows():
                arch_str = "WOW32"
            else:
                arch_str = "WOW64"
            ret_str = "Mozilla/5.0 (Windows NT %s; %s) Chrome/33.0.1750.154 Safari/537.36" % (ver_str, arch_str)
        elif cocos.os_is_mac():
            ver_str = (platform.mac_ver()[0]).replace('.', '_')
            ret_str = "Mozilla/5.0 (Macintosh; Intel Mac OS X %s) Chrome/35.0.1916.153 Safari/537.36" % ver_str
        elif cocos.os_is_linux():
            arch_str = platform.machine()
            ret_str = "Mozilla/5.0 (X11; Linux %s) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1636.0 Safari/537.36" % arch_str

        return ret_str

    def get_system_info(self):
        if cocos.os_is_win32():
            ret_str = "windows"
            ret_str += "_%s" % platform.release()
            if cocos.os_is_32bit_windows():
                ret_str += "_%s" % "32bit"
            else:
                ret_str += "_%s" % "64bit"
        elif cocos.os_is_mac():
            ret_str = "mac_%s" % (platform.mac_ver()[0]).replace('.', '_')
        elif cocos.os_is_linux():
            ret_str = "linux_%s" % platform.linux_distribution()[0]
        else:
            ret_str = "unknown"

        return ret_str

    def get_python_version(self):
        return "python_%s" % platform.python_version()

    def get_static_params(self):
        static_params = {
            Fields.API_VERSION: GA_APIVERSION,
            Fields.TRACKING_ID: GA_TRACKERID,
            Fields.CLIENT_ID: self.get_mac_address(),
            Fields.APP_NAME: APPNAME,
            Fields.HIT_TYPE: "event",
            Fields.USER_LANGUAGE: self.get_language(),
            Fields.APP_VERSION: cocos.COCOS2D_CONSOLE_VERSION,
            Fields.SCREEN_NAME: self.get_system_info(),
            Fields.SCREEN_RESOLUTION: self.get_python_version()
        }
        agent_str = self.get_user_agent()
        if agent_str is not None:
            static_params[Fields.USER_AGENT] = agent_str

        return urllib.urlencode(static_params)

    def get_url_str(self, params):
        ret_str = "%s?%s" % (GA_PATH, self.get_static_params())
        if len(params) > 0:
            ret_str = "%s&%s" % (ret_str, urllib.urlencode(params))
        return ret_str

    def send_event(self, category, action, label):
        try:
            params = {
                Fields.EVENT_CATEGORY: category,
                Fields.EVENT_ACTION: action,
                Fields.EVENT_LABEL: label,
                Fields.EVENT_VALUE: "1",
            }
            url_str = self.get_url_str(params)

            thread = Thread(target = self.do_send, args = (url_str,))
            thread.start()
        except:
            pass

    def do_send(self, url_str):
        conn = None
        try:
            conn = httplib.HTTPConnection(GA_HOST)
            conn.request(method="GET", url=url_str)

            response = conn.getresponse()
            res = response.status
        except:
            pass
        finally:
            if conn:
                conn.close()
