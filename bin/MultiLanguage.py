#!/usr/bin/python
# ----------------------------------------------------------------------------
# MultiLanguage: Get the multi-language strings for console.
#
# Author: Bin Zhang
#
# License: MIT
# ----------------------------------------------------------------------------
'''
Get the multi-language strings for console.
'''

import cocos
import os
import sys
import json
import locale

def get_current_path():
    if getattr(sys, 'frozen', None):
        ret = os.path.realpath(os.path.dirname(sys.executable))
    else:
        ret = os.path.realpath(os.path.dirname(__file__))

    return ret

class MultiLanguage(object):
    CONFIG_FILE_NAME = 'strings.json'
    DEFAULT_LANGUAGE = 'en'
    instance = None

    @classmethod
    def get_instance(cls):
        if cls.instance is None:
            cls.instance = MultiLanguage()

        return cls.instance

    @classmethod
    def get_string(cls, key):
        return cls.get_instance().get_current_string(key)

    @classmethod
    def set_language(cls, lang):
        cls.get_instance().set_current_language(lang)

    def __init__(self):
        cfg_file_path = os.path.join(get_current_path(), MultiLanguage.CONFIG_FILE_NAME)

        try:
            cur_lang, self.encoding = locale.getdefaultlocale()
        except:
            cur_lang = None
            self.encoding = None
            pass

        if self.encoding is None:
            self.encoding = 'utf-8'

        if cur_lang is None:
            cur_lang = MultiLanguage.DEFAULT_LANGUAGE
        else:
            cur_lang = cur_lang.split('_')[0]
            cur_lang = cur_lang.lower()

        # get the strings info
        if os.path.isfile(cfg_file_path):
            f = open(cfg_file_path)
            self.cfg_info = json.load(f, encoding='utf-8')
            f.close()

            if self.cfg_info.has_key(cur_lang):
                self.cur_lang_strings = self.cfg_info[cur_lang]
            else:
                self.cur_lang_strings = None

            if self.cfg_info.has_key(MultiLanguage.DEFAULT_LANGUAGE):
                self.default_lang_strings = self.cfg_info[MultiLanguage.DEFAULT_LANGUAGE]
            else:
                self.default_lang_strings = None
        else:
            self.cfg_info = None
            self.cur_lang_strings = None
            self.default_lang_strings = None

    def has_key(self, key, strings_info):
        ret = False
        if strings_info is not None and strings_info.has_key(key):
            ret = True

        return ret

    def set_current_language(self, lang):
        if (self.cfg_info is not None) and (self.cfg_info.has_key(lang)):
            self.cur_lang_strings = self.cfg_info[lang]
        else:
            cocos.Logging.warning(MultiLanguage.get_string('COCOS_WARNING_LANG_NOT_SUPPORT_FMT') % lang)

    def get_current_string(self, key):
        if self.has_key(key, self.cur_lang_strings):
            ret = self.cur_lang_strings[key]
        elif self.has_key(key, self.default_lang_strings):
            ret = self.default_lang_strings[key]
        else:
            ret= key

        if isinstance(ret, unicode):
            ret = ret.encode(self.encoding)

        return ret
