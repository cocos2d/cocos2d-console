#!/usr/bin/python
#coding=utf-8
"""****************************************************************************
Copyright (c) 2013 cocos2d-x.org

http://www.cocos2d-x.org

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
****************************************************************************"""

import sys
import os, os.path
import json
import shutil

def replaceString(filepath, src_string, dst_string):
    """ From file's content replace specified string
    Arg:
        filepath: Specify a file contains the path
        src_string: old string
        dst_string: new string
    """
    content = ""
    f1 = open(filepath, "rb")
    for line in f1:
        strline = line.decode('utf8')
        if src_string in strline:
            content += strline.replace(src_string, dst_string)
        else:
            content += strline
    f1.close()
    f2 = open(filepath, "wb")
    f2.write(content.encode('utf8'))
    f2.close()
#end of replaceString

class CocosProject:
    CPP = 'cpp'
    JS = 'javascript'
    LUA = 'lua'
    DEFAULT_PKG_NAME = {
        CPP :  'org.cocos2dx.mycppgame',
        LUA :  'org.cocos2dx.myluagame',
        JS :  'org.cocos2dx.myjsgame'
    }

    def __init__(self, project_name, project_path):
        """
        """
        self.platforms= {
            "cpp" : ["ios_mac", "android", "win32", "linux"],
            "lua" : ["ios_mac", "android", "win32", "linux"],
            "javascript" : ["ios_mac", "android", "win32", "linux"]
        }

        self.context = {
            "language": None,
            "src_project_name": None,
            "dst_project_name": None,
            "src_project_path": None,
            "dst_project_path": None,
            "src_package_name": None,
            "dst_package_name": None,
            "script_dir": None,
            "cocosx_file_list":None,
            "cocosh5_file_list":None,
        }

        self.context["script_dir"] = os.path.abspath(os.path.dirname(__file__))
        self.context["cocosx_file_list"] = os.path.join(self.context["script_dir"], "cocosx_files.json")
        self.context["cocosxh5_file_list"] = os.path.join(self.context["script_dir"], "cocosh5_files.json")

        self.platforms_list = []
        self.cocos_root =os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
        self.callbackfun = None
        self.totalStep =1
        self.step=0

        self.context["dst_project_name"] = project_name
        self.context["dst_project_path"] = os.path.join(project_path, project_name)

    def _check_dest_project_path(self):
        # copy "lauguage"(cpp/lua/javascript) platform.proj into cocos2d-x/projects/<project_name>/folder
        if os.path.exists(self.context["dst_project_path"]):
            print ("Error:" + self.context["dst_project_path"] + " folder is already existing")
            print ("Please remove the old project or choose a new PROJECT_NAME in -project parameter")
            return False
        return True



    def _copy_template(self, *ignore_files):
        """ copy file from template folder
        Arg:
            ignore_files: 
                the ignored file or folder path relative the template folder.
        """

        print("> Copying template files...")
        shutil.copytree(self.context["src_project_path"], self.context["dst_project_path"], True,
                ignore = _ignorePath(self.context["src_project_path"], ignore_files))
        print ("< done")

    def _copy_files_from_template(self, src, dst):
        full_path = os.path.abspath(os.path.join(self.context["src_project_path"], src))
        shutil.copytree(full_path, dst, True)

    def _copy_h5_engine(self):
        print("> Copying html5 engine files...")
        print ("< done")
        pass

    def _copy_x_engine(self):
        # check cocos engine exist
        if not os.path.exists(self.context["cocosx_file_list"]):
            print ("cocosx_file_list.json doesn\'t exist." \
                "generate it, please")
            return False

        f = open(self.context["cocosx_file_list"])
        fileList = json.load(f)
        f.close()
        self.platforms_list = self.platforms.get(self.context["language"], [])
        self.totalStep = len(self.platforms_list) + len(fileList)
        self.step = 0

        #begin copy engine
        print("> Copying cocos2d files...")
        dstPath = os.path.join(self.context["dst_project_runtime_path"],"cocos2d")
        for index in range(len(fileList)):
            srcfile = os.path.join(self.cocos_root,fileList[index])
            dstfile = os.path.join(dstPath,fileList[index])
            if not os.path.exists(os.path.dirname(dstfile)):
                os.makedirs(os.path.dirname(dstfile))

            #copy file or folder
            if os.path.exists(srcfile):
                if os.path.isdir(srcfile):
                    if os.path.exists(dstfile):
                        shutil.rmtree(dstfile)
                    shutil.copytree(srcfile, dstfile)
                else:
                    if os.path.exists(dstfile):
                        os.remove(dstfile)
                    shutil.copy(srcfile, dstfile)
            self.step = self.step + 1
            if self.callbackfun and self.step%int(self.totalStep/50) == 0:
                self.callbackfun(self.step,self.totalStep,fileList[index])
        print("< done")

    def _process_platform_projects(self, platform):
        """ Process each platform project.
        Arg:
            platform: "ios_mac", "android", "win32", "linux"
        """

        # determine proj_path
        proj_path = os.path.join(self.context["dst_project_runtime_path"], "proj." + platform)
        java_package_path = ""

        # read json config file for the current platform
        conf_path = os.path.join(self.context["script_dir"], "%s.json" % platform)
        f = open(conf_path)
        data = json.load(f)

        # rename package path, like "org.cocos2dx.hello" to "com.company.game". This is a special process for android
        if platform == "android":
            src_pkg = self.context["src_package_name"].split('.')
            dst_pkg = self.context["dst_package_name"].split('.')

            java_package_path = os.path.join(*dst_pkg)

        # rename files and folders
        for item in data["rename"]:
            tmp = item.replace("PACKAGE_PATH", java_package_path)
            src = tmp.replace("PROJECT_NAME", self.context["src_project_name"])
            dst = tmp.replace("PROJECT_NAME", self.context["dst_project_name"])
            if os.path.exists(os.path.join(proj_path, src)):
                os.rename(os.path.join(proj_path, src), os.path.join(proj_path, dst))

        # remove useless files and folders
        for item in data["remove"]:
            dst = item.replace("PROJECT_NAME", self.context["dst_project_name"])
            if os.path.exists(os.path.join(proj_path, dst)):
                shutil.rmtree(os.path.join(proj_path, dst))

        # rename package_name. This should be replaced at first. Don't change this sequence
        for item in data["replace_package_name"]:
            tmp = item.replace("PACKAGE_PATH", java_package_path)
            dst = tmp.replace("PROJECT_NAME", self.context["dst_project_name"])
            if os.path.exists(os.path.join(proj_path, dst)):
                replaceString(os.path.join(proj_path, dst), self.context["src_package_name"], self.context["dst_package_name"])

        # rename project_name
        for item in data["replace_project_name"]:
            tmp = item.replace("PACKAGE_PATH", java_package_path)
            dst = tmp.replace("PROJECT_NAME", self.context["dst_project_name"])
            if os.path.exists(os.path.join(proj_path, dst)):
                replaceString(os.path.join(proj_path, dst), self.context["src_project_name"], self.context["dst_project_name"])

        # done!
        showMsg = ">> Creating proj.%s... OK" % platform
        self.step += 1
        if self.callbackfun:
            self.callbackfun(self.step,self.totalStep,showMsg)
        print (showMsg)
    # end of processPlatformProjects


