#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos "new" plugin
#
# Copyright 2013 (C) cocos2d-x.org
#
# License: MIT
# ----------------------------------------------------------------------------
'''
"new" plugin for cocos command line tool
'''

__docformat__ = 'restructuredtext'

# python
import os
import sys
import getopt
import ConfigParser
import json
import shutil
import cocos
import cocos_project
import re


#
# Plugins should be a sublass of CCJSPlugin
#
class CCPluginNew(cocos.CCPlugin):

    DEFAULT_PROJ_NAME = {
        cocos_project.Project.CPP : 'MyCppGame',
        cocos_project.Project.LUA : 'MyLuaGame',
        cocos_project.Project.JS : 'MyJSGame'
    }

    DEFAULT_PKG_NAME = {
        cocos_project.Project.CPP : 'org.cocos2dx.hellocpp',
        cocos_project.Project.LUA : 'org.cocos2dx.hellolua',
        cocos_project.Project.JS : 'org.cocos2dx.hellojavascript'
    }

    @staticmethod
    def plugin_name():
      return "new"

    @staticmethod
    def brief_description():
        return "Creates a new project"

    def init(self, args):
        self._projname = args.name
        self._projdir = os.path.abspath(os.path.join(args.directory, self._projname))
        self._lang = args.language
        self._package = args.package
        self._tpname = args.template
        self._cocosroot, self._templates_root = self._parse_cfg(self._lang)
        self._other_opts = args

        self._templates = Templates(args.language, self._templates_root, args.template)
        if self._templates.none_active():
            self._templates.select_one()

    # parse arguments
    def parse_args(self, argv):
        """Custom and check param list.
        """
        from argparse import ArgumentParser
        # set the parser to parse input params
        # the correspond variable name of "-x, --xxx" is parser.xxx
        name = CCPluginNew.plugin_name()
        category = CCPluginNew.plugin_category()
        parser = ArgumentParser(prog="cocos %s" % self.__class__.plugin_name(),
                                description=self.__class__.brief_description())
        parser.add_argument("name", metavar="PROJECT_NAME", nargs='?', help="Set the project name")
        parser.add_argument("-p", "--package", metavar="PACKAGE_NAME",help="Set a package name for project")
        parser.add_argument("-l", "--language",
                            required=True,
                            choices=["cpp", "lua", "js"],
                            help="Major programming language you want to use, should be [cpp | lua | js]")
        parser.add_argument("-d", "--directory", metavar="DIRECTORY",help="Set generate project directory for project")
        parser.add_argument("-t", "--template", metavar="TEMPLATE_NAME",help="Set the template name you want create from")
        
        group = parser.add_argument_group("lua/js project arguments")
        group.add_argument("--no-native", action="store_true", dest="no_native", help="No native support.")

        # parse the params
        args = parser.parse_args(argv)

        if args.name is None:
            args.name = CCPluginNew.DEFAULT_PROJ_NAME[args.language]
        
        if not args.package:
            args.package = CCPluginNew.DEFAULT_PKG_NAME[args.language]

        if not args.directory:
            args.directory = os.getcwd();

        if not args.template:
            args.template = 'default'

        self.init(args)

        return args

    def _create_from_cmd(self):
        #check the dst project dir exists
        if os.path.exists(self._projdir):
            message = "Fatal: %s folder is already exist" % self._projdir
            raise cocos.CCPluginError(message)

        tp_dir = self._templates.template_path()

        creator = TPCreator(self._lang, self._cocosroot, self._projname, self._projdir, self._tpname, tp_dir, self._package)
        # do the default creating step
        creator.do_default_step()

        data = None
        cfg_path = os.path.join(self._projdir, cocos_project.Project.CONFIG)
        if os.path.isfile(cfg_path):
            f = open(cfg_path)
            data = json.load(f)
            f.close()

        if data is None:
            data = {}

        if not data.has_key(cocos_project.Project.KEY_PROJ_TYPE):
            data[cocos_project.Project.KEY_PROJ_TYPE] = self._lang

        # script project may add native support
        if self._lang in (cocos_project.Project.LUA, cocos_project.Project.JS):
            if not self._other_opts.no_native:
                creator.do_other_step('do_add_native_support')
                data[cocos_project.Project.KEY_HAS_NATIVE] = True
            else:
                data[cocos_project.Project.KEY_HAS_NATIVE] = False

        # write config files
        with open(cfg_path, 'w') as outfile:
            json.dump(data, outfile, sort_keys = True, indent = 4)


    def _parse_cfg(self, language):
        self.script_dir= os.path.abspath(os.path.dirname(__file__))
        self.create_cfg_file = os.path.join(self.script_dir, "env.json")
        
        f = open(self.create_cfg_file)
        create_cfg = json.load(f)
        f.close()
        langcfg = create_cfg[language]
        langcfg['COCOS_ROOT'] = os.path.abspath(os.path.join(self.script_dir,langcfg["COCOS_ROOT"]))
        cocos_root = langcfg['COCOS_ROOT']
        
        # replace SDK_ROOT to real path
        for k, v in langcfg.iteritems():
            if 'COCOS_ROOT' in v:
                v = v.replace('COCOS_ROOT', cocos_root)
                langcfg[k] = v
        
        #get the real json cfgs
        templates_root = langcfg['templates_root']

        return cocos_root, templates_root

    # main entry point
    def run(self, argv, dependencies):
        self.parse_args(argv);
        self._create_from_cmd()


