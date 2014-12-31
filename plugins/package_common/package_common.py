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
import os
import os.path,zipfile
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

def ensure_directory(target):
    if not os.path.exists(target):
        os.mkdir(target)


class PackageHelper:
    REPO_URL = "http://quick.cocos.org/downloads/test/"
    REPO_PACKAGES_DIR = "packages"
    WORKDIR = ".cocos_packages"
    LOCALDB_FILENAME = "local_packages.json"
    QUERY_PACKAGE_URL = REPO_URL + "get_package_data.php?name=%s"
    QUERY_KEYWORD_URL = REPO_URL + "search.php?keyword=%s"

    @classmethod
    def get_workdir(cls):
        home = os.path.expanduser("~").rstrip("/\\")
        return home + os.sep + cls.WORKDIR

    @classmethod
    def get_local_database_path(cls):
        return cls.get_workdir() + os.sep + cls.LOCALDB_FILENAME

    @classmethod
    def get_package_path(cls, package_data):
        return cls.get_workdir() + os.sep + package_data["name"] + "-" + package_data["version"]

    @classmethod
    def search_keyword(cls, keyword):
        url = cls.QUERY_KEYWORD_URL % keyword
        print "[PACKAGE] query url: %s" % url
        response = urllib2.urlopen(url)
        html = response.read()
        packages_data = json.loads(html)
        if packages_data is None:
            return False

        if "err" in packages_data:
            message = "error: %s, code %s" % (packages_data["err"], packages_data["code"])
            raise cocos.CCPluginError(message)

        return packages_data

    @classmethod
    def query_package_data(cls, name):
        url = cls.QUERY_PACKAGE_URL % name
        print "[PACKAGE] query url: %s" % url
        response = urllib2.urlopen(url)
        html = response.read()
        package_data = json.loads(html)
        if package_data is None:
            return False

        if "err" in package_data:
            message = "error: %s, code %s" % (package_data["err"], package_data["code"])
            raise cocos.CCPluginError(message)

        return package_data

    @classmethod
    def download_package_zip(cls, package_data, force):
        download_url = cls.REPO_URL + cls.REPO_PACKAGES_DIR + "/" + package_data["filename"]
        workdir = cls.get_package_path(package_data)
        print "[PACKAGE] workdir: %s" % workdir
        downloader = ZipDownloader(download_url, workdir, package_data, force)
        downloader.run()

    @classmethod
    def add_package(cls, package_data):
        localdb = LocalPackagesDatabase(cls.get_local_database_path())
        localdb.add_package(package_data)

    @classmethod
    def get_installed_packages(cls):
        localdb = LocalPackagesDatabase(cls.get_local_database_path())
        return localdb.get_packages()

    @classmethod
    def get_installed_package_data(cls, package_name):
        localdb = LocalPackagesDatabase(cls.get_local_database_path())
        packages = localdb.get_packages()
        keys = packages.keys()
        keys.sort()
        for key in keys:
            package_data = packages[key]
            if package_data["name"] == package_name:
                json_path = cls.get_package_path(package_data) + os.sep + package_name + os.sep + "package.json"
                f = open(json_path, "rb")
                package_data = json.load(f)
                f.close()
                return package_data


class LocalPackagesDatabase(object):
    def __init__(self, path):
        self._path = path
        if os.path.isfile(self._path):
            f = open(self._path, "rb")
            self._data = json.load(f)
            f.close()
        else:
            self._data = {}

    def get_packages(self):
        return self._data.copy()

    def add_package(self, package_data):
        key = package_data["name"] + "-" + package_data["version"]
        self._data[key] = package_data
        self.update_database()
        print "[PACKAGE] add package '%s' ok." % key

    def remove_package(self, package_name):
        key = package_data["name"] + "-" + package_data["version"]
        if key in self._data:
            del self._data[key]
            self.update_database()
            print "[PACKAGE] remove package '%s' ok." % key
        else:
            message = "Fatal: not found specified package '%s'" % key
            raise cocos.CCPluginError(message)

    def update_database(self):
        f = open(self._path, "w+b")
        str = json.dump(self._data, f)
        f.close()
        print "[PACKAGE] update '%s' ok." % self._path

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

    def unpack_zipfile(self, extract_dir):
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
            print("==> Download it from internet again, please wait...")
            self.download_zip_file()


    def run(self):
        ensure_directory(self._destdir)
        self.download_zip_file()
        self.unpack_zipfile(self._destdir)

class UnrecognizedFormat:
    def __init__(self, prompt):
        self._prompt = prompt
    def __str__(self):
        return self._prompt
