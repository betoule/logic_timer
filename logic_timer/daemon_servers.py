import os
import inspect 
import logging
import sys
from xmlrpc.server import SimpleXMLRPCServer, list_public_methods
from socketserver import ThreadingMixIn
import xmlrpc.client
import datetime
import threading

# daemonization related stuff
def redirect_stream(system_stream, target_stream):
    if target_stream is None:
        target_fd = os.open(os.devnull, os.O_RDWR)
    else:
        target_fd = target_stream.fileno()
    os.dup2(target_fd, system_stream.fileno())

def logged_call(f, lock):
    def inner(*args, **keys):
        logging.debug('Call to ' + str(f))
        try:
            with lock:
                return f(*args, **keys)
        except Exception as e:
            logging.exception('Catch exception')
            raise(e)
    return inner

def setup_logging(name, logfile=None, level=logging.INFO):
    if logfile is None:
        now = datetime.datetime.now()
        logdir = os.path.join(os.getenv("HOME"), "logs")
        logname = os.path.join(logdir, 
                               '%s-server-%s.log' % (name, now.date().isoformat()))
        logfile = logname
    logging.basicConfig(level=level, filename=logfile, format=f'%(levelname)s:%(asctime)s:{name}:%(message)s')

def daemonize(server):
    try:
        pid = os.fork()
        if pid > 0:
            # first parent exits
            sys.exit(0)
    except OSError as e:
        print('fork #1 failed: %d (%s)' % (e.errno, e.strerror), file=sys.stderr)
        sys.exit(1)
    os.setsid()
    
    try:
        pid = os.fork()
        if pid > 0:
            # exit from second parent 
            print(f"Starting server as daemon with PID {pid}")
            print(f"Kill with 'kill {pid}' or 'killall logic-timer'")
            sys.exit(0)
    except OSError as e:
        print("fork #2 failed %d (%s)" % (e.errno, e.strerror), file=sys.stderr)
        sys.exit(1)
        
    server.main(daemon=True)

class BasicServer(ThreadingMixIn, SimpleXMLRPCServer):
    def __init__(self, addr, name, instance):
        self.name=name
        SimpleXMLRPCServer.__init__(self, addr)
        self.instance = instance
        self.instance.exit = self.exit
        self.allow_none = True
        self.lock = threading.Lock()
        
    def _listMethods(self):
        methods = list_public_methods(self.instance)
        return methods

    def _methodHelp(self, method):
        f = getattr(self.instance, method)
        return inspect.getdoc(f)

    def serve_forever(self):
        self.quit = False
        while not self.quit:
            self.handle_request()
         
    def exit(self):
        self.quit = True
        return 'Server shutdown'

    def main(self, daemon=False):
        if daemon:
            redirect_stream(sys.stdin, None)
            redirect_stream(sys.stdout, None)
            redirect_stream(sys.stderr, None)

        self.register_function(self._listMethods, "__dir__")
        self.register_function(self._listMethods, "system.listMethods")
        self.register_function(self._listMethods, "trait_names")
        self.register_function(self._listMethods, "_getAttributeNames")
        self.register_function(self._methodHelp, "system.methodHelp")
        self.register_function(self.exit, "exit")

        logging.info(str(self.instance))
        for method in self._listMethods():
            f = getattr(self.instance, method)
            self.register_function(logged_call(f, self.lock), method)
            logging.info('registering method '+method)

        logging.info("server is up and listening at http://%s:%d." % self.socket.getsockname())
        self.serve_forever()
        self.server_close()
