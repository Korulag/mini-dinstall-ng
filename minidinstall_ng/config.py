#!/usr/bin/env python3
# SignedFile -*- mode: python; coding: utf-8 -*-
#-----------------------------------------------------------------------------
'''
Description goes here
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


class ConfigHandler(dict):
    
    def __init__(self, defaults):
        # upack defaults dictionary
        defaults = defaults.items()
        config_names, check_tuples = zip(*defaults)
        types, defaults = zip(*check_tuples)
        # repact 
        self._types = dict(zip(config_names, types))
        dict.__init__(self, zip(config_names, defaults)) 

    def __getattr__(self, name):
        if name[0] != '_' and name in self:
            result = self[name]
        raise AttributeError(name)

    def __setattr__(self, item, value):
        if item[0] == '_':
            return dict.__setattr__(self, item, value)
        self[item] = value

    def __setitem__(self, item, value):
        if not item in self:
            raise IndexError('No such config option %r' % item)
        dict.__setitem__(self, item, self._types[item](value))

if __name__ == '__main__':
    import unittest
    class TestConfigHandler(unittest.TestCase):
        def setUp(self):
            self.defaults = {
                'name': (str, 'mini-dinstall'),
                'version':(int, 0),
                'required':(str, None)
            }
            self.ch = ConfigHandler(self.defaults)

        def test_getitem(self):
            self.assertEqual(self.ch['name'], 'mini-dinstall')
            self.assertEqual(self.ch.name, 'mini-dinstall')
            self.assertEqual(self.ch['version'], 0)
            self.assertEqual(self.ch.version, 0)

        def test_setitem(self):
            self.ch['name'] = 'mini-dinstall-ng'
            self.assertEqual(self.ch['name'], 'mini-dinstall-ng')
            self.assertEqual(self.ch.name, 'mini-dinstall-ng')

            self.ch.version = 2
            self.assertEqual(self.ch['version'], 2)
            self.assertEqual(self.ch.version, 2)

        def test_types(self):
            self.ch.version = '1'
            self.assertEqual(self.ch['version'], 1)
            self.assertEqual(self.ch.version, 1)

        def test_unexisting(self):
            def get_by_key():
                return self.ch['unexisting']
            def get_by_attr():
                return self.ch.unexisting
            self.assertRaises(KeyError, get_by_key)
            self.assertRaises(AttributeError, get_by_attr)
    unittest.main()
