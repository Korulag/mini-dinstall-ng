#!/usr/bin/env python3
# SignedFile -*- mode: python; coding: utf-8 -*-
#-----------------------------------------------------------------------------
'''

This code was originally written by Colin Alters <walters@gnu.org>. So give
him the credits and blame me <l34k@bk.ru> for bugs.
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

from minidinstall_ng.error import DinstallException
from minidinstall_ng import sockethandler
from minidinstall_ng import commands
import threading
try:
    import queue
except ImportError:
    import Queue as queue

class IncomingDir(threading.Thread):
    '''
    Worker which keeps control over a single incoming folder.
    :param dir: The directory to listen on
    :param archivemap: whut config?
    :param die_event: :class:`threading.Event` which is set when a unhandled
                      error occurs.
    :param logger: The logger to use.
    :param trigger_reindex: Whether or not to trigger a reindex.
    '''
    def __init__(self, dir, archivemap, die_event, logger, trigger_reindex=1,
                 poll_time=30, max_retry_time=172800, batch_mode=0):
        threading.Thread.__init__(self, name="incoming")

        self._die_event = die_event
        self._dir = dir
        self._archivemap = archivemap
        self._logger = logger
        self._trigger_reindex = trigger_reindex
        self._poll_time = poll_time
        self._batch_mode = batch_mode
        self._max_retry_time = max_retry_time
        self._last_failed_targets = {}
        self._eventqueue = queue.Queue()
        # ensure we always have some reprocess queue
        self._reprocess_queue = {}
        self.reprocess_needed = threading.Event()
        self._done_event = threading.Event()
        self._task_queue = queue.Queue()
        self._reprocess_event = threading.Event()

    def run(self):
        '''
        The actual thread functionality.
        '''
        self._logger.info('Created new installer thread (%s)' % (self.getName(),))
        self._logger.info('Entering batch mode...')
        initial_reprocess_queue = []
        initial_fucked_list = []
        try:
            for (changefilename, changefile) in self._get_changefiles():
                if self._changefile_ready(changefilename, changefile):
                    try:
                        self._install_changefile(changefilename, changefile, 0)
                    except Exception:
                        self._logger.exception("Unable to install \"%s\"; adding to screwed list" % (changefilename,))
                        initial_fucked_list.append(changefilename)
                else:
                    self._logger.warn('Skipping "%s"; upload incomplete' % (changefilename,))
                    initial_reprocess_queue.append(changefilename)
            if not self._batch_mode:
                self._daemonize(initial_reprocess_queue, initial_fucked_list)
            self._done_event.set()
            self._logger.info('All packages in incoming dir installed; exiting')
        except Exception as e:
            self._logger.exception("Unhandled exception; shutting down")
            self._die_event.set()
            self._done_event.set()
            return 0

    def _abspath(self, *args):
        return os.path.abspath(apply(os.path.join, [self._dir] + list(args)))

    def _get_changefiles(self):
        ret = []
        globpath = self._abspath("*.changes")
        self._logger.debug("glob: " + globpath)
        changefilenames = glob.glob(globpath)
        for changefilename in changefilenames:
            if not self._reprocess_queue.has_key(changefilename):
                self._logger.info('Examining "%s"' % (changefilename,))
                changefile = ChangeFile()
                try:
                    changefile.load_from_file(changefilename)
                except ChangeFileException:
                    self._logger.debug("Unable to parse \"%s\", skipping" % (changefilename,))
                    continue
                ret.append((changefilename, changefile))
            else:
                self._logger.debug('Skipping "%s" during new scan because it is in the reprocess queue.' % (changefilename,))
        return ret

    def _changefile_ready(self, changefilename, changefile):
        try:
            dist = changefile['distribution']
        except KeyError as e:
            self._logger.warn("Unable to read distribution field for \"%s\"; data: %s" % (changefilename, changefile,))
            return 0
        try:
            changefile.verify(self._abspath(''))
        except ChangeFileException:
            return 0
        return 1

    def _install_changefile(self, changefilename, changefile, doing_reprocess):
        changefiledist = changefile['distribution']
        for dist in distributions.keys():
            distributions[dist] = distoptionhandler.get_option_map(dist)
            if distributions[dist]['alias'] != None and changefiledist in distributions[dist]['alias']:
                self._logger.info('Distribution "%s" is an alias for "%s"' % (changefiledist, dist))
                break
            else:
                dist = changefiledist
        if not dist in self._archivemap.keys():
            raise DinstallException('Unknown distribution "%s" in \"%s\"' % (dist, changefilename,))
        self._logger.debug('Installing %s in archive %s' % (changefilename, self._archivemap[dist][1].getName()))
        self._archivemap[dist][0].install(changefilename, changefile)
        if self._trigger_reindex:
            if doing_reprocess:
                self._logger.debug('Waiting on archive %s to reprocess' % (self._archivemap[dist][1].getName()))
                self._archivemap[dist][1].wait_reprocess()
            else:
                self._logger.debug('Notifying archive %s of change' % (self._archivemap[dist][1].getName()))
                self._archivemap[dist][1].notify()
            self._logger.debug('Finished processing %s' % (changefilename))

    def _reject_changefile(self, changefilename, changefile, e):
        dist = changefile['distribution']
        if not dist in self._archivemap:
            raise DinstallException('Unknown distribution "%s" in \"%s\"' % (dist, changefilename,))
        self._archivemap[dist][0].reject(changefilename, changefile, e)

    def _get_socket_server(self, socket_name):
        data = {}
        data['logger'] = self._logger
        data['die_event'] = self._die_event
        Server = type('MyIncomingSocketServer', (sockethandler.RequestServer,), data)
        Handler = type('MyIncomingRequestHandler', (sockethandler.IncomingRequestHandler,), data)
        return Server(socket_name, Handler)

    def _daemon_server_isready(self):
        (inready, outready, exready) = select.select([self._server.fileno()], [], [], 0)
        return len(inready) > 0

    def _daemon_event_ispending(self):
        return self._die_event.isSet() or reprocess_needed.isSet() or self._daemon_server_isready() or (not self._eventqueue.empty())

    def _daemon_its_time_to_reprocess(self):
        curtime = time.time()
        for changefilename in self._reprocess_queue.keys():
            (starttime, nexttime, delay) = self._reprocess_queue[changefilename]
            if curtime >= nexttime:
                return 1
        return 0

    def reprocess(self):
        '''
        Trigger reprocessing
        '''
        self._task_queue.put(commands.RUN)

    def _daemonize(self, init_reprocess_queue, init_fucked_list):
        '''
        Enter the 
        '''
        self._logger.info('Entering daemon mode...')
        self._dnotify = DirectoryNotifierFactory().create([self._dir], use_dnotify=use_dnotify, poll_time=self._poll_time, cancel_event=self._die_event)
        self._async_dnotify = DirectoryNotifierAsyncWrapper(self._dnotify, self._eventqueue, logger=self._logger, name="Incoming watcher")
        self._async_dnotify.start()
        try:
            os.unlink(socket_name)
        except EnvironmentError as e:
            pass
        self._server = self._get_socket_server(socket_name)
        self._server.allow_reuse_address = 1
        self._server.server_forever()
        retry_time = 30
        self._reprocess_queue = {}
        fucked = init_fucked_list
        doing_reprocess = 0
        # Initialize the reprocessing queue
        for changefilename in init_reprocess_queue:
            curtime = time.time()
            self._reprocess_queue[changefilename] = (curtime, curtime, retry_time)

        # The main daemon loop
        while 1:
            if not self._daemon_server_isready():
                self._logger.debug("daemon server not ready")
            
            # handle text commands (from socket server)
            try:
                task = self._task_queue.get_nowait()
            except queue.Empty:
                # no commands
                if self._daemon_its_time_to_reprocess():
                    self._reprocess_event.set()
            else:
                if task == commands.RUN:
                    self._reprocess_event.set()
                    pass
                elif task == commands.DIE:
                    self._logger.debug('DIE command caught.')
                    self._die_event.set()

            # handle events
            if self._die_event.is_set():
                self._logger.debug('DIE event caught. Shutting down server...')
                self._server.shutdown()
                self._logger.debug("Server shut down. Quitting.")
                break

            if not self._reprocess_event.is_set():
                time.sleep(0.5)
                continue


            self._logger.debug('Scanning for changes')
            # do we have anything to reprocess?
            for changefilename in self._reprocess_queue.keys():
                (starttime, nexttime, delay) = self._reprocess_queue[changefilename]
                curtime = time.time()
                try:
                    changefile = ChangeFile()
                    changefile.load_from_file(changefilename)
                except (ChangeFileException, IOError) as e:
                    if not os.path.isfile(changefilename):
                        self._logger.info('Changefile "%s" got removed' % (changefilename,))
                    else:
                        self._logger.exception("Unable to load change file \"%s\"" % (changefilename,))
                        self._logger.warn("Marking \"%s\" as screwed" % (changefilename,))
                        fucked.append(changefilename)
                    del self._reprocess_queue[changefilename]
                    continue
                if (curtime - starttime) > self._max_retry_time:
                    # We've tried too many times; reject it.
                    self._reject_changefile(changefilename, changefile, DinstallException("Couldn't install \"%s\" in %d seconds" % (changefilename, self._max_retry_time)))
                elif curtime >= nexttime:
                    if self._changefile_ready(changefilename, changefile):
                        # Let's do it!
                        self._logger.debug('Preparing to install "%s"' % (changefilename,))
                        try:
                            self._install_changefile(changefilename, changefile, doing_reprocess)
                            self._logger.debug('Removing "%s" from incoming queue after successful install.' % (changefilename,))
                            del self._reprocess_queue[changefilename]
                        except Exception as e:
                            self._logger.exception("Unable to install \"%s\"; adding to screwed list" % (changefilename,))
                            fucked.append(changefilename)
                    else:
                        delay *= 2
                        if delay > 60 * 60:
                            delay = 60 * 60
                        self._logger.info('Upload "%s" isn\'t complete; marking for retry in %d seconds' % (changefilename, delay))
                        self._reprocess_queue[changefilename][1:3] = [time.time() + delay, delay]
            # done reprocessing; now scan for changed dirs.
            relname = None
            self._logger.debug('Checking dnotify event queue')
            if not self._eventqueue.empty():
                relname = os.path.basename(os.path.abspath(self._eventqueue.get()))
                self._logger.debug('Got %s from dnotify' % (relname,))
            if relname is None:
                if (not doing_reprocess) and reprocess_needed.isSet():
                    self._logger.info('Got reprocessing event')
                    reprocess_needed.clear()
                    doing_reprocess = 1
            if relname is None and (not doing_reprocess):
                self._logger.debug('No events to process')
                continue

            for (changefilename, changefile) in self._get_changefiles():
                if changefilename in fucked:
                    self._logger.warn("Skipping screwed changefile \"%s\"" % (changefilename,))
                    continue
                # Have we tried this changefile before?
                if not self._reprocess_queue.has_key(changefilename):
                    self._logger.debug('New change file "%s"' % (changefilename,))
                    if self._changefile_ready(changefilename, changefile):
                        try:
                            self._install_changefile(changefilename, changefile, doing_reprocess)
                        except Exception as e:
                            self._logger.exception("Unable to install \"%s\"; adding to screwed list" % (changefilename,))
                            fucked.append(changefilename)
                    else:
                        curtime = time.time()
                        self._logger.info('Upload "%s" isn\'t complete; marking for retry in %d seconds' % (changefilename, retry_time))
                        self._reprocess_queue[changefilename] = [curtime, curtime + retry_time, retry_time]
            if doing_reprocess:
                doing_reprocess = 0
                self._logger.info('Reprocessing complete')
                self._server.reprocess_done.set()

    def wait(self):
        self._done_event.wait()
