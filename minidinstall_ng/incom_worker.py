#!/usr/bin/env python3
# incom_worker -*- mode: python; coding: utf-8 -*-
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
from minidinstall_ng.ChangeFile import ChangeFile
import threading
try:
    import queue
except ImportError:
    import Queue as queue


ChangeFileTask = namedtuple('ChangeFileTask', ['filename', 'start_time', 'next_time', 'delay'])

class KeyIndexedQueue(queue.Queue):
    '''
    Queue extended with a :meth:`__contains__`
    '''
    def __init__(self, key_index=0):
        queue.Queue.__init__(self)
        self._lock = threading.RLock()
        self._keys = []
        self._key_index = key_index

    def put(self, item, block=True, timeout=None):
        with self._lock:
            queue.Queue.put(self, item, block, timeout)
            self._keys.append(item[self._key_index])

    def get(self, block=True, timeout=None):
        with self._lock:
            res = queue.Queue.get(self, block, timeout)
            index = self._keys.index(res[self._key_index])
            if not index == 0:
                raise RuntimeError('Queue get item is not in keys index 0')
            del self._keys[0]
            # TODO: replace index and del with remove after testing

    def __contains__(self, value):
        with self._lock:
            res = self.value[self._key_index] in self._keys
        return res


class IncomingDirWorker(threading.Thread):
    '''
    :param cancel_event: Global shutdown signal
    :param logger:    Logger.
    :param max_retry_time: The maximal time in which we try to install 
                      a package.
    :param poll_time: Check the stop and die event at least after 
                      some seconds (default: 5).
                      If set to :const:`None` the Thread won't exit until
                      he got a new task.
    :param queue:     The queue to listen on.
    '''
    def __init__(self, archivemap, cancel_event, logger, max_retry_time,
                 fucked_list, config, queue=None, poll_time=5):
        
        threading.Thread.__init__(self, name="incom_worker")
        

        self.archivemap = archivemap
        self.cancel_event = cancel_event
        self._logger = logger
        self._max_retry_time = max_retry_time
        self._reprocess_queue = queue
        self._poll_time = poll_time
        self._shutdown_when_empty_event = threading.Event()
        self._stop_event = threading.Event()
        self.changefile_queue = queue or queue.Queue()
        self.config = config

    def stop(self):
        self._stop_event.set()

    def shutdown_when_finished(self):
        self._shutdown_when_empty_event.set()

    def run(self):
        while not (self._stop_event.is_set() or self.cancel_event.is_set()):
            try:
                task = self.changefile_queue.get(timeout=self._poll_time)             
            except queue.Empty:
                if self._shutdown_when_empty_event.is_set():
                    return
                continue
            self.process_task(task)

    def process_task(self, task):
        '''
        :returns: :const:`True` is we have to reprocess this task later and 
                  :const:`False` otherwise.
        '''
        currtime = time.time()
        if currtime - x.start_time > self._max_retry_time:
            # We've tried too many times; reject it.
            err_msg = 'Couldn\'t install "%s" in %d seconds' 
            err_msg = err_msg % (task.filename, self._max_retry_time)
            exception = DinstallException(err_msg)
            self._reject_changefile(task.filename, changefile, exception)
            return False

        re_add = None
        if task.next_time < currtime:
            try:
                changefile = ChangeFile.from_file(task.filename)
            except (ChangeFileException, IOError) as e:
                if not os.path.isfile(task.filename):
                    self._logger.info('Changefile "%s" got removed' % (task.filename,))
                else:
                    self._logger.exception('Unable to load change file "%s"' % task.filename)
                    self._logger.warn('Marking "%s" as screwed' % task.filename)
                    self.fucked.append(task.filename)
                    # TODO: Handle the screwed change file?
                return False

            if self._changefile_ready(task.filename, changefile):
                # Let's do it!
                self._logger.debug('Preparing to install "%s"' % (task.filename,))
                try:
                    self._install_changefile(task.filename, changefile, doing_reprocess)
                except:
                    self._logger.exception("Unable to install \"%s\"; adding to screwed list" % (task.filename,))
                    self.fucked.append(task.filename)
                return False
            else:
                delay = task.delay * 2
                if delay > 60 * 60:
                    delay = 60 * 60
                self._logger.info('Upload "%s" isn\'t complete; marking for retry in %d seconds' % (task.filename, delay))
                # set next time and delay
                re_add = ChangeFileTask(task.filename, task.start_time, curtime + delay, delay)
        else:
            re_add = task

        if re_add:
            try:
                self._reprocess_queue.put(re_add, timeout=2)
                return True
            except queue.Full:
                self._logger.error("Queue got full while processing packages. Don't know what to do with reprocess task!")
                return False
           

    def _install_changefile(self, filename, changefile,
                            doing_reprocess=False):
        '''
        Install a changefile.

        :param filename: Filename of the change file.
        :param changefile: :class:minidinstall_ng.ChangeFile` object.

        '''
        changefiledist = changefile['distribution']
        alias_dist = None
        for dist in self.config.distributions():
            if self.config[dist]['alias'] != None and changefiledist in distributions[dist]['alias']:
                self._logger.info('Distribution "%s" is an alias for "%s"' % (changefiledist, dist))
                alias_dist = dist
                break
        if alias_dist:
            dist = alias_dist
        else:
            dist = changefiledist
        if not dist in self.config.distributions:
            raise DinstallException('Unknown distribution "%s" in \"%s\"' % (dist, filename,))
        dist_thread_name = self.archivemap[dist][1].getName()
        self._logger.debug('Installing %s in archive %s' % (filename, dist_thread_name))
        self.archivemap[dist][0].install(filename, changefile)
        if self._trigger_reindex:
            if doing_reprocess:
                self._logger.debug('Waiting on archive %s to reprocess' % dist_thread_name)
                self.archivemap[dist][1].wait_reprocess()
            else:
                self._logger.debug('Notifying archive %s of change' % dist_thread_name)
                self.archivemap[dist][1].notify()
            self._logger.debug('Finished processing %s' % filename)

    def _reject_changefile(self, filename, changefile, e):
        dist = changefile['distribution']
        if not dist in self.archivemap:
            raise DinstallException('Unknown distribution "%s" in \"%s\"' % (dist, filename,))
        self.archivemap[dist][0].reject(filename, changefile, e)


