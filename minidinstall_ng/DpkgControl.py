# DpkgControl.py
'''
This module implements control file parsing.

DpkgParagraph is a low-level class, that reads/parses a single paragraph
from a file object.

DpkgControl uses DpkgParagraph in a loop, pulling out the value of a
defined key(package), and using that as a key in it's internal
dictionary.

DpkgSourceControl grabs the first paragraph from the file object, stores
it in object.source, then passes control to DpkgControl.load, to parse
the rest of the file.

To test this, pass it a filetype char, a filename, then, optionally,
the key to a paragraph to display, and if a fourth arg is given, only
show that field.
'''
#
# Copyright 2001 Adam Heath <doogie@debian.org>
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

__all__ = ['DpkgParagraph', 'DpkgControl', 'DpkgSourceControl']

import sys
from DpkgDatalist import *
from minidinstall.SignedFile import *
from types import ListType

class DpkgParagraph(DpkgOrderedDatalist):
    
    case_sensitive = False

    def __init__(self, *args, **kwargs):
        DpkgOrderedDatalist.__init__(self, *args, **kwargs)

        #: This dictionary is only needed when using
        #: :attr:`case_sensitive` set to :const:`False`.
        #: Then here are stored the real cased keys
        self.trueFieldCasing = {}
        # moved this defition to the constructor
        # so multiple instanced don't use the same
        # dictionary

    def setcase_sensitive( self, value ):
        self.case_sensitive = value

    def load(self, f):
        '''
        Read paragraph data from a file object.
        :param f: A file like object with the method f.readline()
        '''
        key = None
        value = None
        while True:
            line = f.readline()
            if not line: # EOF?
                return
            # skip blank lines until we reach a paragraph
            if line == '\n':
                if not self:
                    # we don't contain anything yet
                    continue
                else:
                    # We're already done
                    # EOP (End of Paragraph)
                    return
            line = line[:-1]
            if line[0] != ' ':
                splited = line.split(":", 1)
                if len(splited) != 2:
                    # FIXME: raise some error
                    pass
                key, value = splited
                if value:
                    value = value.strip()
                if not self.case_sensitive:
                    newkey = key.lower()
                    # FIXME: why check if it containes "key" and not "newkey"?
                    if not key in self.trueFieldCasing:
                        self.trueFieldCasing[newkey] = key
                    key = newkey
            else:
                # continued line
                if not type(value) == list:
                    value = [value]
                value.append(line[1:])

            self[key] = value

    def _storeField(self, f, value, lead=''):
        '''
        :param f: File handle
        :param value: The value write
        :param lead: Leading characters. Appended in front of each line.
        '''
        if isinstance(value, list):
            value = '\n'.join(map( lambda v, lead = lead: v and ( lead + v ) or v, value ))
        else:
            if value:
                value = lead + str(value)
        f.write(value + '\n')

    def _store(self, f):
        '''
        Write our paragraph data to a file object

        :param f: File handle
        ''''
        for key, value in self.items():
            if key in self.trueFieldCasing:
                key = self.trueFieldCasing[key]
            f.write(str(key) + ":" )
            self._storeField(f, value)

class DpkgControl(DpkgOrderedDatalist):

    key = "package"
    case_sensitive = False

    def setkey( self, key ):
        self.key = key
    
    def setcase_sensitive( self, value ):
        self.case_sensitive = value

    def _load_one( self, f ):
        '''
        Loads the next :class:`DpkgParagraph̀` from 
        file and returns it.
        :param f: Filehandle
        '''
        p = DpkgParagraph(None)
        p.case_sensitive = self.case_sensitive
        p.load(f)
        return p

    def load(self, f):
        while 1:
            p = self._load_one( f )
            if not p:
                break
            self[p[self.key]] = p

    def _store( self, f ):
        "Write our control data to a file object"

        for key in self.keys():
            self[key]._store(f)
            f.write('\n')

class DpkgSourceControl(DpkgControl):
    source = None

    def load(self, f):
        f = SignedFile(f)
        self.source = self._load_one(f)
        DpkgControl.load(self, f)

    def __repr__( self ):
        return repr(self.source) + "\n" + DpkgControl.__repr__( self )

    def _store( self, f ):
        "Write our control data to a file object"
        self.source._store(f)
        f.write( "\n" )
        DpkgControl._store(self, f)

def main(args):
    '''
    Usage: prog.py <type> <file> [paragraph [key]]
    '''
    types = { 'p' : DpkgParagraph, 'c' : DpkgControl, 's' : DpkgSourceControl }
    type_ = args[0]
    if not type_ in types:
        print("Unknown type `%s'!" % type_)
        return 1
    file_ = open(args[1], "r" )
    data = types[type_]()
    data.load(file_)
    if len(args) > 2:
        para = data[args[2]]
        if len(args) > 3:
            para._storeField( sys.stdout, para[args[3]], "" )
        else:
            para._store( sys.stdout )
    else:
        data._store( sys.stdout )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
# vim:ts=4:sw=4:et:
