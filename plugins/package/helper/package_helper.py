
import os
import os.path
import json
import urllib2

import cocos

from functions import *
from local_package_database import LocalPackagesDatabase
from zip_downloader import ZipDownloader

class PackageHelper:
    REPO_URL = "http://pmr.cocos.com/"
    REPO_PACKAGES_DIR = "packages"
    WORKDIR = ".cocos" + os.sep + "packages"
    LOCALDB_FILENAME = "local_packages.json"
    QUERY_PACKAGE_URL = REPO_URL + "?name=%s"
    QUERY_KEYWORD_URL = REPO_URL + "?keyword=%s"

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
        # print "[PACKAGE] query url: %s" % url
        response = urllib2.urlopen(url)
        html = response.read()
        packages_data = json.loads(html)
        if packages_data is None or len(packages_data) == 0:
            return None

        if "err" in packages_data:
            message = "error: %s, code %s" % (packages_data["err"], packages_data["code"])
            raise cocos.CCPluginError(message)

        return packages_data

    @classmethod
    def query_package_data(cls, name):
        url = cls.QUERY_PACKAGE_URL % name
        # print "[PACKAGE] query url: %s" % url
        response = urllib2.urlopen(url)
        html = response.read()
        package_data = json.loads(html)
        if package_data is None or ("err" in package_data and package_data["code"] == "1002"):
            return None

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
        keys.reverse()
        for key in keys:
            package_data = packages[key]
            if package_data["name"] == package_name:
                return package_data

    @classmethod
    def get_installed_package_zip_path(cls, package_data):
        workdir = cls.get_package_path(package_data)
        return workdir + os.sep + package_data["filename"]