class IncomingDir(threading.Thread):
    '''
    Worker which keeps control over a single incoming folder.
    :param dir: The directory to listen on
    :param archivemap: whut config?
    :param cancel_event: :class:`threading.Event` which is set when a unhandled
                      error occurs.
    :param logger: The logger to use.
    :param trigger_reindex: Whether or not to trigger a reindex.
    :param config: The main configuration. (Object of type 
                   :class:`minidinstall_ng.config.ConfigHandler`)
    '''
    def __init__(self, dir, archivemap, cancel_event, config, logger, 
                 trigger_reindex=1,
                 poll_time=30,
                 max_retry_time=172800,
                 batch_mode=0):
        threading.Thread.__init__(self, name="incoming")
        
        #: fucked packages. yup. fucked. 
        self.fucked = []
        self._worker = IncomingDirWorker(archivemap, cancel_event, max_retry_time)

        self.cancel_event = cancel_event
        self._dir = dir
        self._logger = logger
        self._trigger_reindex = trigger_reindex
        self._poll_time = poll_time
        self._batch_mode = batch_mode
        self._last_failed_targets = {}
        self._eventqueue = queue.Queue()
        # ensure we always have some reprocess queue
        self._reprocess_queue = CheckedIndexedQueue()
        self._done_event = threading.Event()
        self._task_queue = queue.Queue()
        self._rescan_event = threading.Event()
        self._reprocess_event = threading.Event()
        self._server = None
        self._dnotify = None
        self._async_dnotify = None
        # backwards compatibility
        self.wait = self.join
        self._workers = []


    def run(self):
        '''
        The actual thread functionality.
        '''
        self._logger.info('Created new installer thread (%s)' % (self.getName(),))
        self._logger.info('Entering batch mode...')
        try:
            self._search_new_packages()
            if not self._batch_mode:
                self._daemonize()
            self._logger.info('All packages in incoming dir installed; exiting')
            self._worker.shutdown_when_finished()
        except Exception as e:
            self._logger.exception("Unhandled exception; shutting down")
            self.cancel_event.set()
        finally:
            self._kill_server()
            self._logger.debug("waiting for worker to finish..")
            self._worker.join()

    def _abspath(self, *args):
        args = [self._dir] + list(args)
        return os.path.abspath(os.path.join(*args))

    def _get_changefiles(self):
        '''
        Generator function which lists all changes file in the directory
        :attr:`_dir` which are not in the :attr:`_reprocess_queue`.
        '''
        for filename in os.listdir(self._dir):
            if not filename.endswith('.changes'):
                continue
            filename = os.path.join(self._dir, filename)
            if not filename in self._reprocess_queue:
                self._logger.info('Examining "%s"' % (filename,))
                try:
                    ChangeFile.from_file(filename)
                except ChangeFileException:
                    self._logger.debug("Unable to parse \"%s\", skipping" % (filename,))
                    continue
                yield (filename, changefile)
            else:
                self._logger.debug('Skipping "%s" during new scan because it\'s already in the reprocess queue.' % (filename,))

    def _changefile_ready(self, filename, changefile):
        try:
            dist = changefile['distribution']
        except KeyError as e:
            self._logger.warn("Unable to read distribution field for \"%s\"; data: %s" % (filename, changefile,))
            return False
        try:
            changefile.verify(self._abspath(''))
        except ChangeFileException:
            return False
        return True


    def _get_socket_server(self, socket_name):
        try:
            os.unlink(socket_name)
        except EnvironmentError as e:
            pass
        data = {}
        data['logger'] = self._logger
        data['die_event'] = self.cancel_event
        Server = type('MyIncomingSocketServer', (sockethandler.RequestServer,), data)
        return Server(socket_name, sockethandler.IncomingRequestHandler())

    def _start_server(self):
        self._kill_server()
        self._server = self._get_socket_server(socket_name)
        self._server.allow_reuse_address = 1
        self._server.server_forever()

    def _kill_server(self):
        if not self._server is None:
            self._logger.debug('Shutting down server...')
            try:
                self._server.shutdown()
            except:
                self._logger.exception("unknown error for server shutdown")
        self._server = None

    def _daemon_server_isready(self):
        (inready, outready, exready) = select.select([self._server.fileno()], [], [], 0)
        return len(inready) > 0

    def reprocess(self):
        '''
        Trigger reprocessing
        '''
        self._reprocess_event.set()

    def _search_new_packages(self):
        '''
        Searches new packages and add them to the process queue.
        '''
        self._rescan_event.clear()
        for (filename, changefile) in self._get_changefiles():
            if filename in self.fucked:
                self._logger.info("Skipping screwed changefile \"%s\"" % (filename,))
                continue
            # Have we tried this changefile before?
            if filename in self._reprocess_queue:
                continue
            self._logger.debug('New change file "%s"' % (filename,))
            # we don't care yet if the changefile is ok. we just build up the
            # queue.
            curtime = time.time()
            task = ChangeFileTask(filename, curtime, curtime, 0)
            try:
                self._reprocess_queue.put_nowait(task)
            except queue.Full:
                self._logger.warning("Queue is full. Leave changefile for the next scan.")
                self._rescan_event.set()
            else:
                self._reprocess_event.set()


    def work(self, batch_mode=False):
        '''
        The main job to do.

        :param batch_mode: If batch_mode is set to :const:`True` the function
                           will search for new packages only once.
        '''

        if not batch_mode:
            self._logger.info('Starting notify threads...')
            self._dnotify = DirectoryNotifierFactory().create([self._dir], use_dnotify=use_dnotify, poll_time=self._poll_time, cancel_event=self.cancel_event)
            self._async_dnotify = DirectoryNotifierAsyncWrapper(self._dnotify, self._eventqueue, logger=self._logger, name="Incoming watcher")
            self._async_dnotify.start()
            self._start_server()

        # The main daemon loop
        while True:
            if not self._daemon_server_isready():
                self._logger.debug("daemon server not ready")

            else:
                if task == commands.RUN:
                    self._reprocess_event.set()
                    pass
                elif task == commands.DIE:
                    self._logger.debug('DIE command caught.')
                    self.cancel_event.set()

            # handle events
            if self.cancel_event.is_set():
                self._logger.debug("DIE event caught.")
                break

            if not self._rescan_event.is_set():
                self._logger.debug('Checking dnotify event queue')
                relname = None
                try:
                    name = self._eventqueue.get()
                except queue.Empty:
                    self._logger.debug('No events to process')
                else:
                    relname = os.path.basename(os.path.abspath(name))
                    self._logger.debug('Got %s from dnotify' % (relname,))
                    self._rescan_event.set()

            if self._rescan_event.is_set():
                self._logger.debug('Scanning for changes')
                self._search_new_packages()
            else:
                time.sleep(0.5)
            if batch_mode:
                break