# ignore files function generator
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


# copy the whole things from one dir into a dir
# the dst dir will be created, if the dst dir is not exists
def copytree(src, dst, symlinks=False, ignore=None):
    # make sure dst is exists
    if not os.path.exists(dst):
         os.makedirs(dst)

    root_ignorefiles = []
    if ignore is not None:
        root_ignorefiles = ignore(src, os.listdir(src))
    for item in os.listdir(src):
        if item in root_ignorefiles:
            continue
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)

def replace_string(filepath, src_string, dst_string):
    """ From file's content replace specified string
    Arg:
        filepath: Specify a file contains the path
        src_string: old string
        dst_string: new string
    """
    if src_string is None or dst_string is None:
        raise TypeError

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
#end of replace_string

class Templates(object):

    def __init__(self, lang, templates_dir, current):
        self._lang = lang
        self._templates_dir =  templates_dir
        self._scan()
        self._current = None
        if current is not None:
            if self._template_folders.has_key(current):
                self._current = current
            else:
                cocos.Logging.warning("Template named '%s' is not found" % current)

    def _scan(self):
        templates_dir = self._templates_dir
        dirs =  [ name for name in os.listdir(templates_dir) if os.path.isdir(os.path.join(templates_dir, name)) ]
        template_pattern = {
                "cpp" : 'cpp-template-(.+)',
                "lua" : 'lua-template-(.+)',
                "js" : 'js-template-(.+)',
                }
        pattern = template_pattern[self._lang]
        valid_dirs = [ name for name in dirs if re.search(pattern, name) is not None]

        # store the template dir full path, eg. { 'name' : 'full_path'}
        folders = {re.search(pattern, path).group(1) : os.path.join(templates_dir, path) for path in valid_dirs}
        self._template_folders = folders

        if len(folders) == 0:
            message = "Fatal: can't find any template for <%s> language in %s" % (self._lang, templates_dir)
            raise cocos.CCPluginError(message)


    def none_active(self):
        return self._current is None

    def template_path(self):
        if self._current is None:
            return None
        return self._template_folders[self._current]

    def select_one(self):
        cocos.Logging.warning('Multiple templates detected!')
        cocos.Logging.warning("You can select one via command line arguments (-h to see the options)")
        cocos.Logging.warning('Or choose one now:\n')

        p = self._template_folders.keys()
        for i in range(len(p)):
            cocos.Logging.warning('%d %s' % (i + 1, p[i]))
        cocos.Logging.warning("Select one (input number and press enter): ")
        while True:
            option = raw_input()
            if option.isdigit():
                option = int(option) - 1
                if option in range(len(p)):
                    break

        self._current = p[option]


