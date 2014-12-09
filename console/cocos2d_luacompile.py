#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos2d "luacompile" plugin
#
# Copyright 2014 (C) Intel
#
# License: MIT
# ----------------------------------------------------------------------------
'''
"luacompile" plugin for cocos2d command line tool
'''

__docformat__ = 'restructuredtext'

import sys
import subprocess
from contextlib import contextmanager
import os
import json
import inspect
import shutil

import cocos2d

############################################################ 
#http://www.coolcode.org/archives/?article-307.html
############################################################ 

import struct 

_DELTA = 0x9E3779B9  

def _long2str(v, w):  
    n = (len(v) - 1) << 2  
    if w:  
        m = v[-1]  
        if (m < n - 3) or (m > n): return ''  
        n = m  
    s = struct.pack('<%iL' % len(v), *v)  
    return s[0:n] if w else s  
  
def _str2long(s, w):  
    n = len(s)  
    m = (4 - (n & 3) & 3) + n  
    s = s.ljust(m, "\0")  
    v = list(struct.unpack('<%iL' % (m >> 2), s))  
    if w: v.append(n)  
    return v  
  
def encrypt(str, key):  
    if str == '': return str  
    v = _str2long(str, True)  
    k = _str2long(key.ljust(16, "\0"), False)  
    n = len(v) - 1  
    z = v[n]  
    y = v[0]  
    sum = 0  
    q = 6 + 52 // (n + 1)  
    while q > 0:  
        sum = (sum + _DELTA) & 0xffffffff  
        e = sum >> 2 & 3  
        for p in xrange(n):  
            y = v[p + 1]  
            v[p] = (v[p] + ((z >> 5 ^ y << 2) + (y >> 3 ^ z << 4) ^ (sum ^ y) + (k[p & 3 ^ e] ^ z))) & 0xffffffff  
            z = v[p]  
        y = v[0]  
        v[n] = (v[n] + ((z >> 5 ^ y << 2) + (y >> 3 ^ z << 4) ^ (sum ^ y) + (k[n & 3 ^ e] ^ z))) & 0xffffffff  
        z = v[n]  
        q -= 1  
    return _long2str(v, False)  
  
def decrypt(str, key):  
    if str == '': return str  
    v = _str2long(str, False)  
    k = _str2long(key.ljust(16, "\0"), False)  
    n = len(v) - 1  
    z = v[n]  
    y = v[0]  
    q = 6 + 52 // (n + 1)  
    sum = (q * _DELTA) & 0xffffffff  
    while (sum != 0):  
        e = sum >> 2 & 3  
        for p in xrange(n, 0, -1):  
            z = v[p - 1]  
            v[p] = (v[p] - ((z >> 5 ^ y << 2) + (y >> 3 ^ z << 4) ^ (sum ^ y) + (k[p & 3 ^ e] ^ z))) & 0xffffffff  
            y = v[p]  
        z = v[n]  
        v[0] = (v[0] - ((z >> 5 ^ y << 2) + (y >> 3 ^ z << 4) ^ (sum ^ y) + (k[0 & 3 ^ e] ^ z))) & 0xffffffff  
        y = v[0]  
        sum = (sum - _DELTA) & 0xffffffff  
    return _long2str(v, True)  
@contextmanager
def pushd(newDir):
    previousDir = os.getcwd()
    os.chdir(newDir)
    yield
    os.chdir(previousDir)

class CCPluginLuaCompile(cocos2d.CCPlugin):
    """
    compiles (encodes) and minifies Lua files
    """

    @staticmethod
    def brief_description():
        # returns a short description of this module
        return "luacompile\tminifies and/or compiles lua files"

    # This is not the constructor, just an initializator
    def init(self, options, workingdir):
        """
        Arguments:
        - `options`:
        """
        self._current_src_dir = None
        self._src_dir_arr = self.normalize_path_in_list(options.src_dir_arr)
        self._dst_dir = options.dst_dir
        if not os.path.isabs(self._dst_dir):
            self._dst_dir = os.path.abspath(self._dst_dir)
        self._verbose = options.verbose
        self._workingdir = workingdir
        self._lua_files  = {}
        self._isEncrypt = options.encrypt
        self._encryptkey = options.encryptkey
        self._encryptsign = options.encryptsign
        self._disable_compile = options.disable_compile
        self._luajit_exe_path = self.get_luajit_path()
        if self._luajit_exe_path is None:
            raise Exception("Can't find right luajit for current system.")
        self._luajit_dir = os.path.dirname(self._luajit_exe_path)

    def normalize_path_in_list(self, list):
        for i in list:
            tmp = os.path.normpath(i)
            if not os.path.isabs(tmp):
                tmp = os.path.abspath(tmp)
            list[list.index(i)] = tmp
        return list

    def get_relative_path(self, luafile):
        try:
            pos = luafile.index(self._current_src_dir)
            if pos != 0:
                raise Exception("cannot find src directory in file path.")

            return luafile[len(self._current_src_dir)+1:]
        except ValueError:
            raise Exception("cannot find src directory in file path.") 

    def get_output_file_path(self, luafile):
        """
        Gets output file path by source lua file
        """
        # create folder for generated file
        luac_filepath = ""
        # Unknow to remove 'c' 
        relative_path = self.get_relative_path(luafile) + "c"
        luac_filepath = os.path.join(self._dst_dir, relative_path)

        dst_rootpath = os.path.split(luac_filepath)[0]
        try:
            # print "creating dir (%s)" % (dst_rootpath)
            os.makedirs(dst_rootpath)
        except OSError:
            if os.path.exists(dst_rootpath) == False:
                # There was an error on creation, so make sure we know about it
                raise Exception("Error: cannot create folder in " + dst_rootpath)

        # print "return luac path: "+luac_filepath
        return luac_filepath

    def get_luajit_path(self):
        ret = None
        if sys.platform == 'win32':
            ret = os.path.join(self._workingdir, "bin", "luajit.exe")
        elif sys.platform == 'darwin':
            ret = os.path.join(self._workingdir, "bin", "lua", "luajit-mac")
        elif 'linux' in sys.platform:
            ret = os.path.join(self._workingdir, "bin", "lua", "luajit-linux")

        return ret

    def compile_lua(self, lua_file, output_file):
        """
        Compiles lua file
        """
        print("compiling lua (%s) to bytecode..." % lua_file)
        with pushd(self._luajit_dir):

            ret = subprocess.call(self._luajit_exe_path + " -b " + lua_file + " " + output_file, shell=True)
            if ret == 0:
               print("_success " + output_file)
            else:
               print("_failure" + output_file)
            print "----------------------------------------"

    def deep_iterate_dir(self, rootDir):
        for lists in os.listdir(rootDir):
            path = os.path.join(rootDir, lists)
            if os.path.isdir(path):
                self.deep_iterate_dir(path)
            elif os.path.isfile(path):
                if os.path.splitext(path)[1] == ".lua":
                    self._lua_files[self._current_src_dir].append(path)

    def handle_all_lua_files(self):
        """
        Arguments:
        - `self`:
        """

        print "processing lua script files"
        index = 0
        for src_dir in self._src_dir_arr:
            for lua_file in self._lua_files[src_dir]:
                self._current_src_dir = src_dir
                dst_lua_file = self.get_output_file_path(lua_file)
                if self._disable_compile:
                    shutil.copy(lua_file, dst_lua_file)
                else:
                    self.compile_lua(lua_file, dst_lua_file)                   

                if self._isEncrypt == True:
                    bytesFile = open(dst_lua_file, "rb+")
                    encryBytes = encrypt(bytesFile.read(), self._encryptkey)
                    encryBytes = self._encryptsign + encryBytes
                    bytesFile.seek(0)
                    bytesFile.write(encryBytes)
                    bytesFile.close()
                    index = index + 1

    # will be called from the cocos2d.py script
    def run(self, argv):
        """
        """
        self.parse_args(argv)

        # create output directory
        try:
            os.makedirs(self._dst_dir)
        except OSError:
            if os.path.exists(self._dst_dir) == False:
                raise Exception("Error: cannot create folder in "+ self._dst_dir)

        # deep iterate the src directory
        for src_dir in self._src_dir_arr:
            self._current_src_dir = src_dir
            self._lua_files[self._current_src_dir] = []
            self.deep_iterate_dir(src_dir)

        self.handle_all_lua_files()
        print("compilation finished")
        print "------------------------------"

    def parse_args(self, argv):
        """
        """
        from optparse import OptionParser

        parser = OptionParser("usage: %prog luacompile -s src_dir -d dst_dir -v")

        parser.add_option("-v", "--verbose",
                          action="store_true",
                          dest="verbose",
                          help="verbose output")
        parser.add_option("-s", "--src",
                          action="append", type="string", dest="src_dir_arr",
                          help="source directory of lua files needed to be compiled, supports mutiple source directory")
        parser.add_option("-d", "--dst",
                          action="store", type="string", dest="dst_dir",
                          help="destination directory of lua bytecode files to be stored")
        parser.add_option("-e", "--encrypt",
                          action="store_true", dest="encrypt",default=False,
                          help="Whether or not to encrypt")
        parser.add_option("-k", "--encryptkey",
                          dest="encryptkey",default="2dxLua",
                          help="encrypt key")
        parser.add_option("-b", "--encryptsign",
                          dest="encryptsign",default="XXTEA",
                          help="encrypt sign")
        parser.add_option("--disable-compile",
                          action="store_true", dest="disable_compile", default=False,
                          help="Whether or not to compile")

        (options, args) = parser.parse_args(argv)

        # print options
        if options.src_dir_arr == None:
            raise Exception("Please set source folder by \"-s\" or \"-src\", run ./luacompile.py -h for the usage ")
        elif options.dst_dir == None:
            raise Exception("Please set destination folder by \"-d\" or \"-dst\", run ./luacompile.py -h for the usage ")
        else:
            for src_dir in options.src_dir_arr:
                if os.path.exists(src_dir) == False:
                    raise Exception("Error: dir (%s) doesn't exist..." % (src_dir))

        # script directory
        workingdir = os.path.dirname(inspect.getfile(inspect.currentframe()))

        self.init(options, workingdir)

