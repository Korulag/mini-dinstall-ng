import socketserver

class IncomingRequestHandler(SocketServer.StreamRequestHandler, SocketServer.BaseRequestHandler):
    
    # the following attributes will be defined by subclassing.    
    logger = None
    reprocess_lock = None
    die_event = None
    reprocess_finished = None
    reprocess_needed = None
    def handle(self):
        self.logger.debug('Got request from %s' % (self.client_address,))
        req = self.rfile.readline()
        if req == 'RUN\n':
            logger.debug('Doing RUN command')
            reprocess_lock.acquire()
            reprocess_needed.set()
            logger.debug('Waiting on reprocessing')
            # wait until reprocess completed
            reprocess_finished.wait()
            reprocess_finished.clear()
            reprocess_lock.release()
            self.wfile.write('200 Reprocessing complete\n')
        elif req == 'DIE\n':
            self.logger.debug('Doing DIE command')
            self.wfile.write('200 Beginning shutdown\n')
            die_event.set()
        else:
            self.logger.debug('Got unknown command %s' % (req,))
            self.wfile.write('500 Unknown request\n')


class RequestServer(SocketServer.ThreadingUnixStreamServer):
    logger = None
    die_event = None
    def handle_error(self, request, client_address):
        self._logger.exception("Unhandled exception during request processing; shutting down")
        die_event.set()