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
import os
import json
import time
import socket

import multiprocessing

# Constants

GA_HOST        = 'www.google-analytics.com'
GA_PATH        = '/collect'
GA_APIVERSION  = '1'
APPNAME     = 'CocosConcole'

TIMEOUT_VALUE = 0.5

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


CACHE_EVENTS_FILE = 'cache_events'
CACHE_EVENTS_BAK_FILE = 'cache_event_bak'

local_cfg_path = os.path.expanduser('~/.cocos')
local_cfg_file = os.path.join(local_cfg_path, CACHE_EVENTS_FILE)
local_cfg_bak_file = os.path.join(local_cfg_path, CACHE_EVENTS_BAK_FILE)
file_in_use_lock = multiprocessing.Lock()
bak_file_in_use_lock = multiprocessing.Lock()

def get_mac_address():
    node = uuid.getnode()
    mac = uuid.UUID(int = node).hex[-12:]
    return mac

def get_language():
    lang, encoding = locale.getdefaultlocale()
    return lang

def get_user_agent():
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

def get_system_info():
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

def get_python_version():
    return "python_%s" % platform.python_version()

def get_static_params():
    static_params = {
        Fields.API_VERSION: GA_APIVERSION,
        Fields.TRACKING_ID: GA_TRACKERID,
        Fields.CLIENT_ID: get_mac_address(),
        Fields.APP_NAME: APPNAME,
        Fields.HIT_TYPE: "event",
        Fields.USER_LANGUAGE: get_language(),
        Fields.APP_VERSION: cocos.COCOS2D_CONSOLE_VERSION,
        Fields.SCREEN_NAME: get_system_info(),
        Fields.SCREEN_RESOLUTION: get_python_version()
    }
    agent_str = get_user_agent()
    if agent_str is not None:
        static_params[Fields.USER_AGENT] = agent_str

    return static_params

def get_cached_events(is_bak=False, need_lock=True):
    if is_bak:
        cfg_file = local_cfg_bak_file
        lock = bak_file_in_use_lock
    else:
        cfg_file = local_cfg_file
        lock = file_in_use_lock

    if not os.path.isfile(cfg_file):
        cached_events = []
    else:
        f = None
        try:
            if need_lock:
                lock.acquire()

            f = open(cfg_file)
            cached_events = json.load(f)
            f.close()

            if not isinstance(cached_events, list):
                cached_events = []
        except:
            cached_events = []
        finally:
            if f is not None:
                f.close()
            if need_lock:
                lock.release()

    return cached_events

def cache_event( event):
    file_in_use_lock.acquire()

    outFile = None
    try:
        # get current cached events
        cache_events = get_cached_events(is_bak=False, need_lock=False)

        # delete the oldest events if there are too many events.
        events_size = len(cache_events)
        if events_size >= Statistic.MAX_CACHE_EVENTS:
            start_idx = events_size - (Statistic.MAX_CACHE_EVENTS - 1)
            cache_events = cache_events[start_idx:]

        # cache the new event
        cache_events.append(event)

        # write file
        outFile = open(local_cfg_file, 'w')
        json.dump(cache_events, outFile)
        outFile.close()
    except:
        if outFile is not None:
            outFile.close()
    finally:
        file_in_use_lock.release()

def pop_bak_cached_event():
    bak_file_in_use_lock.acquire()
    events = get_cached_events(is_bak=True, need_lock=False)

    if len(events) > 0:
        e = events[0]
        events = events[1:]
        outFile = None
        try:
            outFile = open(local_cfg_bak_file, 'w')
            json.dump(events, outFile)
            outFile.close()
        except:
            if outFile:
                outFile.close()
    else:
        e = None

    bak_file_in_use_lock.release()

    return e

def do_send_cached_event():
    e = pop_bak_cached_event()
    while(e is not None):
        do_send(e, 0)
        e = pop_bak_cached_event()

def do_http_request(event, event_value):
    ret = False
    conn = None
    try:
        params = get_static_params()
        params[Fields.EVENT_CATEGORY] = event[0]
        params[Fields.EVENT_ACTION]   = event[1]
        params[Fields.EVENT_LABEL]    = event[2]
        params[Fields.EVENT_VALUE]    = '%d' % event_value
        params_str = urllib.urlencode(params)

        socket.setdefaulttimeout(TIMEOUT_VALUE)

        conn = httplib.HTTPConnection(GA_HOST, timeout=TIMEOUT_VALUE)
        conn.request(method="POST", url=GA_PATH, body=params_str)

        response = conn.getresponse()
        res = response.status
        if res >= 200 and res < 300:
            # status is 2xx mean the request is success.
            ret = True
        else:
            ret = False
    except:
        pass
    finally:
        if conn:
            conn.close()

    return ret

def do_send(event, event_value):
    try:
        ret = do_http_request(event, event_value)
        if not ret:
            # request failed, cache the event
            cache_event(event)
    except:
        pass

class Statistic(object):

    MAX_CACHE_EVENTS = 50
    MAX_CACHE_PROC = 5

    def __init__(self):
        self.process_pool = []

    def send_cached_events(self):
        try:
            # get cached events
            events = get_cached_events()
            event_size = len(events)
            if event_size == 0:
                return

            # rename the file
            if os.path.isfile(local_cfg_bak_file):
                os.remove(local_cfg_bak_file)
            os.rename(local_cfg_file, local_cfg_bak_file)

            # create processes to handle the events
            proc_num = min(event_size, Statistic.MAX_CACHE_PROC)
            for i in range(proc_num):
                p = multiprocessing.Process(target=do_send_cached_event)
                p.start()
                self.process_pool.append(p)
        except:
            pass

    def send_event(self, category, action, label):
        try:
            event = [ category, action, label ]
            p = multiprocessing.Process(target=do_send, args=(event, 1,))
            p.start()
            self.process_pool.append(p)
        except:
            pass

    def terminate_stat(self):
        # terminate sub-processes
        if len(self.process_pool) > 0:
            alive_count = 0
            for p in self.process_pool:
                if p.is_alive():
                    alive_count += 1

            if alive_count > 0:
                time.sleep(1)
                for p in self.process_pool:
                    if p.is_alive():
                        p.terminate()

        # remove the backup file
        if os.path.isfile(local_cfg_bak_file):
            os.remove(local_cfg_bak_file)
