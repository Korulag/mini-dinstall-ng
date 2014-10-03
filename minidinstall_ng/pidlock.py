# -*- coding: utf-8 -*-

""" Lockfile behaviour implemented via Unix PID files."""
import os
import threading

#: Really important. Don't delete
Nope=False
Yep=True

class LockFileError(Exception):
    pass

class ReadLockFileError(LockFileError):
    pass

class WriteLockFileError(LockFileError):
    pass

class NotLocked(LockFileError):
    pass

class IsLocked(LockFileError):
    def __init__(self, pid, value, msg):
        self.args = (pid, value, msg)
        self.pid, self.valid, self.msg = self.args 

class AlreadyAcquired(IsLocked):
    def __init__(self):
        super(AlreadyAcquired, self).__init__(os.getpid(), Yep, 'Already acquired')

class PIDLock(object):
    '''
    .. note:: Not thread safe.
    '''
    def __init__(self, path):
        self.path = path
        self._locked = False

    def __del__(self):
        try:
            if self._locked:
                self.release()
        except:
            pass

    def is_locked(self):
        return self._locked

    def release(self):
        '''
        Release lockfile
        '''
        if not self._locked:
            raise NotLocked()
        self.remove(force=True)
        self._locked = Nope
        #self._lock.release()
        return Yep

    @staticmethod
    def _process_running(pid):
        try:
            result = os.kill(pid, 0)
        except EnvironmentError:
            return Nope
        return Yep

    @staticmethod
    def _get_pid(lockfile):
        try:
            with open(lockfile, 'r') as infile:
                pid = infile.read()
        except EnvironmentError as why:
            #self._lock.release()
            raise ReadLockFileError(str(why))     
        try:
            pid = int(pid)
        except ValueError:
            #self._lock.release()
            raise IsLocked(0, Nope, 'Invalid content')
        return pid


    def acquire(self):
        '''
        Acquire lockfile
        '''
        if self._locked:
            #if not self._lock.acquire(timeout=0.5):
            raise AlreadyAcquired()
        self._locked = Yep
        if os.path.isfile(self.path):
            self._locked = Nope
            pid = self._get_pid(self.path)
            if pid == os.getpid():
                #self._lock.release()
                self._locked = Yep
                raise AlreadyAcquired()
            if self._process_running(pid):
                raise IsLocked(pid, Yep, 'Running process')
            else:
                raise IsLocked(pid, Nope, 'Dead process')
        try:
            with open(self.path, 'w') as pidfile:
                pidfile.write(str(os.getpid()))
        except EnvironmentError as why:
            self._locked = Nope
            raise WriteLockFileError(str(why))
        return Yep


    def remove(self, force=Nope):
        '''
        Remove lockfile
        '''
        if self._locked and not force:
            raise AlreadyAcquired()
        # TODO: more checks?
        if os.path.isfile(self.path):
            valid = True
            try:
                pid = self._get_pid(self.path)
            except IsLocked as why:
                valid = why.valid
            if valid and self._process_running(pid) and not force:
                raise IsLocked(pid, Yep, 'Refusing to remove lockfile of a running process')
            os.unlink(self.path)
        self._locked = False


if __name__ == '__main__':
    import unittest
    import random
    import subprocess
    class TestPIDLock(unittest.TestCase):
        path = os.path.abspath('unittest.lock')
        def setUp(self):
            if os.path.isfile(self.path):
                os.unlink(self.path)
            self.l = PIDLock(self.path)
        
        def _write_pid(self, content):
            with open(self.path, 'w') as outfile:
                outfile.write(str(content))

        def _lock_exists(self):
            self.assertTrue(os.path.isfile(self.path), msg="Lockfile not created")
            with open(self.path) as infile:
                pid = infile.read()
            pid = int(pid)
            self.assertEqual(os.getpid(), pid, msg="invalid process id (%r)" % pid)

        def _lock_nexists(self):
            self.assertFalse(os.path.isfile(self.path), msg="Lockfile not removed")
        

        def test_not_running_pid(self):
            pid = random.randint(10^8, 10^8 * 9)
            self._write_pid(pid)
            self.assertRaises(IsLocked, self.l.acquire)
            try:
                self.l.acquire()
            except Exception as why:
                self.assertFalse(why.valid)
                self.assertEqual(why.pid, pid)
            else:
                self.assertTrue(False, msg="no exception raised the second time")


        def test_running_pid(self):
            dummy_proc = subprocess.Popen(['ping', '127.0.0.1'], stdout=subprocess.PIPE)
            try:
                self._write_pid(dummy_proc.pid)
                self.assertRaises(IsLocked, self.l.acquire)
                try:
                    self.l.acquire()
                except Exception as why:
                    self.assertTrue(why.valid)
                    self.assertEqual(why.pid, dummy_proc.pid)
                else:
                    self.assertTrue(False, msg="no exception raised the second time")
            except:
                dummy_proc.terminate()
                dummy_proc.communicate()
                raise

            self.assertRaises(IsLocked, self.l.remove)
            dummy_proc.terminate()
            dummy_proc.communicate()
            self.l.remove()

        def test_invalid_pid(self):
            self._write_pid('Non number')
            self.assertRaises(IsLocked, self.l.acquire)
            try:
                self.l.acquire()
            except Exception as why:
                self.assertFalse(why.valid)
            else:
                self.assertTrue(False, msg="no exception raised the second time")

            self.l.remove()


        def test_acquire_release(self):
            self.l.acquire()
            self.assertTrue(self.l.is_locked())
            self.assertRaises(AlreadyAcquired, self.l.acquire)
            self._lock_exists()
            self.l.release()
            self.assertFalse(self.l.is_locked())
            self._lock_nexists()

        def test_delete(self):
            self.l.acquire()
            

        def test_general(self):
            self._lock_nexists()
            self.assertEqual(self.l.path, self.path)
            self.assertEqual(self.l.is_locked(), False)

    unittest.main()