class TPCreator(object):
    def __init__(self, lang, cocos_root, project_name, project_dir, tp_name, tp_dir, project_package):
        self.lang = lang
        self.cocos_root = cocos_root
        self.project_dir = project_dir
        self.project_name = project_name
        self.package_name = project_package

        self.tp_name = tp_name
        self.tp_dir = tp_dir
        self.tp_json = 'cocos-project-template.json'

        tp_json_path = os.path.join(tp_dir, self.tp_json)
        if not os.path.exists(tp_json_path):
            message = "Fatal: '%s' not found" % tp_json_path
            raise cocos.CCPluginError(message)

        f = open(tp_json_path)
        # keep the key order
        from collections import OrderedDict
        tpinfo = json.load(f, encoding='utf8', object_pairs_hook=OrderedDict)

        # read the default creating step
        if not tpinfo.has_key('do_default'):
            message = ("Fatal: the '%s' dosen't has 'do_default' creating step, it must defined."
                        % tp_json_path)
            raise cocos.CCPluginError(message)
        self.tp_default_step = tpinfo.pop('do_default')
        # keep the other steps
        self.tp_other_step = tpinfo

    def cp_self(self, project_dir, exclude_files):
        cocos.Logging.info('> Copy template into %s' % project_dir)
        shutil.copytree(self.tp_dir, self.project_dir, True,
                ignore = _ignorePath(self.tp_dir, exclude_files) )


    def do_default_step(self):
        default_cmds = self.tp_default_step
        exclude_files = []
        if default_cmds.has_key("exclude_from_template"):
            exclude_files = exclude_files + default_cmds['exclude_from_template']
            default_cmds.pop('exclude_from_template')

        # should ignore teh xx-template-xx.json
        exclude_files.append(self.tp_json)
        self.cp_self(self.project_dir, exclude_files)
        self.do_cmds(default_cmds)
    
    def do_other_step(self, step):
        if not self.tp_other_step.has_key(step):
            message = "Fatal: creating step '%s' is not found" % step
            raise cocos.CCPluginError(message)

        cmds = self.tp_other_step[step]
        self.do_cmds(cmds)


    def do_cmds(self, cmds):
        for k, v in cmds.iteritems():
            # call cmd method by method/cmd name
            # get from http://stackoverflow.com/questions/3951840/python-how-to-invoke-an-function-on-an-object-dynamically-by-name
            try:
                cmd = getattr(self, k)
            except AttributeError:
                raise cocos.CCPluginError("cmd = %s is not found" % k)

            try:
                cmd(v)
            except Exception as e:
                raise cocos.CCPluginError(str(e))

