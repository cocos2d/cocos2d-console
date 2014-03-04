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


#
# Plugins should be a sublass of CCJSPlugin
#
class CCPluginNew(cocos.CCPlugin):

    DEFAULT_PROJ_NAME = {
        cocos.Project.CPP : 'MyCppGame',
        cocos.Project.LUA : 'MyLuaGame',
        cocos.Project.JS : 'MyJSGame'
    }

    @staticmethod
    def plugin_category():
      return "project"

    @staticmethod
    def plugin_name():
      return "new"

    @staticmethod
    def brief_description():
        return "creates a new project"

    # parse arguments
    def parse_args(self, argv):
        """Custom and check param list.
        """
        from optparse import OptionParser
        # set the parser to parse input params
        # the correspond variable name of "-x, --xxx" is parser.xxx
        name = CCPluginNew.plugin_name()
        category = CCPluginNew.plugin_category()
        parser = OptionParser(
            usage=
            "\n\t%%prog %s %s, start GUI version."
            "\n\t%%prog %s %s <PROJECT_NAME> -p <PACKAGE_NAME> -l <cpp|lua|javascript> -d <PROJECT_DIR>"
            "\nSample:"
            "\n\t%%prog %s %s MyGame -p com.MyCompany.AwesomeGame -l javascript -d c:/mycompany" \
                    % (category, name, category, name, category, name)
        )
        parser.add_option("-p", "--package", metavar="PACKAGE_NAME",help="Set a package name for project")
        parser.add_option("-l", "--language",metavar="PROGRAMMING_NAME",
                            type="choice",
                            choices=["cpp", "lua", "javascript"],
                            help="Major programming language you want to use, should be [cpp | lua | javascript]")
        parser.add_option("-d", "--directory", metavar="DIRECTORY",help="Set generate project directory for project")
        parser.add_option("-t", "--template", metavar="TEMPLATE_NAME",help="Set the template name you want create from")
        parser.add_option("--gui", action="store_true", help="Start GUI")
        parser.add_option("--has-native", action="store_true", dest="has_native", help="Has native support.")

        # parse the params
        (opts, args) = parser.parse_args(argv)

        if not opts.language:
            opts.language = cocos.Project.CPP

        if len(args) == 0:
            self.project_name = CCPluginNew.DEFAULT_PROJ_NAME[opts.language]
        else:
            self.project_name = args[0]

        if not opts.directory:
            opts.directory = os.getcwd();

        if not opts.template:
            opts.template = 'default'

        return opts


    def _create_from_ui(self, opts):
        from ui import createTkCocosDialog
        createTkCocosDialog()

    def _create_from_cmd(self, opts):

        self._parse_cfg(opts.language)


        if opts.language == 'cpp':
            if not opts.package:
                raise cocos.CCPluginError('package_name is not specified!')
        
        if opts.language == 'lua' or opts.language == 'javascript':
            # do add native support
            if opts.has_native:
                if not opts.package:
                    raise cocos.CCPluginError('package_name is not specified!')

        # read the templates.json
        templates_json = os.path.abspath(os.path.join(self.langcfg['templates_dir'], 'templates.json'))
        f = open(templates_json)
        # keep the key order
        from collections import OrderedDict
        templates_info = json.load(f, encoding='utf8', object_pairs_hook=OrderedDict)

        # get the default template
        template_name = opts.template
        if not templates_info.has_key(template_name):
            raise cocos.CCPluginError('Not found template: %s' % template_name)
        template = templates_info[template_name]
        project_dir = os.path.abspath(os.path.join(opts.directory, self.project_name))
        creator = TPCreator(self._sdkroot, self.project_name, project_dir, template_name, template, opts.package)
        # do the default creating step
        creator.do_default_step()
        if opts.has_native:
            creator.do_other_step('native_support')



    def _parse_cfg(self, language):
        self.script_dir= os.path.abspath(os.path.dirname(__file__))
        self.create_cfg_file = os.path.join(self.script_dir, "sdk.json")
        
        f = open(self.create_cfg_file)
        create_cfg = json.load(f)
        f.close()
        langcfg = create_cfg[language]
        langcfg['SDK_ROOT'] = os.path.abspath(os.path.join(self.script_dir,langcfg["SDK_ROOT"]))
        self._sdkroot = langcfg['SDK_ROOT']
        
        # replace SDK_ROOT to real path
        for k, v in langcfg.iteritems():
            if 'SDK_ROOT' in v:
                v = v.replace('SDK_ROOT', self._sdkroot)
                langcfg[k] = v
        
        #get the real json cfgs
        self.langcfg = langcfg
 

    def create_cpp_project(self, opts):
        pass


    # main entry point
    def run(self, argv, dependencies):
        opts = self.parse_args(argv);
        if opts.gui:
            self._create_from_ui(opts)
        else:
            self._create_from_cmd(opts)


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


