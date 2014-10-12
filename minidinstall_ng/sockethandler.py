import threading
from minidinstall_ng.commands import COMMANDS
try:
    import socketserver
except:
    import SocketServer as socketserver

class IncomingRequestHandler(socketserver.StreamRequestHandler,
                             socketserver.BaseRequestHandler):
    '''
    Handler for mini-dinstall soket commands. The command can be one of
    :data:`minidinstall_ng.commands.COMMANDS`.
    '''
    def __init__(self, *args, **kwargs):
        super(IncomingRequestHandler, self).__init__(*args, **kwargs)

    task_queue = None

    def handle(self):
        self.logger.debug('Got request from %s' % (self.client_address,))
        req = self.rfile.readline()
        if req[:-1] in COMMANDS:
            self.logger.info("Got %r command" % req)
            self.task_queue.put()
            self.wfile.write('200 Command scheduled')
        else:
            self.logger.info('Got unknown command %s' % (req,))
            self.wfile.write('500 Unknown request\n')

class RequestServer(socketserver.UnixStreamServer,
                    socketserver.ThreadingMixIn):
    '''
    Threaded unix stream handler which sets the :attr:`die_event` if an
    error occurs while handling a request.
    '''
    logger = None
    die_event = None
    daemon_threads = True
    def handle_error(self, request, client_address):
        self.logger.exception("Unhandled exception during request processing; shutting down")
        if not self.die_event is None:
            self.die_event.set()
