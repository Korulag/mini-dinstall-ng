#!/usr/bin/env python3
# SignedFile -*- mode: python; coding: utf-8 -*-
#-----------------------------------------------------------------------------
'''
Exceptions
'''
#-----------------------------------------------------------------------------
# Copyright (c) 2014  c0ff3m4kr <l34k@bk.ru>
#
# This program may use source code parts from the original mini-dinstall
# which is published under the GNU General Public License. 
# Copyright (c) 2002,2003 Colin Walters <walters@gnu.org>
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

class DinstallException(Exception):
	'''
	Base class for all non-standard exceptions raised.
	'''
	pass

class ChangeFileException(DinstallException):
	pass