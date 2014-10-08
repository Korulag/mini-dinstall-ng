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


class CheckedIndexedQueue(KeyIndexedQueue):
    '''
    A Queue where you can supply a check function to the :meth:`get`.
    This is useful if you only want special items.
    '''
    def __init__(self, **kwargs):
        super(TimedIndexedQueue, self).__init__(**kwargs)
        self._try_to_get_lock = threading.RLock()

    def get(self, *args, **kwargs):
        '''
        If the parameter *check* is set this function returns the next
        item in the queue which is successfully checked against this function.
        Unmachting items are appended at the back of the queue.

        :param check: Function which can be called to check the queue item
                      before returning it. This function has to return
                      :const:`True` is the item matches the requirements and
                      :const:`False` if not.
        :raises queue.Empty:
        '''
        check = None
        if 'check' in kwargs:
            check = kwargs.pop('check')
        first_element = None
        with self._try_to_get_lock:
            if check is None:
                return super(TimedIndexedQueue, self).get(*args, **kwargs)
            while True:
                # queue.Empty may be raised the first time
                res = super(TimedIndexedQueue, self).get_nowait()
                if first_element is None:
                    first_element = res
                elif first_element == res:
                    # iterated once over all elements
                    raise queue.Empty()
                if res[self._time_index] >= only_after:
                    # re-add the object (should never raise an exception
                    # because we have acquired the lock!)
                    super(TimedIndexedQueue, self).put(timeout=1)
                    continue
                return res

    def put(self, *args, **kwargs):
        '''
        This method acquires the lock so we can't add items while get 
        processing its input. This is needed to avoid :exc:`queue.Full`
        exceptions in the :meth:`get`.
        '''
        with self._try_to_get_lock:
            super(TimedIndexedQueue, self).put(*args, **kwargs)


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
        #: fucked packages. yup. fucked. 
        self.fucked = []
        # ensure we always have some reprocess queue
        self._reprocess_queue = CheckedIndexedQueue()
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
        try:
            self._search_new_packages()
            if not self._batch_mode:
                self._daemonize(initial_reprocess_queue)
            self._done_event.set()
            self._logger.info('All packages in incoming dir installed; exiting')
        except Exception as e:
            self._logger.exception("Unhandled exception; shutting down")
            self._die_event.set()
            self._done_event.set()
            return 0

    def _abspath(self, *args):
        args = [self._dir] + list(args)
        return os.path.abspath(os.path.join(*args))

    def _get_changefiles(self):
        '''
        Generator function which lists all changes file in the directory
        :attr:`_dir` which are not in the :attr:`_reprocess_queue`.
        '''
        for changefilename in os.listdir(self._dir):
            if not changefilename.endswith('.changes'):
                continue
            changefilename = os.path.join(self._dir, changefilename)
            if not changefilename in self._reprocess_queue:
                self._logger.info('Examining "%s"' % (changefilename,))
                try:
                    ChangeFile.from_file(changefilename)
                except ChangeFileException:
                    self._logger.debug("Unable to parse \"%s\", skipping" % (changefilename,))
                    continue
                yield (changefilename, changefile)
            else:
                self._logger.debug('Skipping "%s" during new scan because it\'s already in the reprocess queue.' % (changefilename,))

    def _changefile_ready(self, changefilename, changefile):
        try:
            dist = changefile['distribution']
        except KeyError as e:
            self._logger.warn("Unable to read distribution field for \"%s\"; data: %s" % (changefilename, changefile,))
            return False
        try:
            changefile.verify(self._abspath(''))
        except ChangeFileException:
            return False
        return True

    def _install_changefile(self, changefilename, changefile, doing_reprocess=False):
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
        return Server(socket_name, sockethandler.IncomingRequestHandler())

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

    def _search_new_packages(self):
        '''
        Searches new packages and add them to the process queue.
        '''
        for (changefilename, changefile) in self._get_changefiles():
            if changefilename in self.fucked:
                self._logger.info("Skipping screwed changefile \"%s\"" % (changefilename,))
                continue
            # Have we tried this changefile before?
            if changefilename in self._reprocess_queue:
                continue
            self._logger.debug('New change file "%s"' % (changefilename,))
            # we don't care yet if the changefile is ok. we just build up the
            # queue.
            curtime = time.time()
            task = ChangeFileTask(changefilename, curtime, curtime, 0)
            try:
                self._reprocess_queue.put_nowait(task)
            except queue.Full:
                self._logger.warning("Queue is full. Leave changefile for the next scan.")
            
    def _reprocess_packages(self):
        '''
        Process packages in the :attr:`_reprocess_queue`
        '''
        def check_fnc(x):
            return (time.time() - x.start_time > self._max_retry_time)
        
        while True:
            try:
                task = self._reprocess_queue.get(check=check_fnc)
            except queue.Empty:
                break

            # We've tried too many times; reject it.
            err_msg = 'Couldn\'t install "%s" in %d seconds' 
            err_msg = err_msg % (task.filename, self._max_retry_time)
            exception = DinstallException(err_msg)
            self._reject_changefile(task.filename, changefile, exception)
 
        check_fnc = lambda x: x.next_time < time.time()
        while True:
            try:
                task = self._reprocess_queue.get(check=check_fnc)
            except queue.Empty:
                # nothing to do
                break

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
                # process the next change file
                continue

            if self._changefile_ready(task.filename, changefile):
                # Let's do it!
                self._logger.debug('Preparing to install "%s"' % (task.filename,))
                try:
                    self._install_changefile(task.filename, changefile, doing_reprocess)
                except:
                    self._logger.exception("Unable to install \"%s\"; adding to screwed list" % (task.filename,))
                    self.fucked.append(task.filename)
            else:
                delay = task.delay * 2
                if delay > 60 * 60:
                    delay = 60 * 60
                self._logger.info('Upload "%s" isn\'t complete; marking for retry in %d seconds' % (task.filename, delay))
                # set next time and delay
                re_add = ChangeFileTask(task.filename, task.start_time, curtime + delay, delay)
                try:
                    self._reprocess_queue.put(re_add, timeout=2)
                except queue.Full:
                    self._logger.error("Queue got full while processing packages. Don't know what to do with reprocess task!")


    def _daemonize(self):
        '''
        Enter the .. hell?
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
        doing_reprocess = False

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
            self._reprocess_packages()
            # done reprocessing; now scan for changed dirs.

            self._logger.debug('Checking dnotify event queue')
            relname = None
            try:
                name = self._eventqueue.get()
            except queue.Empty:
                self._logger.debug('No events to process')
                continue
            else:
                relname = os.path.basename(os.path.abspath(name))
                self._logger.debug('Got %s from dnotify' % (relname,))

            self._search_new_packages()
            self._logger.info('Reprocessing complete')
            doing_reprocess = True
    

    def wait(self):
        self._done_event.wait()
