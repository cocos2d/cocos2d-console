#!/usr/bin/python
#-*- coding: utf-8 -*-

import os
import sys
import shutil
import cocos
import re

def get_msbuild_path(vs_version):
    if cocos.os_is_win32():
        import _winreg
    else:
        return None

    if vs_version == 2013:
        vs_ver = "12.0"
    elif vs_version == 2015:
        vs_ver = "14.0"
    else:
        # not supported VS version
        return None

    # If the system is 64bit, find VS in both 32bit & 64bit registry
    # If the system is 32bit, only find VS in 32bit registry
    if cocos.os_is_32bit_windows():
        reg_flag_list = [ _winreg.KEY_WOW64_32KEY ]
    else:
        reg_flag_list = [ _winreg.KEY_WOW64_64KEY, _winreg.KEY_WOW64_32KEY ]

    # Find VS path
    msbuild_path = None
    for reg_flag in reg_flag_list:
        try:
            vs = _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\MSBuild\ToolsVersions\%s" % vs_ver,
                0,
                _winreg.KEY_READ | reg_flag
            )
            msbuild_path, type = _winreg.QueryValueEx(vs, 'MSBuildToolsPath')
        except:
            continue

        if msbuild_path is not None and os.path.exists(msbuild_path):
            break

    # generate msbuild path
    if msbuild_path is not None:
        commandPath = os.path.join(msbuild_path, "MSBuild.exe")
    else:
        commandPath = None

    return commandPath

def rmdir(folder):
    if os.path.exists(folder):
        if sys.platform == 'win32':
            cocos.CMDRunner.run_cmd("rd /s/q \"%s\"" % folder, verbose=True)
        else:
            shutil.rmtree(folder)

VERSION_FILE_PATH = 'cocos/cocos2d.cpp'
VERSION_PATTERN = r".*return[ \t]+\"(.*)\";"
def get_engine_version(engine_path):
    ret = None

    try:
        version_file = os.path.join(engine_path, VERSION_FILE_PATH)
        if os.path.isfile(version_file):
            f = open(version_file)
            for line in f.readlines():
                match = re.match(VERSION_PATTERN, line)
                if match:
                    ret = match.group(1)
                    break
            f.close()
    except:
        pass

    return ret
