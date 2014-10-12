# SignedFile -*- mode: python; coding: utf-8 -*-
'''
SignedFile offers a subset of file object operations, and is
designed to transparently handle files with PGP signatures.
'''
# Copyright © 2002 Colin Walters <walters@gnu.org>
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

import re,string

class SignedFile(object):
    #: The file handle
    _stream = None
    _eof = False
    _signed = False
    _signature = None
    _signatureversion = None
    _initline = None

    def __init__(self, stream):
        self._stream = stream
        line = stream.readline()
        if line == "-----BEGIN PGP SIGNED MESSAGE-----\n":
            self._signed = True
            while line and line != '\n':
                line = stream.readline()
        else:
            self._initline = line

    def readline(self):
        if self._eof:
            return ''
        if self._initline:
            line = self._initline
            self._initline = None
        else:
            line = self._stream.readline()
        if not self._signed:
            return line
        elif line == "-----BEGIN PGP SIGNATURE-----\n":
            self._eof = 1
            self._signature = []
            self._signatureversion = self._stream.readline()
            if ':' in self._signatureversion:
                self._signatureversion = self._signatureversion.split(':',1)[1]
            self._signatureversion = self._signatureversion.strip()
            self._stream.readline()  # skip blank line
            while True:
                line = self._stream.readline()
                if not line or line == "-----END PGP SIGNATURE-----\n":
                    break
                self._signature.append(line)
            self._signature = ''.join(self._signature)
            return ''
        return line

    def readlines(self):
        ret = []
        while 1:
            line = self.readline()
            if line != '':
                ret.append(line)
            else:
                break
        return ret

    def close(self):
        self._stream.close()

    def getSigned(self):
        return self._signed

    signed = property(getSigned)

    def getSignature(self):
        return self._signature
    signature = property(getSignature)

    def getSignatureVersion(self):
        return self._signatureversion

    singature_version = property(getSignatureVersion)

def main(args):
    if len(args) == 0:
        print("Need one file as an argument")
        return 1
    filename = args[0]
    with open(filename) as infile:
        actuallines = infile.readlines()

    with open(filename) as infile:
        f = SignedFile(infile)
        if f.getSigned():
            print("**** SIGNED ****")
        else:
            print("**** NOT SIGNED ****")
        lines = f.readlines()
        print(lines)
        if not f.getSigned():
            assert(len(lines) == len(actuallines))
        else:
            print("Signature: %s" % (f.getSignature()))

if __name__=="__main__":
    import sys
    import unittest

    class TestSignedFile(unittest.TestCase):
        signed = '../test/signed_file'
        unsigned = '../test/unsigned_file'
        def test_read_signed(self):
            with open(self.signed,'r') as infile:
                f = SignedFile(infile)
                lines = f.readlines()
            self.assertEqual(f.singature_version, 'GnuPG v2')
            self.assertEqual(f.signature, '''iQEcBAEBAgAGBQJUOs4yAAoJEMI9pZ72muJzaBAIAMB+aLOsAIG7xva7z6jjtEti
a9uUnWpeJCCZYfmj0ZX1lpzrcwRLPfmzbAgC3JZ0gzAsyhX6ysNPIHF3BhmF1Yvy
8guhkUtjrao3DvE397QlzUIrJSW+/RLniPuLdYDDJLUasaWOR2kkOVIPdHtYnoAT
k9LIUippc/NkX6m4qZjahHWAeSvbAdjEjt7Wznd884OdEnNTAHHp2L8q9lf9mlw7
Y0vfe+QuFXfsK0587q3LGLGdAcpep9lwCUbB3dxDVTt1XuByovXup0+M9Mm6yg99
fBUDSfrkYXPt+57IIhgNE07na4Wz+hXK22M4RH3RsHRBdvU9M/g+Et17LUCf3eM=
=Nc23
''')

    unittest.main()



# vim:ts=4:sw=4:et:
