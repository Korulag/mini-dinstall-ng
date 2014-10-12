#!/usr/bin/env python3
# compression -*- mode: python; coding: utf-8 -*-
#-----------------------------------------------------------------------------
'''

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

import gzip
import bz2
import lzma

class MultiCompressedFile(object):
	filetypes = {
		'': open,
		'.gz': gzip.open	,
		'.bz2': bz2.open,
		'.xz': lzma.open
	}
	def __del__(self):
		for f in self.files:
			f.close()

	def __init__(self, filename, mode='r'):
		self.files = []
		self.filename = filename
		self.mode = mode

	@property
	def filenames(self):
		for ext in self.filetypes:
			yield self.filename + ext

	def __enter__(self):
		for ext, type_ in self.filetypes.items():
			self.files.append(type_(self.filename+ext, self.mode))
		return self

	def write(self, content):
		for f in self.files:
			f.write(content)

	def read(self, size=-1):
		result = self.files[0].read(size)
		for f in self.files[1:]:
			if (f.read(size) != result):
				raise RuntimeError('Different content not supported')
		return result

	def __exit__(self, type, value, tb):
		for f in self.files:
			f.close()

if __name__ == '__main__':
	import unittest, os, random
	class TestMultiCompressedFiles(unittest.TestCase):

		def test_read_write(self):
			with MultiCompressedFile('test1', 'wt')  as f:
				f.write("hi there")
			self.assertTrue(os.path.isfile('test1'))
			self.assertTrue(os.path.isfile('test1.bz2'))
			self.assertTrue(os.path.isfile('test1.gz'))
			self.assertTrue(os.path.isfile('test1.xz'))

			with MultiCompressedFile('test1', 'rt') as f:
				self.assertEqual(f.read(3), 'hi ')
				self.assertEqual(f.read(), 'there')
			for f in f.filenames:
				os.unlink(f)
	unittest.main()