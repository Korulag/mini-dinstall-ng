#!/usr/bin/env python3
from collections import UserDict

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
        if name[0] != '_':
            return self[name]
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
                'version':(int, 0)
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

    unittest.main()
