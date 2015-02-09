
import os
import os.path
import json
import re
import shlex

import cocos


class AddFrameworkHelper(object):
    IOS_MAC_PROJECT_FILE_REF_BEGIN_TAG = '/\* Begin PBXFileReference section \*/'
    IOS_MAC_PROJECT_FILE_REF_END_TAG = '/\* End PBXFileReference section \*/'
    IOS_MAC_PROJECT_FILE_REF_TAG = '(' + IOS_MAC_PROJECT_FILE_REF_BEGIN_TAG + ')(.*)(' + IOS_MAC_PROJECT_FILE_REF_END_TAG + ')'
    IOS_MAC_PROJECT_MAINGROUP_TAG = '(mainGroup\s=\s)(.+)(;)'
    IOS_MAC_PROJECT_REFERENCES_TAG = 'projectReferences = \('
    IOS_MAC_PBXGROUP_TAG = '(/\* Begin PBXGroup section \*/)(.*)(/\* End PBXGroup section \*/)'
    IOS_MAC_PBXCONTAINER_TAG = '(/\* Begin PBXContainerItemProxy section \*/)(.*)(/\* End PBXContainerItemProxy section \*/)'
    IOS_MAC_PBXPROXY_TAG = '(/\* Begin PBXReferenceProxy section \*/)(.*)(/\* End PBXReferenceProxy section \*/)'
    IOS_MAC_PBXBUILD_TAG = '(/\* Begin PBXBuildFile section \*/)(.*)(/\* End PBXBuildFile section \*/)'
    MAC_PBXFRAMEWORKBUILDPHASE_TAG = '\S+ /\* libcocos2d Mac.a in Frameworks \*/,'
    IOS_PBXFRAMEWORKBUILDPHASE_TAG = '\S+ /\* libcocos2d iOS.a in Frameworks \*/,'

    IOS_HEADER_MATCH_TAG = '(\$\(_COCOS_HEADER_IOS_BEGIN\))(.+)(\$\(_COCOS_HEADER_IOS_END\))'
    IOS_LIB_BEGIN_TAG = '\$\(_COCOS_LIB_IOS_BEGIN\)'
    IOS_LIB_END_TAG = '\$\(_COCOS_LIB_IOS_END\)'

    MAC_HEADER_MATCH_TAG = '(\$\(_COCOS_HEADER_MAC_BEGIN\))(.+)(\$\(_COCOS_HEADER_MAC_END\))'
    MAC_LIB_BEGIN_TAG = '\$\(_COCOS_LIB_MAC_BEGIN\)'
    MAC_LIB_END_TAG = '\$\(_COCOS_LIB_MAC_END\)'

    WIN32_HEADER_MATCH_TAG = '(\$\(_COCOS_HEADER_WIN32_BEGIN\))(.+)(\$\(_COCOS_HEADER_WIN32_END\))'
    WIN32_LIB_PATH_MATCH_TAG = '(\$\(_COCOS_LIB_PATH_WIN32_BEGIN\))(.+)(\$\(_COCOS_LIB_PATH_WIN32_END\))'
    WIN32_LIB_MATCH_TAG = '(\$\(_COCOS_LIB_WIN32_BEGIN\))(.+)(\$\(_COCOS_LIB_WIN32_END\))'

    ANDROID_HEADER_BEGIN_TAG = '# _COCOS_HEADER_ANDROID_BEGIN'
    ANDROID_HEADER_END_TAG = '# _COCOS_HEADER_ANDROID_END'
    ANDROID_HEADER_PREFIX = 'LOCAL_C_INCLUDES'
    ANDROID_LIB_BEGIN_TAG = '# _COCOS_LIB_ANDROID_BEGIN'
    ANDROID_LIB_END_TAG = '# _COCOS_LIB_ANDROID_END'
    ANDROID_LIB_PREFIX = 'LOCAL_STATIC_LIBRARIES'
    ANDROID_LIB_IMPORT_BEGIN_TAG = '# _COCOS_LIB_IMPORT_ANDROID_BEGIN'
    ANDROID_LIB_IMPORT_END_TAG = '# _COCOS_LIB_IMPORT_ANDROID_END'


    def __init__(self, project, package_data):
        self._package_name = package_data["name"]
        self._package_version = package_data["version"]
        self._package_path = project["packages_dir"] + os.sep + package_data["name"] + '-' + package_data["version"]
        self._install_json_path = self._package_path + os.sep + "install.json"
        f = open(self._install_json_path, "rb")
        self._commands = json.load(f)
        self._project = project
        f.close()

    def run(self):
        for command in self._commands:
            try:
                name = "do_" + command["command"]
                cmd = getattr(self, name)
            except AttributeError:
                raise cocos.CCPluginError("cmd = %s is not found" % name)

            try:
                cmd(command)
            except Exception as e:
                raise cocos.CCPluginError(str(e))

    def do_add_entry_function(self, command):
        self.add_entry_function(command)

    def do_add_system_framework(self, command):
        self.add_system_framework(command)

    def do_add_project(self, command):
        platforms = command["platform"]
        for platform in platforms:
            name = "do_add_project_on_" + platform
            cmd = getattr(self, name)
            cmd(command)

    def do_add_lib(self, command):
        platforms = command["platform"]
        for platform in platforms:
            name = "do_add_lib_on_" + platform
            cmd = getattr(self, name)
            cmd(command)

    def do_add_header_path(self, command):
        platforms = command["platform"]
        for platform in platforms:
            name = "do_add_header_path_on_" + platform
            cmd = getattr(self, name)
            cmd(command)

    def do_add_header_path_on_ios(self, command):
        self.add_header_path_on_ios_mac(command["source"].encode('UTF-8'), "ios")

    def do_add_header_path_on_mac(self, command):
        self.add_header_path_on_ios_mac(command["source"].encode('UTF-8'), "mac")

    def do_add_header_path_on_win(self, command):
        source = command["source"].encode('UTF-8')
        tag = self.__class__.WIN32_HEADER_MATCH_TAG
        self.do_add_header_lib_on_win(source, tag)

    def do_add_header_path_on_android(self, command):
        source = command["source"].encode('UTF-8')
        begin_tag = self.__class__.ANDROID_HEADER_BEGIN_TAG
        end_tag = self.__class__.ANDROID_HEADER_END_TAG
        prefix_tag = self.__class__.ANDROID_HEADER_PREFIX
        self.do_add_header_lib_on_android(source, begin_tag, end_tag, prefix_tag)

    def add_header_path_on_ios_mac(self, source, platform):
        if platform == "ios":
            tag = self.__class__.IOS_HEADER_MATCH_TAG
        elif platform == "mac":
            tag = self.__class__.MAC_HEADER_MATCH_TAG
        else:
            raise cocos.CCPluginError("Invalid platform '%s'" % platform)

        workdir, proj_file_path, lines = self.load_proj_ios_mac(False)
        contents = []
        tag_found = False
        for line in lines:
            match = re.search(tag, line)
            if match is None:
                contents.append(line)
            else:
                includes = shlex.split(match.group(2))
                headers = []
                for include in includes:
                    include = self.get_ios_mac_path(workdir, include)
                    headers.append(include)

                headers.append(self.get_ios_mac_path(workdir, source))
                headers = list(set(headers))
                start, end = match.span(0)
                parts = []
                parts.append(line[:start])
                parts.append(match.group(1))
                parts.append(' ')
                for header in headers:
                    if header.find(' ') != -1:
                        header = '"' + header + '"'
                    parts.append(header)
                    parts.append(' ')
                parts.append(match.group(3))
                parts.append(line[end:])
                contents.append(''.join(parts))
                tag_found = True

        if tag_found == False:
            raise cocos.CCPluginError("Not found header TAG in project for platform '%s'" % platform)
        else:
            f = open(proj_file_path, "wb")
            f.writelines(contents)
            f.close()

    def add_entry_function(self, command):
        declare_str = command["declare"]
        find_tag = '(\S*\s*)(\S*)(\(.*\);)'
        match = re.search(find_tag, declare_str)
        if match is None:
            raise cocos.CCPluginError("Error for declare of entry function")
        else:
            str_to_add = 'extern ' + declare_str + '\n\t' + match.group(2) + '(L);'

        file_path, all_text = self.load_lua_module_register_file()
        find_tag = '(lua_module_register\(.*\)\s*\{.*)(return 1;\s*\})'
        match = re.search(find_tag, all_text, re.DOTALL)
        if match is None:
            raise cocos.CCPluginError("Error in file: %s" %file_path)
        else:
            # add entry funtion
            split_index = match.end(1)
            headers = all_text[0:split_index]
            tails = all_text[split_index:]
            all_text = headers + str_to_add + '\n\t' + tails

        f = open(file_path, "wb")
        f.write(all_text)
        f.close()

    def add_system_framework(self, command):
        framework_name = command["name"].encode('UTF-8')
        file_id = command["file_id"].encode('UTF-8')
        file_path = command["path"].encode('UTF-8')
        sourceTree = command["sourceTree"].encode('UTF-8')
        framework_id = command["id"].encode('UTF-8')
        platform = command["platform"].encode('UTF-8')

        workdir, proj_pbx_path, all_text = self.load_proj_ios_mac(True)
        find_tag = self.__class__.IOS_MAC_PROJECT_FILE_REF_TAG
        match = re.search(find_tag, all_text, re.DOTALL)
        if match is None:
            raise cocos.CCPluginError("Not found PBXFileReference TAG in project for platform '%s'" % platform)
        else:
            # add PBXFileReference of framework
            split_index = match.end(1)
            headers = all_text[0:split_index]
            tails = all_text[split_index:]
            all_text = headers + '\n\t\t' + file_id
            all_text = all_text + ' /* ' + framework_name + ' */ = {'
            all_text = all_text + 'isa = PBXFileReference; '
            all_text = all_text + 'lastKnownFileType = wrapper.framework; '
            all_text = all_text + 'name = ' + framework_name + '; '
            all_text = all_text + 'path = ' + file_path + '; '
            all_text = all_text + 'sourceTree = ' + sourceTree + '; '
            all_text = all_text + '};' + tails

        find_tag = self.__class__.IOS_MAC_PBXBUILD_TAG
        match = re.search(find_tag, all_text, re.DOTALL)
        if match is None:
            raise cocos.CCPluginError("Not found PBXBuildFile in project for platform '%s'" % platform)
        else:
            # add framework to PBXBuildFile
            split_index = match.start(3)
            headers = all_text[0:split_index]
            tails = all_text[split_index:]
            skip_str = '\t\t'
            all_text = headers + skip_str + framework_id + ' /* ' + framework_name + ' in Frameworks */ = {'
            all_text = all_text + 'isa = PBXBuildFile; '
            all_text = all_text + 'fileRef = ' + file_id + ' /* ' + framework_name + ' */; };\n'
            all_text = all_text + tails

        if platform == 'mac':
            find_tag = self.__class__.MAC_PBXFRAMEWORKBUILDPHASE_TAG
        else:
            find_tag = self.__class__.IOS_PBXFRAMEWORKBUILDPHASE_TAG
        match = re.search(find_tag, all_text)
        if match is None:
            raise cocos.CCPluginError("Not found PBXFrameworksBuildPhase in project for platform '%s'" % platform)
        else:
            # add framework to PBXFrameworksBuildPhase
            split_index = match.start()
            headers = all_text[0:split_index]
            tails = all_text[split_index:]
            all_text = headers + framework_id + ' /* ' + framework_name + ' in Frameworks */,\n\t\t\t\t' + tails

        f = open(proj_pbx_path, "wb")
        f.write(all_text)
        f.close()

    def do_add_project_on_android(self, command):
        proj_name = command["name"].encode('UTF-8')

        build_cfg_file = self.get_build_cfg_json_path()
        if build_cfg_file is None:
            raise cocos.CCPluginError("Not found build config file for platform 'android'")
        f = open(build_cfg_file, "rb")
        configs = json.load(f)
        f.close()
        if not isinstance(configs["ndk_module_path"], list):
            raise cocos.CCPluginError("Not found 'ndk_module_path' in build config file for platform 'android'")
        moudle_path = '../../../packages/' + self._package_name + '-' + self._package_version
        configs["ndk_module_path"].append(moudle_path)
        f = open(build_cfg_file, "w+b")
        str = json.dump(configs, f)
        f.close()

        workdir, proj_pbx_path, all_text = self.load_proj_android(True)

        find_tag = '(' + self.__class__.ANDROID_LIB_BEGIN_TAG+ ')(.*)(' + self.__class__.ANDROID_LIB_END_TAG + ')'
        match = re.search(find_tag, all_text, re.DOTALL)
        if match is None:
            raise cocos.CCPluginError("Not found lib TAG in project for platform 'android'")
        else:
            # add project
            split_index = match.end(2)
            headers = all_text[0:split_index]
            tails = all_text[split_index:]
            all_text = headers + 'LOCAL_STATIC_LIBRARIES += ' + proj_name + '_static\n'
            all_text = all_text + tails

        find_tag = '(' + self.__class__.ANDROID_LIB_IMPORT_BEGIN_TAG+ ')(.*)(' + self.__class__.ANDROID_LIB_IMPORT_END_TAG + ')'
        match = re.search(find_tag, all_text, re.DOTALL)
        if match is None:
            raise cocos.CCPluginError("Not found lib TAG in project for platform 'android'")
        else:
            # add import moudle
            split_index = match.end(2)
            headers = all_text[0:split_index]
            tails = all_text[split_index:]
            all_text = headers + '$(call import-module,proj.android)\n'
            all_text = all_text + tails

        f = open(proj_pbx_path, "wb")
        f.write(all_text)
        f.close()

    def do_add_project_on_ios_mac(self, command):
        self.add_project_on_ios_mac(command)

    def add_project_on_ios_mac(self, command):
        proj_name = command["name"].encode('UTF-8')
        pbx_id = command["id"].encode('UTF-8')

        mac_lib = command["mac_lib"]
        mac_lib_remote = mac_lib["remoteGlobalIDString"].encode('UTF-8')
        mac_lib_info = mac_lib["remoteInfo"]
        mac_lib_name = 'lib' + mac_lib_info + '.a'
        mac_lib_container = mac_lib["container"].encode('UTF-8')
        mac_lib_id = mac_lib["lib_id"].encode('UTF-8')
        mac_lib_build = mac_lib["build_id"].encode('UTF-8')

        ios_lib = command["ios_lib"]
        ios_lib_remote = ios_lib["remoteGlobalIDString"].encode('UTF-8')
        ios_lib_info = ios_lib["remoteInfo"]
        ios_lib_name = 'lib' + ios_lib_info + '.a'
        ios_lib_container = ios_lib["container"].encode('UTF-8')
        ios_lib_id = ios_lib["lib_id"].encode('UTF-8')
        ios_lib_build = ios_lib["build_id"].encode('UTF-8')

        productGroup_id = command["ProductGroup"].encode('UTF-8')

        platform = 'ios_mac'
        workdir, proj_pbx_path, lines = self.load_proj_ios_mac(False)

        begin_tag = self.__class__.IOS_MAC_PROJECT_FILE_REF_BEGIN_TAG
        end_tag = self.__class__.IOS_MAC_PROJECT_FILE_REF_END_TAG
        contents = []
        contents_str = ''
        file_ref_begin = False
        tag_found = False
        for line in lines:
            if file_ref_begin == False:
                contents.append(line)
                contents_str = contents_str + line
                match = re.search(begin_tag, line)
                if not match is None:
                    file_ref_begin = True
                    tag_found = True
            else:
                match = re.search(end_tag, line)
                if match is None:
                    contents.append(line)
                    contents_str = contents_str + line
                else:
                    # add PBXFileReference of project
                    file_ref_string = '\t\t' + pbx_id + ' /* ' + proj_name + '.xcodeproj */ = '
                    file_ref_string += '{isa = PBXFileReference; lastKnownFileType = "wrapper.pb-project"; name = '
                    file_ref_string += proj_name + '.xcodeproj; path = "../../../packages/'
                    file_ref_string += self._package_name + '-' + self._package_version + '/proj.ios_mac/'
                    file_ref_string += proj_name + '.xcodeproj"; sourceTree = "<group>"; };\n'
                    contents.append(file_ref_string)
                    contents_str = contents_str + file_ref_string
                    contents.append(line)
                    contents_str = contents_str + line

        if tag_found == False:
            raise cocos.CCPluginError("Not found PBXFileReference TAG in project for platform '%s'" % platform)

        # get id of mainGroup
        main_tag = self.__class__.IOS_MAC_PROJECT_MAINGROUP_TAG
        match = re.search(main_tag, contents_str)
        if match is None:
            raise cocos.CCPluginError("Not found main group in project for platform '%s'" % platform)
        else:
            main_group_id = match.group(2)

        find_tag = '(' + main_group_id + '\s=\s\{\s*isa\s=\sPBXGroup;\s*children\s=\s\()(\s*)(\S*\s/\*\s\S*\s\*/,\s*)+(\);.*\};)'
        match = re.search(find_tag, contents_str, re.DOTALL)
        if match is None:
            raise cocos.CCPluginError("Not found children of main group in project for platform '%s'" % platform)
        else:
            # add project to mainGroup
            split_index = match.end(1)
            headers = contents_str[0:split_index]
            tails = contents_str[split_index:]
            skip_str = match.group(2)
            contents_str = headers + skip_str + pbx_id + ' /* ' + proj_name + '.xcodeproj */,' + tails

        find_tag = self.__class__.IOS_MAC_PBXCONTAINER_TAG
        match = re.search(find_tag, contents_str, re.DOTALL)
        if match is None:
            raise cocos.CCPluginError("Not found PBXContainerItemProxy in project for platform '%s'" % platform)
        else:
            # add PBXContainerItemProxy
            split_index = match.start(3)
            headers = contents_str[0:split_index]
            tails = contents_str[split_index:]
            skip_str = '\t\t'
            contents_str = headers + skip_str + mac_lib_container + ' /* PBXContainerItemProxy */ = {\n'
            contents_str = contents_str + skip_str + '\tisa = PBXContainerItemProxy;\n'
            contents_str = contents_str + skip_str + '\tcontainerPortal = ' + pbx_id + ' /* ' + proj_name + '.xcodeproj */;\n'
            contents_str = contents_str + skip_str + '\tproxyType = 2;\n'
            contents_str = contents_str + skip_str + '\tremoteGlobalIDString = ' + mac_lib_remote + ';\n'
            contents_str = contents_str + skip_str + '\tremoteInfo = "' + mac_lib_info + '";\n'
            contents_str = contents_str + skip_str + '};\n'
            contents_str = contents_str + skip_str + ios_lib_container + ' /* PBXContainerItemProxy */ = {\n'
            contents_str = contents_str + skip_str + '\tisa = PBXContainerItemProxy;\n'
            contents_str = contents_str + skip_str + '\tcontainerPortal = ' + pbx_id + ' /* ' + proj_name + '.xcodeproj */;\n'
            contents_str = contents_str + skip_str + '\tproxyType = 2;\n'
            contents_str = contents_str + skip_str + '\tremoteGlobalIDString = ' + ios_lib_remote + ';\n'
            contents_str = contents_str + skip_str + '\tremoteInfo = "' + ios_lib_info + '";\n'
            contents_str = contents_str + skip_str + '};\n' + tails

        find_tag = self.__class__.IOS_MAC_PBXPROXY_TAG
        match = re.search(find_tag, contents_str, re.DOTALL)
        if match is None:
            raise cocos.CCPluginError("Not found PBXReferenceProxy in project for platform '%s'" % platform)
        else:
            # add PBXReferenceProxy
            split_index = match.start(3)
            headers = contents_str[0:split_index]
            tails = contents_str[split_index:]
            skip_str = '\t\t'
            contents_str = headers + skip_str + mac_lib_id + ' /* ' + mac_lib_name + ' */ = {\n'
            contents_str = contents_str + skip_str + '\tisa = PBXReferenceProxy;\n'
            contents_str = contents_str + skip_str + '\tfileType = archive.ar;\n'
            contents_str = contents_str + skip_str + '\tpath = "' + mac_lib_name + '";\n'
            contents_str = contents_str + skip_str + '\tremoteRef = ' + mac_lib_container + ' /* PBXContainerItemProxy */;\n'
            contents_str = contents_str + skip_str + '\tsourceTree = BUILT_PRODUCTS_DIR;\n'
            contents_str = contents_str + skip_str + '};\n'
            contents_str = contents_str + skip_str + ios_lib_id + ' /* ' + ios_lib_name + ' */ = {\n'
            contents_str = contents_str + skip_str + '\tisa = PBXReferenceProxy;\n'
            contents_str = contents_str + skip_str + '\tfileType = archive.ar;\n'
            contents_str = contents_str + skip_str + '\tpath = "' + ios_lib_name + '";\n'
            contents_str = contents_str + skip_str + '\tremoteRef = ' + ios_lib_container + ' /* PBXContainerItemProxy */;\n'
            contents_str = contents_str + skip_str + '\tsourceTree = BUILT_PRODUCTS_DIR;\n'
            contents_str = contents_str + skip_str + '};\n' + tails

        find_tag = self.__class__.IOS_MAC_PBXGROUP_TAG
        match = re.search(find_tag, contents_str, re.DOTALL)
        if match is None:
            raise cocos.CCPluginError("Not found PBXGroup in project for platform '%s'" % platform)
        else:
            # add ProductGroup of project to PBXGroup
            split_index = match.end(1)
            headers = contents_str[0:split_index]
            tails = contents_str[split_index:]
            skip_str = '\n\t\t'
            contents_str = headers + skip_str + productGroup_id + ' /* Products */ = {'
            contents_str = contents_str + skip_str + '\tisa = PBXGroup;'
            contents_str = contents_str + skip_str + '\tchildren = ('
            contents_str = contents_str + skip_str + '\t\t' + mac_lib_id + ' /* ' + mac_lib_name + ' */,'
            contents_str = contents_str + skip_str + '\t\t' + ios_lib_id + ' /* ' + ios_lib_name + ' */,'
            contents_str = contents_str + skip_str + '\t);'
            contents_str = contents_str + skip_str + '\tname = Products;'
            contents_str = contents_str + skip_str + '\tsourceTree = "<group>";'
            contents_str = contents_str + skip_str + '};' + tails

        find_tag = self.__class__.IOS_MAC_PROJECT_REFERENCES_TAG
        match = re.search(find_tag, contents_str)
        if match is None:
            raise cocos.CCPluginError("Not found projectReferences in project for platform '%s'" % platform)
        else:
            # add ProductGroup & project to projectReferences
            split_index = match.end()
            headers = contents_str[0:split_index]
            tails = contents_str[split_index:]
            skip_str = '\n\t\t\t\t'
            contents_str = headers + skip_str + '{'
            contents_str = contents_str + skip_str + '\tProductGroup = ' + productGroup_id + ' /* Products */;'
            contents_str = contents_str + skip_str + '\tProjectRef = ' + pbx_id + ' /* ' + proj_name + '.xcodeproj */;'
            contents_str = contents_str + skip_str + '},' + tails

        find_tag = self.__class__.IOS_MAC_PBXBUILD_TAG
        match = re.search(find_tag, contents_str, re.DOTALL)
        if match is None:
            raise cocos.CCPluginError("Not found PBXBuildFile in project for platform '%s'" % platform)
        else:
            # add lib to PBXBuildFile
            split_index = match.start(3)
            headers = contents_str[0:split_index]
            tails = contents_str[split_index:]
            skip_str = '\t\t'
            contents_str = headers + skip_str + mac_lib_build + ' /* ' + mac_lib_name + ' in Frameworks */ = {'
            contents_str = contents_str + 'isa = PBXBuildFile; '
            contents_str = contents_str + 'fileRef = ' + mac_lib_id + ' /* ' + mac_lib_name + ' */; };\n'
            contents_str = contents_str + skip_str + ios_lib_build + ' /* ' + ios_lib_name + ' in Frameworks */ = {'
            contents_str = contents_str + 'isa = PBXBuildFile; '
            contents_str = contents_str + 'fileRef = ' + ios_lib_id + ' /* ' + ios_lib_name + ' */; };\n'
            contents_str = contents_str + tails

        # get productName
        # find_tag = '(productName\s*=\s*)(.+)(;)'
        # match = re.search(find_tag, contents_str)
        # if match is None:
        #     raise cocos.CCPluginError("Not found productName in project for platform '%s'" % platform)
        # else:
        #     product_name = match.group(2)
        #     target_mac = product_name + ' Mac'
        #     target_ios = product_name + ' iOS'

        find_tag = self.__class__.MAC_PBXFRAMEWORKBUILDPHASE_TAG
        match = re.search(find_tag, contents_str)
        if match is None:
            raise cocos.CCPluginError("Not found Mac Frameworks in project for platform '%s'" % platform)
        else:
            # add mac lib to PBXFrameworksBuildPhase
            split_index = match.start()
            headers = contents_str[0:split_index]
            tails = contents_str[split_index:]
            contents_str = headers + mac_lib_build + ' /* ' + mac_lib_name + ' in Frameworks */,\n\t\t\t\t' + tails

        find_tag = self.__class__.IOS_PBXFRAMEWORKBUILDPHASE_TAG
        match = re.search(find_tag, contents_str)
        if match is None:
            raise cocos.CCPluginError("Not found iOS Frameworks in project for platform '%s'" % platform)
        else:
            # add ios lib to PBXFrameworksBuildPhase
            split_index = match.start()
            headers = contents_str[0:split_index]
            tails = contents_str[split_index:]
            contents_str = headers + ios_lib_build + ' /* ' + ios_lib_name + ' in Frameworks */,\n\t\t\t\t' + tails

        f = open(proj_pbx_path, "wb")
        f.write(contents_str)
        f.close()

    def do_add_lib_on_ios(self, command):
        self.add_lib_on_ios_mac(command["source"].encode('UTF-8'), "ios")

    def do_add_lib_on_mac(self, command):
        self.add_lib_on_ios_mac(command["source"].encode('UTF-8'), "mac")

    def do_add_lib_on_win(self, command):
        source = command["source"].encode('UTF-8')
        self.do_add_header_lib_on_win(os.path.basename(source), self.__class__.WIN32_LIB_MATCH_TAG)
        self.do_add_header_lib_on_win(os.path.dirname(source), self.__class__.WIN32_LIB_PATH_MATCH_TAG)

    def do_add_header_lib_on_win(self, source, tag):
        workdir, proj_file_path, lines = self.load_proj_win32()
        contents = []
        tag_found = False
        for line in lines:
            match = re.search(tag, line)
            if match is None:
                contents.append(line)
            else:
                includes = re.split(';', match.group(2))
                headers = []
                for include in includes:
                    include = self.get_win32_path(workdir, include)
                    if include is not None:
                        headers.append(include)

                headers.append(self.get_win32_path(workdir, source))
                headers = list(set(headers))
                start, end = match.span(0)
                parts = []
                parts.append(line[:start])
                parts.append(match.group(1))
                parts.append(';')
                for header in headers:
                    if header.find(' ') != -1:
                        header = '"' + header + '"'
                    parts.append(header)
                    parts.append(';')
                parts.append(match.group(3))
                parts.append(line[end:])
                contents.append(''.join(parts))
                tag_found = True

        if tag_found == False:
            raise cocos.CCPluginError("Not found header TAG in project for platform 'win32'")
        else:
            f = open(proj_file_path, "wb")
            f.writelines(contents)
            f.close()

    def do_add_lib_on_android(self, command):
        source = command["source"].encode('UTF-8')
        begin_tag = self.__class__.ANDROID_LIB_BEGIN_TAG
        end_tag = self.__class__.ANDROID_LIB_END_TAG
        prefix_tag = self.__class__.ANDROID_LIB_PREFIX
        self.do_add_header_lib_on_android(source, begin_tag, end_tag, prefix_tag)

        source = command["import-module"].encode('UTF-8')
        begin_tag = self.__class__.ANDROID_LIB_IMPORT_BEGIN_TAG
        end_tag = self.__class__.ANDROID_LIB_IMPORT_END_TAG
        self.do_add_header_lib_on_android(source, begin_tag, end_tag, None, True)

    def do_add_header_lib_on_android(self, source, begin_tag, end_tag, prefix_tag, is_import = False):
        workdir, proj_pbx_path, lines = self.load_proj_android()
        contents = []
        lib_begin = False
        tag_found = False
        libs = []
        for line in lines:
            if lib_begin == False:
                contents.append(line)
                match = re.search(begin_tag, line)
                if not match is None:
                    lib_begin = True
                    tag_found = True
            else:
                if prefix_tag is not None:
                    match = re.search(prefix_tag, line)
                    if match is not None:
                        continue

                match = re.search(end_tag, line)
                if match is None:
                    libs.append(self.get_android_path(workdir, line, is_import))
                else:
                    # add new lib to libs
                    libs.append(self.get_android_path(workdir, source, is_import))
                    libs = list(set(libs))
                    count = len(libs)
                    cur = 1
                    if count > 0 and prefix_tag is not None:
                        contents.append(prefix_tag)
                        contents.append(" += \\\n")
                    for lib in libs:
                        if cur < count and prefix_tag is not None:
                            contents.append('    ' + lib + ' \\')
                        elif is_import is False:
                            contents.append('    ' + lib)
                        else:
                            contents.append('$(call import-module,')
                            contents.append(lib)
                            contents.append(')')
                        contents.append("\n")

                    libs = []
                    lib_begin = False
                    contents.append(line)

        if tag_found == False:
            raise cocos.CCPluginError("Not found lib TAG in project for platform 'android'")
        else:
            f = open(proj_pbx_path, "wb")
            f.writelines(contents)
            f.close()

    def add_lib_on_ios_mac(self, source, platform):
        if platform == "ios":
            begin_tag = self.__class__.IOS_LIB_BEGIN_TAG
            end_tag = self.__class__.IOS_LIB_END_TAG
        elif platform == "mac":
            begin_tag = self.__class__.MAC_LIB_BEGIN_TAG
            end_tag = self.__class__.MAC_LIB_END_TAG
        else:
            raise cocos.CCPluginError("Invalid platform '%s'" % platform)

        workdir, proj_pbx_path, lines = self.load_proj_ios_mac(False)
        contents = []
        lib_begin = False
        tag_found = False
        libs = []
        for line in lines:
            if lib_begin == False:
                contents.append(line)
                match = re.search(begin_tag, line)
                if not match is None:
                    lib_begin = True
                    tag_found = True
            else:
                match = re.search(end_tag, line)
                if match is None:
                    libs.append(self.get_ios_mac_path(workdir, line))
                else:
                    # add new lib to libs
                    libs.append(self.get_ios_mac_path(workdir, source))
                    libs = list(set(libs))
                    for lib in libs:
                        contents.append('\t\t\t\t\t"' + lib + '",\n')

                    libs = []
                    lib_begin = False
                    contents.append(line)

        if tag_found == False:
            raise cocos.CCPluginError("Not found lib TAG in project for platform '%s'" % platform)
        else:
            f = open(proj_pbx_path, "wb")
            f.writelines(contents)
            f.close()

    def get_ios_mac_path(self, project_path, source):
        source = source.strip(',"\t\n\r')
        if not source[:10] == '$(SRCROOT)':
            source = '$(SRCROOT)' + os.sep + os.path.relpath(self._project["packages_dir"] + os.sep + source,
                                                             project_path)

        return source.replace(os.sep, '/')

    def get_win32_path(self, project_path, source):
        if source == ";" or source == "":
            return None

        if source.find('\\') == -1 and source.find('/') == -1:
            return source

        source = source.strip(',"\t\n\r')
        if not source[:13] == '$(ProjectDir)':
            source = '$(ProjectDir)' + os.sep + os.path.relpath(self._project["packages_dir"] + os.sep + source,
                                                             project_path)

        return source.replace('/', '\\')

    def get_android_path(self, project_path, source, ignore_local_path):
        source = source.strip(' ,"\t\n\r')

        if source.find('\\') == -1 and source.find('/') == -1:
            return source

        if source[-2:] == ' \\':
            source = source[0:-2]
        if source[:21] == '$(call import-module,':
            # strip "$(call import-module, ../../../../packages/"
            source = source[21:-1].strip('./\\')
            if source[:8] == "packages":
                source = source[9:]
        if not source[:13] == '$(LOCAL_PATH)':
            source = os.path.relpath(self._project["packages_dir"] + os.sep + source, project_path)
            if ignore_local_path is False:
                source = '$(LOCAL_PATH)' + os.sep + source

        return source

    def load_proj_ios_mac(self, notSplitLines):
        if not "proj.ios_mac" in self._project:
            print "This project not include proj.ios_mac"
            return

        workdir = self._project["proj.ios_mac"]
        files = os.listdir(workdir)
        for filename in files:
            if filename[-10:] == ".xcodeproj":
                proj_dir = filename
                break

        if proj_dir is None:
            print "Not found *.xcodeproj in proj.ios_mac"
            return

        if not os.path.isdir(workdir + os.sep + proj_dir):
            raise cocos.CCPluginError("'%s' is not xcode project" % proj_dir)

        proj_file_path = workdir + os.sep + proj_dir + os.sep + "project.pbxproj"
        f = open(proj_file_path, "rb")
        if notSplitLines == True:
            lines = f.read()
        else:
            lines = f.readlines()
        f.close()

        return workdir, proj_file_path, lines

    def load_proj_win32(self):
        if not "proj.win32" in self._project:
            print "This project not include proj.win32"
            return

        workdir = self._project["proj.win32"]
        files = os.listdir(workdir)
        for filename in files:
            if filename[-8:] == ".vcxproj":
                proj_file_path = workdir + os.sep +  filename
                break

        if proj_file_path is None:
            print "Not found *.vcxproj in proj.win32"
            return

        f = open(proj_file_path, "rb")
        lines = f.readlines()
        f.close()

        return workdir, proj_file_path, lines

    def load_proj_android(self, notSplitLines = False):
        if not "proj.android" in self._project:
            print "This project not include proj.android"
            return

        workdir = self._project["proj.android"] + os.sep + "jni"
        proj_file_path = workdir + os.sep + "Android.mk"
        if not os.path.isfile(proj_file_path):
            print "Not found Android.mk in proj.android/jni"
            return

        f = open(proj_file_path, "rb")
        if notSplitLines == True:
            lines = f.read()
        else:
            lines = f.readlines()
        f.close()

        return workdir, proj_file_path, lines

    def load_lua_module_register_file(self):
        file_path = self._project["classes_dir"] + os.sep + "lua_module_register.h"
        if not os.path.isfile(file_path):
            print "Not found lua_module_register.h in Classes/"
            return

        f = open(file_path, "rb")
        all_text = f.read()
        f.close()

        return file_path, all_text

    def get_build_cfg_json_path(self):
        file_path = self._project["proj.android"] + os.sep + "build-cfg.json"
        if not os.path.isfile(file_path):
            print "Not found build_cfg.json in proj.android/"
            return

        return file_path
