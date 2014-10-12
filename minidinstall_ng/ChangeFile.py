# ChangeFile

# A class which represents a Debian change file.

# Copyright 2002 Colin Walters <walters@gnu.org>

# This file is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

import os, re, sys, string, stat
import threading
try:
    import queue
except ImportError:
    import Queue as queue
import logging
from minidinstall_ng import DpkgControl, SignedFile
from minidinstall_ng import misc
from minidinstall_ng import hasher

class ChangeFileException(Exception):

    def __init__(self, value):
        self._value = value

    def __str__(self):
        return str(self._value)

class ChangeFile(DpkgControl.DpkgParagraph):
    '''
    Object representing a changefile.
    '''
    md5_re = r'^(?P<md5>[0-9a-f]{32})[ \t]+(?P<size>\d+)[ \t]+(?P<section>[-/a-zA-Z0-9]+)[ \t]+(?P<priority>[-a-zA-Z0-9]+)[ \t]+(?P<file>[0-9a-zA-Z][-+:.,=~0-9a-zA-Z_]+)$'
    sha1_re = r'^(?P<sha1>[0-9a-f]{40})[ \t]+(?P<size>\d+)[ \t]+(?P<file>[0-9a-zA-Z][-+:.,=~0-9a-zA-Z_]+)$'
    sha256_re = r'^(?P<sha256>[0-9a-f]{64})[ \t]+(?P<size>\d+)[ \t]+(?P<file>[0-9a-zA-Z][-+:.,=~0-9a-zA-Z_]+)$'

    hashes = { 'md5': ['files', re.compile(md5_re)],
               'sha1': ['checksums-sha1', re.compile(sha1_re)],
               'sha256': ['checksums-sha256', re.compile(sha256_re)]
             }

    def __init__(self):
        DpkgControl.DpkgParagraph.__init__(self)
        self._logger = logging.getLogger("mini-dinstall")
        self._file = ''

    def load_from_file(self, filename):
        self._file = filename
        f = SignedFile.SignedFile(open(self._file))
        self.load(f)
        f.close()

    @classmethod
    def from_file(cls, filename):
        obj = cls()
        obj.load_from_file(filename)

    def getFiles(self):
        return self._get_checksum_from_changes()['md5']

    def _get_checksum_from_changes(self):
        """ extract checksums and size from changes file """
        output = {}
        if not 'files' in self:
            return output
        for hash, (hash_key, regex) in self.hashes.items():
            if not hash_key in self:
                self._logger.warn("Can't find %s checksum in changes file '%s'" % (hash, os.path.basename(self._file)))
                continue
            output[hash] = []
            for line in self[hash_key]:
                if line == '':
                    continue
                match = regex.match(line)
                if match is None:
                    raise ChangeFileException("Couldn't parse file entry \"%s\" in Files field of .changes" % line)
                output[hash].append((match.group(hash), int(match.group('size')), match.group('file'))
        return output

    def verify(self, sourcedir):
        '''
        verify size and hash values from changes file
        '''
        checksums = self._get_checksum_from_changes()
        for hash, (hashsum, size, filename) in checksum[hash].items():
            self._verify_file_integrity(os.path.join(sourcedir, filename), size, hash, hashsum)


    def _verify_file_integrity(self, filename, expected_size, hash, expected_hashsum):
        '''
        Check a files hash, size.
        :param filename: The file to check.
        :param excepted_size: The size of the file.
        :param hash: The hashing method.
        :param excepted_hash: The expected hex digest. 

        Raises an :exc:`ChangeFileException` if the file doesn't match the expedted values.
        '''
        self._logger.debug('Checking integrity of %s' % filename)
        try:
            statbuf = os.stat(filename)
            if not stat.S_ISREG(statbuf[stat.ST_MODE]):
                raise ChangeFileException("%s is not a regular file" % (filename,))
            size = statbuf[stat.ST_SIZE]
        except OSError as e:
            raise ChangeFileException("Can't stat %s: %s" % (filename,e.strerror))
        if size != expected_size:
            raise ChangeFileException("File size for %s does not match that specified in .dsc" % (filename,))
        if (hasher.hash_file(hash, filename) != expected_hashsum):
            raise ChangeFileException("%ssum for %s does not match that specified in .dsc" % (hash, filename,))
        self._logger.debug('Verified %ssum %s and size %s for %s' % (hash, expected_hashsum, expected_size, filename))

# vim:ts=4:sw=4:et: