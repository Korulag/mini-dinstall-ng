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
from minidinstall_ng.config import ConfigHandler
from minidinstall_ng import config_types as types
from minidinstall_ng.version import pkg_version
import logging
# to get the username:
import getpass
import os

class MiniDinstall(object):

    defaults = {
        'toplevel_directory':(str, None),
        'log_level':(types.loglevel, logging.WARN),
        'rejectdir':(str, 'REJECT'),
        'lockfilename':(str, 'mini-dinstall.lock'),
        'dinstall_subdir':(str, 'mini-dinstall'),
        'incoming_subdir':(str, 'incoming'),
        'socket_name':(str, 'master'),
        'logfile_name':(str, 'mini-dinstall.log'),
        'use_dnotify':(types.str_bool, False),
        'trigger_reindex':(int, 1),
        'incoming_permissions':(types.IntWithBase(8), int('750', 8)),
        'configfiles':(types.StrList(type=types.path), ['/etc/mini-dinstall.conf', '~/.mini-dinstall.conf']),
        
        'arches':(types.str_list, ('all', 'i386', 'amd64')),
        'distributions':(types.str_list, ('unstable',)),
        # 
        'alias': (str, None),
        'poll_time':(int, 30),
        'max_retry_time':(int, 2 * 24 * 60 * 60),
        'mail_on_success':(types.str_bool, True),
        'mail_log_level':(types.loglevel, logging.ERROR),
        'mail_log_flush_level':(types.loglevel, logging.ERROR),
        'mail_log_flush_count':(int, 10),
        'mail_to':(str, getpass.getuser()),
        'mail_server':(str, 'localhost'),
        'mail_subject_template':(str, "mini-dinstall: Successfully installed %(source)s %(version)s to %(distribution)s"),
        'mail_body_template': (str,   ('Package: %(source)s\n' + 
                                       'Maintainer: %(maintainer)s\n' + 
                                       'Changed-By: %(changed-by)s\n' +
                                       'Changes:\n' +
                                       '%(changes_without_dot)s\n')),
        'tweet_on_success':(types.str_bool, False),
        'tweet_server':(str, 'identica'),
        'tweet_user':(str, None),
        'tweet_password':(str, None),
        'tweet_template':(str, "Installed %(source)s %(version)s to %(distribution)s"),
        'archive_style':(str, 'flat'),
        'extra_keyrings':(types.str_list, ()),
        'keyrings':(types.str_list, None),
        'verify_sigs':(types.str_bool, os.access('/usr/share/keyrings/debian-keyring.gpg', os.R_OK)),
        'post_install_script': (str, None),
        'pre_install_script': (str, None),
        'dynamic_reindex': (types.str_bool, True),
        'chown_changes_files': (types.str_bool, True),
        'keep_old': (types.str_bool, False),
        'generate_release': (types.str_bool, False),
        'release_origin': (str, getpass.getuser()),
        'release_label': (str, getpass.getuser()),
        'release_suite': (str, None),
        'release_codename':  (str, None),
        'experimental_release': (types.str_bool, 0),
        'release_description': (str, None),
        'release_signscript': (str, None)
    }

    def __init__(self):
        self.__dist_default = None
        

    def main(self, args):
        arguments = self.parse_args(args)

        config = ConfigHandler(self.defaults, additional_arguments=[arguments.config])



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


