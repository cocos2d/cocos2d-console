
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
                return package_data

    @classmethod
    def get_installed_package_zip_path(cls, package_data):
        workdir = cls.get_package_path(package_data)
        return workdir + os.sep + package_data["filename"]

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

