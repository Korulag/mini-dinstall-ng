#!/usr/bin/env python3
# SignedFile -*- mode: python; coding: utf-8 -*-
#-----------------------------------------------------------------------------
'''
Description goes here
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

import argparse
from minidinstall_ng.config import ConfigHandler
from minidinstall_ng import config_types as types
from minidinstall_ng.version import pkg_version
from minidinstall_ng.osactions import OsActions
import minidinstall_ng.pidlock as lock
from minidinstall_ng import sockethandler
import threading
import logging
import sys
# to get the username:
import getpass
import os
import time

SUCCESS = 0
ERROR_CONFIG = 1
ERROR_LOCK = 2
ERROR_INV_LOCK = 3

class MiniDinstall(object):
    '''
    The main mini-dinstall class.

    If you just want to run the mini-dinstall you can call the 
    :meth:`main()`.
    '''
    defaults = {
        'archivedir':(str, None),
        'log_level':(types.loglevel, logging.WARN),
        'log_name': 'mini-dinstall',
        'log_format': (str, "%(name)s [%(thread)d] %(levelname)s: %(message)s"),
        'rejectdir':(str, 'REJECT'),
        'lockfile':(str, 'mini-dinstall.lock'),
        'subdirectory':(str, 'mini-dinstall'),
        'incoming':(str, 'incoming'),
        'incoming_permissions':(types.IntWithBase(8), int('750', 8)),
        'socket_name':(str, 'master'),
        'socket_permissions':(types.IntWithBase(8), int('750', 8)),
        'logfile_name':(str, 'mini-dinstall.log'),
        'use_dnotify':(types.str_bool, False),
        'trigger_reindex':(int, 1),
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

        # These global variables are used in IncomingDir::daemonize
        # I couldn't figure out any way to pass state to a BaseRequestHandler.
        self.die_event = threading.Event()
        self.reprocess_needed = threading.Event()
        self.reprocess_finished = threading.Event()
        self.reprocess_lock = threading.Lock()

    # -> to worker
    # def _get_socket_server(self):
    #     data = {}
    #     data['logger'] = self.logger
    #     data['die_event'] = self.die_event
    #     Server = type('MyIncomingSocketServer', (sockethandler.RequestServer,), data)
    #     data['reprocess_lock'] = self.reprocess_lock
    #     data['reprocess_finished'] = self.reprocess_finished
    #     Handler = type('MyIncomingRequestHandler', (sockethandler.IncomingRequestHandler,), data)
    #     server = Server()


    def _config_paths(self, arguments):
        if self.c.archivedir is None and not arguments.DIRECTORY:
            self.logger.error('\'archivedir\' not given')
            return ERROR_CONFIG
        elif not arguments.DIRECTORY:
            toplevel = self.c.archivedir
        else:
            toplevel = os.path.abspath(arguments.DIRECTORY)

        if not os.path.isabs(toplevel):
            self.logger.error('Top level directory in config file has to be absolute.')
            return ERROR_CONFIG

        if not os.path.isdir(toplevel):
            self.logger.error('Directory %r does not exist' % toplevel)
            return ERROR_CONFIG

        self.toplevel_dir = os.path.abspath(toplevel)
        if os.path.isabs(self.c.subdirectory):
            self.subdir = os.path.abspath(os.path.join(self.toplevel_dir, self.c.subdirectory))
        else:
            self.subdir = self.c.subdirectory
        self.os.mkdir(self.subdir)
        self.os.mkdir(self.c.incoming)
        return SUCCESS

    def _get_logger(self, arguments):
        log_level = self.c.log_level
        # if quiet use at most WARN
        if arguments.quiet and log_level < logging.WARN:
            log_level = logging.WARN
        # if verbose use at least INFO
        if arguments.verbose and log_level > logging.INFO:
            log_level = logging.INFO
        # if debug use at least DEBUG
        if arguments.debug and log_level > logging.DEBUG:
            log_level = logging.DEBUG
        logger = logging.getLogger(self.c.log_name)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(fmt=self.c.log_format)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(log_level)
        return logger

    def _config_logfile(self, arguments):
        if not arguments.no_log:
            if not os.path.isabs(self.c.logfile_name):
                logfile = os.path.join(self.c.logfile_name, self.c.logfile_name)
            else:
                logfile = self.c.logfile_name

    def main(self, args):
        arguments = self.parse_args(args)
        add_files = None
        if arguments.config:
            add_files = [arguments.config]
        self.config = ConfigHandler(self.defaults, additional_files=add_files)
        self.c = self.config.all
        self.logger = self._get_logger(arguments)
        self.os = OsActions(arguments.no_act, self.logger)
        errno = self._config_paths(arguments)
        if errno:
            return errno

        if os.path.isabs(self.c.lockfile):
            self.lockfile = lock.PIDLock(self.c.lockfile)
        else:
            self.lockfile = lock.PIDLock(os.path.join(self.subdir, self.c.lockfile))

        errno = self._config_logfile(arguments)
        if errno:
            return errno
        if arguments.run:
            return self.trigger()
        elif arguments.kill:
            return self.kill()
        else:
            return self.run(not arguments.batch)

    def kill(self):
        try:
            self.lockfile.acquire()
        except lock.IsLocked as why:
            if why.valid:
                pid = why.pid
            else:
                self.logger.info("Removing invalid lockfile (%s)" % why.msg)
                lock.remove()
                return SUCCESS
        else:
            self.logger.info("No process running.")
            return SUCCESS

        self.logger.info("Sending DIE signal to process (pid %d)" % pid)


    def run(self, daemonize, ):
        try:
            self.lockfile.acquire()
        except lock.IsLocked as why:
            if why.valid:
                self.logger.error('Process already running at pid %d' % why.pid)
                return ERROR_LOCK
            else:
                self.logger.error('Invalid lockfile existing (%s). Use -k to remove it.' % why.msg)
                return ERROR_INV_LOCK
        if daemonize:
            self.logger.debug("daemonizing...")
            child_pid = os.fork()
            if child_pid == 0:
                # I'm the child
                os.setsid()
                child_pid = os.fork()
                if child_pid != 0:
                    # I'm the useless fork in between :(
                    os._exit(0)
            else:
                # I'm the parent and I go to let the shell serve the user :)
                os._exit(0)
            self.logger.debug("Finished daemonizing (pid %s)" % (os.getpid(),))
        


        if daemonize:
            self.logger.debug('waiting for die event')
            self.die_event.wait()
            self.logger.debug('die event caught. waiting for incom-dir worker to finish')
            self.incom_thread.join()            

        self.logger.debug("Process done %d" % os.getpid())
        self.lockfile.release()
        return SUCCESS


parser = argparse.ArgumentParser(prog='mini-dinstall',
                                 # disabled manual usage definition because the built-in is good enough
                                 #usage='mini-dinstall [OPTIONS...] [DIRECTORY]',
                                 description='Copyright (C) 2002 Colin Walters <walters@gnu.org>\nLicensed under the GNU GPL.')
parser.add_argument('-v', '--verbose', action="store_true", help="Display extra information. Overrides quiet flag")
parser.add_argument('-q', '--quiet', action="store_true", help="Display less information")
parser.add_argument('-d', '--debug', action='store_true', help='Output information to stdout as well as log. Overrides verbose and quiet flags')
parser.add_argument('-c', '--config', metavar="FILE", help='Parse configuration info from FILE', default=None)
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

if __name__ == '__main__':
    minidinstall = MiniDinstall()
    minidinstall.main(sys.argv[1:])
