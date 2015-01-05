# ----------------------------------------------------------------------------
# cocos "package install" plugin
#
# Copyright 2014 (C) cocos2d-x.org
#
# License: MIT
# ----------------------------------------------------------------------------
'''
"package common" for all package plugins
'''

__docformat__ = 'restructuredtext'

# python
import os, os.path
import errno
import zipfile
import sys
import getopt
import ConfigParser
import json
import shutil
import cocos
import cocos_project
import urllib2
import re
import hashlib
from pprint import pprint
from collections import OrderedDict
from time import time
from package_common import *

def ensure_directory(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

class ZipUnpacker(object):
    def __init__(self, filename):
        self._filename = filename

    def unpack(self, extract_dir):
        """Unpack zip `filename` to `extract_dir`

        Raises ``UnrecognizedFormat`` if `filename` is not a zipfile (as determined
        by ``zipfile.is_zipfile()``).
        """

        if not zipfile.is_zipfile(self._filename):
            raise UnrecognizedFormat("%s is not a zip file" % (self._filename))

        print("==> Extracting files, please wait ...")
        z = zipfile.ZipFile(self._filename)
        try:
            for info in z.infolist():
                name = info.filename

                # don't extract absolute paths or ones with .. in them
                if name.startswith('/') or '..' in name:
                    continue

                target = os.path.join(extract_dir, *name.split('/'))
                if not target:
                    continue
                if name.endswith('/'):
                    # directory
                    ensure_directory(target)
                else:
                    # file
                    data = z.read(info.filename)
                    f = open(target,'wb')
                    try:
                        f.write(data)
                    finally:
                        f.close()
                        del data
                unix_attributes = info.external_attr >> 16
                if unix_attributes:
                    os.chmod(target, unix_attributes)
        finally:
            z.close()
            print("==> Extraction done!")


class ZipDownloader(object):
    def __init__(self, url, destdir, package_data, force):
        self._url = url
        self._destdir = destdir
        self._package_data = package_data
        self._force = force
        self._zip_file_size = int(package_data["filesize"])
        self._filename = destdir + os.sep + package_data["filename"]

    def download_file(self):
        print("==> Ready to download '%s' from '%s'" % (self._filename, self._url))
        import urllib2
        try:
            u = urllib2.urlopen(self._url)
        except urllib2.HTTPError as e:
            if e.code == 404:
                print("==> Error: Could not find the file from url: '%s'" % (self._url))
            print("==> Http request failed, error code: " + str(e.code) + ", reason: " + e.read())
            sys.exit(1)

        f = open(self._filename, 'wb')
        meta = u.info()
        content_len = meta.getheaders("Content-Length")
        file_size = 0
        if content_len and len(content_len) > 0:
            file_size = int(content_len[0])
        else:
            # github server may not reponse a header information which contains `Content-Length`,
            # therefore, the size needs to be written hardcode here. While server doesn't return
            # `Content-Length`, use it instead
            print("==> WARNING: Couldn't grab the file size from remote, use 'zip_file_size' section in '%s'" % self._config_path)
            file_size = self._zip_file_size

        print("==> Start to download, please wait ...")

        file_size_dl = 0
        block_sz = 8192
        block_size_per_second = 0
        old_time=time()

        while True:
            buffer = u.read(block_sz)
            if not buffer:
                break

            file_size_dl += len(buffer)
            block_size_per_second += len(buffer)
            f.write(buffer)
            new_time = time()
            if (new_time - old_time) > 1:
                speed = block_size_per_second / (new_time - old_time) / 1000.0
                status = ""
                if file_size != 0:
                    percent = file_size_dl * 100. / file_size
                    status = r"Downloaded: %6dK / Total: %dK, Percent: %3.2f%%, Speed: %6.2f KB/S " % (file_size_dl / 1000, file_size / 1000, percent, speed)
                else:
                    status = r"Downloaded: %6dK, Speed: %6.2f KB/S " % (file_size_dl / 1000, speed)

                status = status + chr(8)*(len(status)+1)
                print(status),
                sys.stdout.flush()
                block_size_per_second = 0
                old_time = new_time

        print("==> Downloading finished!")
        f.close()

    def check_file_md5(self):
        if not os.path.isfile(self._filename):
            return False

        block_size = 65536 # 64KB
        md5 = hashlib.md5()
        f = open(self._filename)
        while True:
            data = f.read(block_size)
            if not data:
                break
            md5.update(data)
        hashcode = md5.hexdigest()
        return hashcode == self._package_data["md5"]

    def download_zip_file(self):
        if os.path.isfile(self._filename):
            if self._force or not self.check_file_md5():
                os.remove(self._filename)
            else:
                print "==> '%s' exists, skip download." % self._filename

        if not os.path.isfile(self._filename):
            self.download_file()

        try:
            if not zipfile.is_zipfile(self._filename):
                raise UnrecognizedFormat("%s is not a zip file" % (self._filename))
        except UnrecognizedFormat as e:
            print("==> Unrecognized zip format from your local '%s' file!" % (self._filename))
            if os.path.isfile(self._filename):
                os.remove(self._filename)
            # print("==> Download it from internet again, please wait...")
            # self.download_zip_file()


    def run(self):
        ensure_directory(self._destdir)
        self.download_zip_file()

class UnrecognizedFormat:
    def __init__(self, prompt):
        self._prompt = prompt
    def __str__(self):
        return self._prompt
