
import os
import os.path
import json
import re
import shlex
import shutil

import cocos


class RemoveFrameworkHelper(object):

    def __init__(self, project, package_path):
        self._package_path = package_path
        self._uninstall_json_path = self._package_path + os.sep + "uninstall.json"
        self.get_uninstall_info()

    def run(self):
        for remove_info in self._uninstall_info:
            if "file" in remove_info:
                filename = remove_info["file"]
                remove_string = remove_info["string"]
                self.do_remove_string_from_file(filename, remove_string)
            elif "json_file" in remove_info:
                filename = remove_info["json_file"]
                remove_items = remove_info["items"]
                self.do_remove_string_from_jsonfile(filename, remove_items)
            elif "bak_file" in remove_info:
                ori = remove_info["ori_file"]
                bak = remove_info["bak_file"]
                if os.path.exists(bak):
                    self.do_remove_file(ori)
                    os.rename(bak, ori)

    def do_remove_file(self, file_path):
        if not os.path.exists(file_path):
            return

        if os.path.isdir(file_path):
            shutil.rmtree(file_path)
        else:
            os.remove(file_path)

    def do_remove_string_from_file(self, filename, remove_string):
        if not os.path.isfile(filename):
            return

        f = open(filename, "rb")
        all_text = f.read()
        f.close()

        find_index = all_text.find(remove_string.encode("ascii"))
        if find_index >= 0:
            headers = all_text[0:find_index]
            tails = all_text[find_index+len(remove_string):]
            all_text = headers + tails
            f = open(filename, "wb")
            f.write(all_text)
            f.close()

    def do_remove_string_from_jsonfile(self, filename, remove_items):
        if not os.path.isfile(filename):
            return

        f = open(filename, "rb")
        configs = json.load(f)
        f.close()

        for remove_item in remove_items:
            key = remove_item["key"]
            if not key in configs:
                continue

            # found the key need to remove or to remove items
            if "items" in remove_item:
                # remove items in configs[key]
                self.remove_items_from_json(configs[key], remove_item["items"])
            else:
                # remove configs[key]
                del(configs[key])

        f = open(filename, "w+b")
        str = json.dump(configs, f)
        f.close()

    def remove_items_from_json(self, configs, remove_items):
        if isinstance(configs, list):
            # delete string in list
            for item in remove_items:
                if item in configs:
                    configs.remove(item)

        else:
            # delete key in dict
            for item in remove_items:
                if "key" in item:
                    key = item["key"]
                    if not key in configs:
                        continue
                    # found the key need to remove or to remove items
                    if "items" in item:
                        # remove items in configs[key]
                        self.remove_items_from_json(configs[key], item["items"])
                    else:
                        # remove configs[key]
                        del(configs[key])

    def get_uninstall_info(self):
        file_path = self._uninstall_json_path
        if os.path.isfile(file_path):
            f = open(file_path, "rb")
            self._uninstall_info = json.load(f)
            f.close()
        else:
            self._uninstall_info = []
