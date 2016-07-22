#!/usr/bin/env python
# encoding: utf-8

"""
@license: Apache Licence 
@contact: yanli.huang@chukong-inc.com
@author = 'daisy'
@software: PyCharm
@file: cocospackage.py
@time: 16/5/25 上午11:33
"""
import os
import sys
import platform
import zipfile
import time
import subprocess


def _get_currency_path():
    path = ''
    if getattr(sys, 'frozen', None):
        path = os.path.realpath(os.path.dirname(sys.executable))
    else:
        path = os.path.realpath(os.path.dirname(__file__))
    return path

def main():
    #update
    #unzip cocospackage.zip
    name = 'cocospackage.zip'
    currency_path = _get_currency_path()
    file_path = os.path.join(currency_path, name)
    if os.path.isfile(file_path):
        time.sleep(0.5)
        fh = open(file_path, 'rb')
        z = zipfile.ZipFile(fh)
        for n in z.namelist():
            outfile = open(os.path.join(currency_path, n), 'wb')
            try:
                data = z.read(n)
            except:
                raise RuntimeError('failed to find ' + n + 'in archive ' + file_path)
            outfile.write(data)
            outfile.close()
        fh.close()
        os.remove(file_path)

    #import package
    path = ''
    architecture = platform.architecture()[0]
    if '64' in architecture:
        path = os.path.join(currency_path, 'bin', architecture)
    else:
        path = os.path.join(currency_path, 'bin', architecture)
    # download the bin folder
    if not os.path.exists(path):
        download_cmd_path = os.path.join(currency_path, os.pardir, os.pardir)
        subprocess.call("python %s -f -r no" % (os.path.join(download_cmd_path, "download-bin.py")), shell=True, cwd=download_cmd_path)
    sys.path.append(path)
    import package 
    package.main()

if __name__ == '__main__':
    reload(sys)
    sys.setdefaultencoding('utf-8')
    main()