# copy the whole things from one dir into a exists dir
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



class TPCreator(object):
    def __init__(self, sdk_root, project_name, project_dir, tp_name, tp, project_package=None):
        self.sdk_root = sdk_root
        self.project_dir = project_dir
        self.project_name = project_name
        self.package_name = project_package

        self.tp_name = tp_name
        self.tp_dir = tp.pop('dir').replace('SDK_ROOT', self.sdk_root)

        # read the default creating step
        if not tp.has_key('default'):
            raise cocos.CCPluginError("The '%s' template dosen't has 'default' creating step" %
                    self.tp_name)
        self.tp_default_step = tp.pop('default')
        self.tp_other_step = tp

    def cp_self(self, project_dir, exclude_files):
        print 'copy tp to %s , and ignore files = %s ' % (project_dir, exclude_files)
        shutil.copytree(self.tp_dir, self.project_dir, True,
                ignore = _ignorePath(self.tp_dir, exclude_files) )


    def do_default_step(self):
        default_cmds = self.tp_default_step
        if default_cmds.has_key("exclude_from_template"):
            exclude_files = default_cmds['exclude_from_template']
            self.cp_self(self.project_dir, exclude_files)
            default_cmds.pop('exclude_from_template')

        self.do_cmds(default_cmds)
    
    def do_other_step(self, step):
        if step in self.tp_other_step:
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



## cmd below
    def append_h5_engine(self, v):
        print 'append_h5_engine'
        src = os.path.join(self.sdk_root, v['from'])
        dst = os.path.join(self.project_dir, v['to'])
        # check cocos engine exist
        moudle_cfg = os.path.join(src, 'moduleConfig.json')
        if not os.path.exists(moudle_cfg):
            print ("moduleConfig.json doesn\'t exist." \
                "generate it, please")
            return False

        f = open(moudle_cfg)
        data = json.load(f, 'utf8')
        f.close()
        modules = data['module'] 
        file_list = []
        for k, v in modules.iteritems():
            module = modules[k]
            for f in module:
                if f[-2:] == 'js':
                    file_list.append(f)

        #begin copy engine
        print("> Copying cocos2d-html5 files...")
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
        print 'append_x_engine'
        src = os.path.join(self.sdk_root, v['from'])
        dst = os.path.join(self.project_dir, v['to'])

        # check cocos engine exist
        cocosx_files_json = os.path.join(src, 'cocosx_files.json')
        if not os.path.exists(cocosx_files_json):
            print ("cocosx_files.json doesn\'t exist." \
                "generate it, please")
            return False

        f = open(cocosx_files_json)
        fileList = json.load(f)
        f.close()

        #begin copy engine
        print("> Copying cocos2d-x files...")
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
        print 'append_from_template'
        src = os.path.join(self.tp_dir, v['from'])
        dst = os.path.join(self.project_dir, v['to'])
        exclude_files = v['exclude']
        shutil.copytree(src, dst, True,
                ignore = _ignorePath(src, exclude_files) )


    def append_dir(self, v):
        print 'append_dir'
        src = os.path.join(self.sdk_root, v['from'])
        dst = os.path.join(self.project_dir, v['to'])
        exclude_files = v['exclude']
        copytree(src, dst, True, ignore = _ignorePath(src, exclude_files))

    def append_file(self, v):
        print 'append_file'
        for item in v:
            src = os.path.join(self.sdk_root, item['from'])
            dst = os.path.join(self.project_dir, item['to'])
            shutil.copy2(src, dst)

## project cmd
    def project_rename(self, v):
        print 'project_rename'
        src_project_name = v['src_project_name']
        files = v['files']
        for f in files:
            src = f.replace("PROJECT_NAME", src_project_name)
            dst = f.replace("PROJECT_NAME", self.project_name)
            if os.path.exists(os.path.join(self.project_dir, src)):
                os.rename(os.path.join(self.project_dir, src), os.path.join(self.project_dir, dst))

    def project_replace_project_name(self, v):
        print 'project_replace_project_name'
        src_project_name = v['src_project_name']
        files = v['files']
        for f in files:
            dst = f.replace("PROJECT_NAME", self.project_name)
            if os.path.exists(os.path.join(self.project_dir, dst)):
                replace_string(os.path.join(self.project_dir, dst), src_project_name, self.project_name)

    def project_replace_package_name(self, v):
        print 'project_replace_package_name'
        src_package_name = v['src_package_name']
        files = v['files']
        if not self.package_name:
            raise cocos.CCPluginError('package name not specified')
        for f in files:
            dst = f.replace("PROJECT_NAME", self.project_name)
            if os.path.exists(os.path.join(self.project_dir, dst)):
                replace_string(os.path.join(self.project_dir, dst), src_package_name, self.package_name)


