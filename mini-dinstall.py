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

import argparse



class MiniDinstall(object):

    def __init__(self):
        pass

    def main(self, args):
        arguments = self.parse_args(args)



parser = argparse.ArgumentParser(prog='mini-dinstall',
                                 # disabled manual usage definition because the built-in is good enough
                                 #usage='mini-dinstall [OPTIONS...] [DIRECTORY]',
                                 description='Copyright (C) 2002 Colin Walters <walters@gnu.org>\nLicensed under the GNU GPL.')
parser.add_argument('-v', '--verbose', action="store_true", help="Display extra information")
parser.add_argument('-q', '--quiet', action="store_true", help="Display less information")
parser.add_argument('-c', '--config', metavar="FILE", help='Parse configuration info from FILE', default=None)
parser.add_argument('-d', '--debug', action='store_true', help='Output information to stdout as well as log')
parser.add_argument('--no-log', action='store_true', help='Don\'t write information to log file')
parser.add_argument('-n', '--no-act', action='store_true', help='Don\'t actually perform changes')
parser.add_argument('-b', '--batch', action='store_true', help='Don\'t daemonize; run once, then exit')
parser.add_argument('-r', '--run', action='store_true', help='Process queue immediately')
parser.add_argument('-k', '--kill', action='store_true', help='Kill the running mini-dinstall')
parser.add_argument('--no-db', action='store_true', help='Disable lookups on package database')
parser.add_argument('--version', action='version', version='%(prog)s ' + pkg_version, help='Print the software version and exit')
parser.add_argument('DIRECTORY', nargs='?', default=None)

# map argumentparser functionallity to class.
MiniDinstall.parse_args = parser.parse_args


