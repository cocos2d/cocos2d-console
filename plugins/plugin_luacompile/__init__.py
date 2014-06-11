#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos "luacompile" plugin
#
# Copyright 2013 (C) Intel
#
# License: MIT
# ----------------------------------------------------------------------------

'''
"luacompile" plugin for cocos command line tool
'''

__docformat__ = 'restructuredtext'

import sys
import subprocess
import os
import json
import inspect

import cocos

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



#import cocos
class CCPluginLuaCompile(cocos.CCPlugin):
    """
    compiles (encodes) and minifies Lua files
    """
    @staticmethod
    def plugin_name():
        return "luacompile"

    @staticmethod
    def brief_description():
        # returns a short description of this module
        return "minifies and/or compiles lua files"

    # This is not the constructor, just an initializator
    def init(self, options, workingdir):
        """
        Arguments:
        - `options`:
        """
        self._current_src_dir = None
        self._src_dir_arr = self.normalize_path_in_list(options.src_dir_arr)
        self._dst_dir = options.dst_dir
        self._verbose = options.verbose
        self._workingdir = workingdir
        self._lua_files = {}
        self._isEncrypt = options.encrypt
        self._encryptkey = options.encryptkey
        self._encryptsign = options.encryptsign
        self._luajit_exe_path = self.get_luajit_path()

        if self._luajit_exe_path is None:
            raise cocos.CCPluginError("Can't find right luajit for current system.")

        self._luajit_dir = os.path.dirname(self._luajit_exe_path)

    def normalize_path_in_list(self, list):
        for i in list:
            tmp = os.path.normpath(i)
            list[list.index(i)] = tmp
        return list

    def get_relative_path(self, luafile):
        try:
            pos = luafile.index(self._current_src_dir)
            if pos != 0:
                raise cocos.CCPluginError("cannot find src directory in file path.")

            return luafile[len(self._current_src_dir)+1:]
        except ValueError:
            raise cocos.CCPluginError("cannot find src directory in file path.") 

    def get_output_file_path(self, luafile):
        """
        Gets output file path by source lua file
        """
        # create folder for generated file
        luac_filepath = ""
        # Unknow to remove 'c' 
        relative_path = self.get_relative_path(luafile)+"c"
        luac_filepath = os.path.join(self._dst_dir, relative_path)

        dst_rootpath = os.path.split(luac_filepath)[0]
        try:
            # print "creating dir (%s)" % (dst_rootpath)
            os.makedirs(dst_rootpath)
        except OSError:
            if os.path.exists(dst_rootpath) == False:
                # There was an error on creation, so make sure we know about it
                raise cocos.CCPluginError("Error: cannot create folder in "+dst_rootpath)

        # print "return luac path: "+luac_filepath
        return luac_filepath

    def get_luajit_path(self):
        ret = None
        if cocos.os_is_win32():
            ret = os.path.join(self._workingdir, "bin", "luajit.exe")
        elif cocos.os_is_mac():
            ret = os.path.join(self._workingdir, "bin", "lua", "luajit-mac")
        elif cocos.os_is_linux():
            ret = os.path.join(self._workingdir, "bin", "lua", "luajit-linux")

        return ret

    def compile_lua(self, lua_file, output_file):
        """
        Compiles lua file
        """
        cocos.Logging.debug("compiling lua (%s) to bytecode..." % lua_file)

        with cocos.pushd(self._luajit_dir):
            self._run_cmd(self._luajit_exe_path + " -b " + lua_file+ " " + output_file)

    # TODO
    # def compress_js(self):
    def deep_iterate_dir(self, rootDir):
        for lists in os.listdir(rootDir):
            path = os.path.join(rootDir, lists)
            if os.path.isdir(path):
                self.deep_iterate_dir(path)
            elif os.path.isfile(path):
                if os.path.splitext(path)[1] == ".lua":
                    self._lua_files[self._current_src_dir].append(path)

    # UNDO
    # def index_in_list(self, lua_file, l):
    # def lua_filename_pre_order_compare(self, a, b):
    # def lua_filename_post_order_compare(self, a, b):
    # def _lua_filename_compare(self, a, b, files, delta):
    # def reorder_lua_files(self):

    def handle_all_lua_files(self):
        """
        Arguments:
        - `self`:
        """

        cocos.Logging.info("compiling lua script files to bytecode")
        index = 0
        for src_dir in self._src_dir_arr:
            for lua_file in self._lua_files[src_dir]:
                self._current_src_dir = src_dir
                dst_lua_file = self.get_output_file_path(lua_file)
                self.compile_lua(lua_file, dst_lua_file)
                if self._isEncrypt == True:
                    bytesFile = open(dst_lua_file, "rb+")
                    encryBytes = encrypt(bytesFile.read(), self._encryptkey)
                    encryBytes = self._encryptsign + encryBytes
                    bytesFile.seek(0)
                    bytesFile.write(encryBytes)
                    bytesFile.close()
                    index = index + 1



    def run(self, argv, dependencies):
        """
        """
        self.parse_args(argv)

        # create output directory
        try:
            os.makedirs(self._dst_dir)
        except OSError:
            if os.path.exists(self._dst_dir) == False:
                raise cocos.CCPluginError("Error: cannot create folder in " + self._dst_dir)

        # deep iterate the src directory
        for src_dir in self._src_dir_arr:
            self._current_src_dir = src_dir
            self._lua_files[self._current_src_dir] = []
            self.deep_iterate_dir(src_dir)

        self.handle_all_lua_files()

        cocos.Logging.info("compilation finished")

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

        (options, args) = parser.parse_args(argv)

        if options.src_dir_arr == None:
            raise cocos.CCPluginError("Please set source folder by \"-s\" or \"-src\", run ./luacompile.py -h for the usage ")
        elif options.dst_dir == None:
            raise cocos.CCPluginError("Please set destination folder by \"-d\" or \"-dst\", run ./luacompile.py -h for the usage ")
        else:
            for src_dir in options.src_dir_arr:
                if os.path.exists(src_dir) == False:
                    raise cocos.CCPluginError("Error: dir (%s) doesn't exist..." % (src_dir))

        # script directory
        workingdir = os.path.dirname(inspect.getfile(inspect.currentframe()))

        self.init(options, workingdir)








