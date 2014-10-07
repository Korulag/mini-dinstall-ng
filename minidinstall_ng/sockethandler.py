import threading
from minidinstall_ng.commands import COMMANDS
try:
    import socketserver
except:
    import SocketServer as socketserver

class IncomingRequestHandler(socketserver.StreamRequestHandler, socketserver.BaseRequestHandler):
    def __init__(self, *args, **kwargs):
        super(IncomingRequestHandler, self).__init__(*args, **kwargs)

    task_queue = None

    def handle(self):
        self.logger.debug('Got request from %s' % (self.client_address,))
        req = self.rfile.readline()
        if req[:-1] in COMMANDS:
            self.logger.info("Got %r command" % req)
            self.task_queue.put()
        else:
            self.logger.info('Got unknown command %s' % (req,))
            self.wfile.write('500 Unknown request\n')


class RequestServer(socketserver.UnixStreamServer, socketserver.ThreadingMixIn):
    logger = None
    die_event = None
    daemon_threads = True
    def handle_error(self, request, client_address):
        self.logger.exception("Unhandled exception during request processing; shutting down")
        self.die_event.set()