## cmd methods below
    def append_h5_engine(self, v):
        src = os.path.join(self.cocos_root, v['from'])
        dst = os.path.join(self.project_dir, v['to'])
        # check cocos engine exist
        moduleConfig = 'moduleConfig.json'
        moudle_cfg = os.path.join(src, moduleConfig)
        if not os.path.exists(moudle_cfg):
            message ="Fatal: %s doesn't exist." % moudle_cfg
            raise cocos.CCPluginError(message)

        f = open(moudle_cfg)
        data = json.load(f, 'utf8')
        f.close()
        modules = data['module'] 

        # must copy moduleConfig.json & CCBoot.js
        file_list = [moduleConfig, data['bootFile']]
        for k, v in modules.iteritems():
            module = modules[k]
            for f in module:
                if f[-2:] == 'js':
                    file_list.append(f)

        #begin copy engine
        cocos.Logging.info("> Copying cocos2d-html5 files...")
        for index in range(len(file_list)):
            srcfile = os.path.join(src,file_list[index])
            dstfile = os.path.join(dst,file_list[index])
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
                    shutil.copy2(srcfile, dstfile)


    def append_x_engine(self, v):
        src = os.path.join(self.cocos_root, v['from'])
        dst = os.path.join(self.project_dir, v['to'])

        # check cocos engine exist
        cocosx_files_json = os.path.join(src, 'templates', 'cocos2dx_files.json')
        if not os.path.exists(cocosx_files_json):
            message = "Fatal: %s doesn\'t exist." % cocosx_files_json
            raise cocos.CCPluginError(message)

        f = open(cocosx_files_json)
        data = json.load(f)
        f.close()

        fileList = data['common']
        if self.lang == 'lua':
            fileList = fileList + data['lua']

        #begin copy engine
        cocos.Logging.info("> Copying cocos2d-x files...")

        for index in range(len(fileList)):
            srcfile = os.path.join(src,fileList[index])
            dstfile = os.path.join(dst,fileList[index])
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
                    shutil.copy2(srcfile, dstfile)


    def append_from_template(self, v):
        cocos.Logging.info('> Copying files from template directory...')
        src = os.path.join(self.tp_dir, v['from'])
        dst = os.path.join(self.project_dir, v['to'])
        exclude_files = v.get('exclude', [])
        if os.path.exists(src):
            shutil.copytree(src, dst, True, ignore = _ignorePath(src, exclude_files))


    def append_dir(self, v):
        cocos.Logging.info('> Copying directory from cocos root directory...')
	for item in v:
            src = os.path.join(self.cocos_root, item['from'])
            dst = os.path.join(self.project_dir, item['to'])
            exclude_files = item.get('exclude', [])
            copytree(src, dst, True, ignore = _ignorePath(src, exclude_files))

    def append_file(self, v):
        cocos.Logging.info('> Copying files from cocos root directory...')
        for item in v:
            src = os.path.join(self.cocos_root, item['from'])
            dst = os.path.join(self.project_dir, item['to'])
            shutil.copy2(src, dst)

## project cmd
    def project_rename(self, v):
        """ will modify the file name of the file
        """
        dst_project_dir = self.project_dir
        dst_project_name = self.project_name
        src_project_name = v['src_project_name']
        cocos.Logging.info("> Rename project name from '%s' to '%s'" % (src_project_name, dst_project_name))
        files = v['files']
        for f in files:
            src = f.replace("PROJECT_NAME", src_project_name)
            dst = f.replace("PROJECT_NAME", dst_project_name)
            if os.path.exists(os.path.join(dst_project_dir, src)):
                os.rename(os.path.join(dst_project_dir, src), os.path.join(dst_project_dir, dst))
            else:
                cocos.Logging.warning("%s not found" % os.path.join(dst_project_dir, src))

    def project_replace_project_name(self, v):
        """ will modify the content of the file
        """
        dst_project_dir = self.project_dir
        dst_project_name = self.project_name
        src_project_name = v['src_project_name']
        cocos.Logging.info("> Replace the project name from '%s' to '%s'" % (src_project_name, dst_project_name))
        files = v['files']
        for f in files:
            dst = f.replace("PROJECT_NAME", dst_project_name)
            if os.path.exists(os.path.join(dst_project_dir, dst)):
                replace_string(os.path.join(dst_project_dir, dst), src_project_name, dst_project_name)
            else:
                cocos.Logging.warning("%s not found" % os.path.join(dst_project_dir, dst))

    def project_replace_package_name(self, v):
        """ will modify the content of the file
        """
        dst_project_dir = self.project_dir
        dst_project_name = self.project_name
        src_package_name = v['src_package_name']
        dst_package_name = self.package_name
        cocos.Logging.info("> Replace the project package name from '%s' to '%s'" % (src_package_name, dst_package_name))
        files = v['files']
        if not dst_package_name:
            raise cocos.CCPluginError('package name not specified')
        for f in files:
            dst = f.replace("PROJECT_NAME", dst_project_name)
            if os.path.exists(os.path.join(dst_project_dir, dst)):
                replace_string(os.path.join(dst_project_dir, dst), src_package_name, dst_package_name)
            else:
                cocos.Logging.warning("%s not found" % os.path.join(dst_project_dir, dst))


