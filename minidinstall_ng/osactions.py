import os
from collections import namedtuple

Action = namedtuple('OSAction', ['message', 'do_with_noact'])

class OsActions(object):

    def __init__(self, no_act, logger):
        self.logger = logger
        self.act = not no_act

    def unlink(self, f):
        self.logger.debug('removing file "%s"', f)
        if self.act:
            return os.unlink(f)

    remove = unlink

    def link(self, *args):
        self.logger.debug('linking "%s" to "%s"', args)
        if self.act:
            return os.link(*args)
    
    def chown(self, *args):
        self.logger.debug('changing overship of file "%s" to "%s:%s"' % args)
        if self.act:
            return os.chown(*args)

    def mkdir(self, dir):
        if not os.path.isdir(dir):
            self.logger.debug('Creating directory %r' % dir)
            if self.act:
                return os.mkdir(dir)