class NativeProject(CocosProject):
    def __init__(self, project_name, project_path):
        """
        """
        CocosProject.__init__(self, project_name, project_path)

        self.context["src_project_name"] = "HelloCpp"
        self.context["src_package_name"] = "org.cocos2dx.hellocpp"
        self.context["dst_package_name"] = "org.cocos2dx.mycppgame"
        self.context["language"] = CocosProject.CPP
        # fill in src_project_name and src_package_name according to "language"
        template_dir = os.path.abspath(os.path.join(self.cocos_root, "template"))
        self.context["src_project_path"] = os.path.join(template_dir, "multi-platform-cpp")

        # init our internal params
        self.context["dst_project_runtime_path"] = self.context["dst_project_path"]

    def create_platform_projects(self, package_name = None, modules = None, callbackfun = None):

        self.callbackfun = callbackfun
        if package_name:
            self.context["dst_package_name"] = package_name

        if self._check_dest_project_path():
            self._copy_x_engine()
            # call process_proj from each platform's script folder
            print("> Creating project files...")
            for platform in self.platforms_list:
                self._process_platform_projects(platform)
            print("< done")

            print ("")
            print ("A new project was created in:")
            print (self.context["dst_project_path"].replace("\\", "/"))
            return True
        return False

class LuaProject(CocosProject):

    def __init__(self, project_name, project_path):
        """
        """
        CocosProject.__init__(self, project_name, project_path)

        self.context["src_project_name"] = "HelloCpp"
        self.context["src_package_name"] = "org.cocos2dx.hellolua"
        self.context["dst_package_name"] = "org.cocos2dx.myluagame"
        self.context["language"] = CocosProject.LUA

        self.context["dst_project_runtime_path"] = None

        # fill in src_project_name and src_package_name according to "language"
        template_dir = os.path.abspath(os.path.join(self.cocos_root, "template"))
        self.context["src_project_path"] = os.path.join(template_dir, "multi-platform-lua")

        # init our internal params
        self.context["dst_project_runtime_path"] = os.path.join(self.context["dst_project_path"], "libs", "native")


    def create_platform_projects(self, has_native, package_name = None, modules = None, callbackfun = None):

        self.callbackfun = callbackfun

        if self._check_dest_project_path():
            if not has_native:
                self._copy_template("libs/native")
            else:
                self._copy_template()
            if has_native :
                if package_name:
                    self.context["dst_package_name"] = package_name
                print ("> Adding native support")
                self._copy_x_engine()
                print("> Creating project files...")
                for platform in self.platforms_list:
                    self._process_platform_projects(platform)
                print("< done")

                print ("")
                print ("A new project was created in:")
                print (self.context["dst_project_path"].replace("\\", "/"))
                return True
        return False

