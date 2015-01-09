
import os
import os.path
import zipfile
import sys
import hashlib

import cocos

from time import time
from functions import *

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
                print("==> Error: Could not find the file from url: '%s'" % self._url)
            print("==> Http request failed, error code: " + str(e.code) + ", reason: " + e.read())
            sys.exit(1)

        f = open(self._filename, 'wb')
        file_size = self._zip_file_size
        print("==> Start to download, please wait ...")

        file_size_dl = 0
        block_sz = 8192
        block_size_per_second = 0
        old_time = time()

        while True:
            buf = u.read(block_sz)
            if not buf:
                break

            file_size_dl += len(buf)
            block_size_per_second += len(buf)
            f.write(buf)
            new_time = time()
            if (new_time - old_time) > 1:
                speed = block_size_per_second / (new_time - old_time) / 1000.0
                status = ""
                if file_size != 0:
                    percent = file_size_dl * 100. / file_size
                    status = r"Downloaded: %6dK / Total: %dK, Percent: %3.2f%%, Speed: %6.2f KB/S " % (
                        file_size_dl / 1000, file_size / 1000, percent, speed)
                else:
                    status = r"Downloaded: %6dK, Speed: %6.2f KB/S " % (file_size_dl / 1000, speed)

                status += chr(8) * (len(status) + 1)
                print(status),
                sys.stdout.flush()
                block_size_per_second = 0
                old_time = new_time

        print("==> Downloading finished!")
        f.close()

    def check_file_md5(self):
        if not os.path.isfile(self._filename):
            return False

        block_size = 65536  # 64KB
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

