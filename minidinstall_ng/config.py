#!/usr/bin/env python3
# SignedFile -*- mode: python; coding: utf-8 -*-
#-----------------------------------------------------------------------------
'''
Simple configuration handler class creating an easy way to access the
configuration.
'''
#-----------------------------------------------------------------------------
# Copyright (C) 2014  c0ff3m4kr <l34k@bk.ru>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#-----------------------------------------------------------------------------
import configparser
from configparser import ConfigParser
import logging
import collections

class SectionMapper(object):
    def __init__(self, parent, section):
        self._parent = parent
        self._section = section

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        if not name[0] == '_':
            self._parent.set(self._section, name, value)
        object.__setattr__(self, name, value)

    def __setitem__(self, name, value):
        self._parent.set(self._section, name, value)

    def __getitem__(self, name):
        return self._parent.get(self._section, name)

class ConfigHandler(object):
    '''
    :param defaults: A dictionary with the configuration names
                     (e.g 'rootfolder')  as names and a tuple containing the
                     type (callable object to convert a value into a given 
                     type) and the default value as values.
    :param config_parser: A :class`configparser.ConfigParser` object with
                          the config files already read.
    '''
    def __init__(self, defaults, additional_files=None, logger=None):
        self._logger = logger or logging.getLogger()
        # upack defaults dictionary
        defaults = defaults.items()
        config_names, check_tuples = zip(*defaults)
        types, defaults = zip(*check_tuples)
        self._types = dict(zip(config_names, types))
        self._mappers = {}
        self._configp = ConfigParser()
        self._defaults = dict(zip(config_names, defaults))

        config_files = []
        if self._configp.has_option(configparser.DEFAULTSECT, 'configfiles'):
            config_files += self.get_default('configfiles')
        if additional_files:
            config_files += additional_files
        read_files = self._configp.read(config_files)
        for not_read_file in set(config_files) - set(read_files):
            self._logger.warning('Config file could not be read: %r' % not_read_file)

        for section in [configparser.DEFAULTSECT] + self.distributions:
            self._mappers[section] = SectionMapper(self, section)

    def set(self, section, option, value):
        if not option in self._types:
            raise KeyError('No such option %r' % option)
        # check value
        self._types[option](value)
        # save it unchanged
        self._configp.set(section, option, value)

    def get(self, section, option):
        if not option in self._types:
            raise KeyError('No such option %r' % option)
        if self._configp.has_option(section, option):
            value = self._configp.get(section, option)
            value = self._types[option](value)
        else:
            value = self._defaults[option]
        return value

    def get_default(self, option):
        return self.get(configparser.DEFAULTSECT, option)

    def get_distributions(self):
        if len(self._configp.sections()) == 0:
            if self._configp.has_option(configparser.DEFAULTSECT, 'distributions'):
                for distribution in self.get_default('distributions'):
                    self.add_section(distribution)
        # call sections directly from now on
        self.get_distributions = self._configp.sections    
        return self.get_distributions()

    distributions = property(get_distributions)

    def __getattr__(self, name):
        # if name in self._types:
        #     return self._mappers[name]
        if name == 'all':
            return self._mappers[configparser.DEFAULTSECT]
        raise AttributeError('No such attribute %r' % name)

    def __getitem__(self, name):
        if name == 'all':
            name = configparser.DEFAULTSECT
        if not name in self._mappers:
            raise KeyError('No distribution %r' % name)
        return self._mappers[name]

    # def __setitem__(self, name, value):
    #     if name == 'all':
    #         name = configparser.DEFAULTSECT
    #     if not name in self._mappers:
    #         raise KeyError('No distribution %r' % name)
    #     self._mappers[name] = value        

if __name__ == '__main__':
    import unittest
    import minidinstall_ng.config_types as types
    class TestConfigHandler(unittest.TestCase):
        def setUp(self):
            self.defaults = {
                'name': (str, 'mini-dinstall'),
                'version':(int, 0),
                'required':(str, None),
                'list': (types.StrList(), None)
            }
            self.ch = ConfigHandler(self.defaults)

        def test_getitem(self):
            self.assertEqual(self.ch['all']['name'], 'mini-dinstall')
            self.assertEqual(self.ch.all['name'], 'mini-dinstall')
            self.assertEqual(self.ch['all'].name, 'mini-dinstall')
            self.assertEqual(self.ch.all.name, 'mini-dinstall')
            self.assertEqual(self.ch['all']['version'], 0)
            self.assertEqual(self.ch.all.version, 0)

        def test_unexisting(self):
            def get_by_key():
                return self.ch['all']['unexisting']
            def get_by_attr():
                return self.ch.all.unexisting
            self.assertRaises(KeyError, get_by_key)
            self.assertRaises(KeyError, get_by_attr)

        def test_read(self):
            ch = ConfigHandler(self.defaults, ['test/config_001.cfg'])
            self.assertEqual(ch['all']['version'], 3)
            self.assertEqual(ch['all']['version'], 3)
            self.assertEqual(ch['all']['list'], ['hi','I','will','hopefully be seperated','correctly'])
            def get_by_key():
                return ch.all['unexisting']
            self.assertRaises(KeyError, get_by_key)
    unittest.main()
