
import os
import os.path
import json
import re
import shlex

import cocos


class CreateFrameworkHelper(object):

    def __init__(self, project, package_name):
        self._package_name = package_name
        self._package_path = project["packages_dir"] + os.sep + package_name + "-1.0"
        self._vars = {}

    def run(self):
        package_path = self._package_path
        if os.path.isdir(package_path):
            raise cocos.CCPluginError("ERROR: The path '%s' is exist!" % package_path)
        os.makedirs(package_path)

        self._vars["__PACKAGE_NAME__"] = self._package_name

        template_path = os.path.dirname(__file__) + os.sep + "template"

        self.copy_files_from_template(template_path, package_path)
        

    def copy_files_from_template(self, src_dir, dst_dir):
        files = os.listdir(src_dir)
        for filename in files:
            src = src_dir + os.sep + filename
            dst = dst_dir + os.sep + self.get_format_string(filename)
            if os.path.isdir(src):
                os.makedirs(dst)
                self.copy_files_from_template(src, dst)
            else:
                self.copy_file_from_template(src, dst)

    def copy_file_from_template(self, src, dst):
        f = open(src, "rb")
        text = f.read()
        f.close()
        text = self.get_format_string(text)

        f = open(dst, "wb")
        f.write(text)
        f.close()
        print "%s create OK" %dst

    def get_format_string(self, src_str):
        vars = self._vars
        for var in vars:
            src_str = src_str.replace(var, vars[var])

        return src_str