class JSProject(CocosProject):

    def __init__(self, project_name, project_path):
        """
        """
        CocosProject.__init__(self, project_name, project_path)

        self.context["src_project_name"] = "HelloCpp"
        self.context["src_package_name"] = "org.cocos2dx.hellojavascript"
        self.context["dst_package_name"] = "org.cocos2dx.myjsgame"
        self.context["language"] = CocosProject.JS

        self.context["dst_project_runtime_path"] = None

        # fill in src_project_name and src_package_name according to "language"
        template_dir = os.path.abspath(os.path.join(self.cocos_root, "template"))
        self.context["src_project_path"] = os.path.join(template_dir, "multi-platform-js")

        # init our internal params
        self.context["dst_project_runtime_path"] = os.path.join(self.context["dst_project_path"], "libs", "native")

    def create_platform_projects(self, has_native, package_name = None, modules = None, callbackfun = None):

        self.callbackfun = callbackfun

        if self._check_dest_project_path():
            if not has_native:
                self._copy_template("libs/native")
            else:
                self._copy_template()
            self._copy_h5_engine()
            if has_native :
                if package_name :
                    self.context["dst_package_name"] = package_name
                print ("> Adding native support...")
                self._copy_x_engine()
                print("> Creating project files...")
                for platform in self.platforms_list:
                    self._process_platform_projects(platform)
                print("< done")

                print ("")
                print ("A new project was created in:")
                print (self.context["dst_project_path"].replace("\\", "/"))
                return True
        return False

def _ignorePath(root, ignore_files):
    def __ignoref(p, files):
        ignore_list = []
        for f in files:
            for igf in ignore_files:
                f1 = os.path.abspath(os.path.join(p, f))
                f2 = os.path.abspath(os.path.join(root, igf))
                if f1 == f2:
                    ignore_list.append(f)
        return ignore_list
    return __ignoref

def create_platform_projects(
        language,
        project_name,
        project_path,
        package_name = None,
        has_native = False,
        modules = None,
        callbackfun = None):

    breturn = False
    if(CocosProject.CPP == language):
        project = NativeProject(project_name, project_path)
        breturn = project.create_platform_projects(package_name, modules, callbackfun)
    elif(CocosProject.LUA == language):
        project = LuaProject(project_name, project_path)
        breturn = project.create_platform_projects(has_native, package_name, modules, callbackfun)
    elif(CocosProject.JS == language):
        project = JSProject(project_name, project_path)
        breturn = project.create_platform_projects(has_native, package_name, modules, callbackfun)
    return breturn

