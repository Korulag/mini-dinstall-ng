# DpkgDatalist.py
#
# This module implements DpkgDatalist, an abstract class for storing 
# a list of objects in a file. Children of this class have to implement
# the load and _store methods.
#
# Copyright 2001 Wichert Akkerman <wichert@linux.com>
#
# This file is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

import os, sys
from UserDict import UserDict
from OrderedDict import OrderedDict
from minidinstall.SafeWriteFile import SafeWriteFile

class DpkgDatalistException(Exception):
    UNKNOWN     = 0
    SYNTAXERROR = 1

    def __init__(self, message="", reason=UNKNOWN, file=None, line=None):
        self.message=message
        self.reason=reason
        self.filename=file
        self.line=line

class _DpkgDatalist:
    def __init__(self, fn=""):
        '''Initialize a DpkgDatalist object. An optional argument is a
        file from which we load values.'''

        self.filename=fn
        if self.filename:
            self.load(self.filename)

    def load(fn):
        raise NotImplementedError()

    def store(self, fn=None):
        "Store variable data in a file."

        if type(fn) == str:
            # Write to a temporary file first
            vf = SafeWriteFile(fn+".new", fn, "w")
        else:
            # use filename as a file handle
            vf = fn
        try:
            self._store(vf)
        finally:
            if type(fn) == str:
                vf.close()


class DpkgDatalist(UserDict, _DpkgDatalist):
    def __init__(self, fn=""):
        UserDict.__init__(self)
        _DpkgDatalist.__init__(self, fn)


class DpkgOrderedDatalist(OrderedDict, _DpkgDatalist):
    def __init__(self, fn=""):
        OrderedDict.__init__(self)
        _DpkgDatalist.__init__(self, fn)

# vim:ts=4:sw=4:et:
