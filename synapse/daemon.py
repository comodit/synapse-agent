# Public Domain
#
# Copyright 2007, 2009 Sander Marechal <s.marechal@jejik.com>
# Copyright 2010, 2011 Jack Kaliko <efrim@azylum.org>
#
# http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/

import atexit
import os
import sys
import time
from signal import signal, SIGTERM


class Daemon(object):
    """
    A generic daemon class.

    Usage: subclass the Daemon class and override the run() method
    """
    version = "0.4"

    def __init__(self, pidfile,
            stdin='/dev/null',
            stdout='/dev/null',
            stderr='/dev/null'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile
        self.umask = 0

    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #1 failed: %d (%s)\n" %
                             (e.errno, e.strerror))
            sys.exit(1)

        # Decouple from parent environment
        os.chdir("/")
        os.setsid()
        self.umask = os.umask(0)

        # Do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #2 failed: %d (%s)\n" %
                             (e.errno, e.strerror))
            sys.exit(1)

        self.write_pid()
        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        atexit.register(self.shutdown)
        self.signal_management()

    def write_pid(self):
        # write pidfile
        if not self.pidfile:
            return
        pid = str(os.getpid())
        try:
            os.umask(self.umask)
            file(self.pidfile, 'w').write('%s\n' % pid)
        except Exception, wpid_err:
            sys.stderr.write(u'Error trying to write pid file: %s\n' %
                             wpid_err)
            sys.exit(1)
        os.umask(0)
        atexit.register(self.delpid)

    def signal_management(self):
        # Declare signal handlers
        signal(SIGTERM, self.exit_handler)

    def exit_handler(self, signum, frame):
        sys.exit(1)

    def delpid(self):
        try:
            os.unlink(self.pidfile)
        except OSError as err:
            message = 'Error trying to remove PID file: %s\n'
            sys.stderr.write(message % err)

    def start(self):
        """
        Start the daemon
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if pid:
            message = "pidfile %s already exist. Daemon already running?\n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run()

    def foreground(self):
        """
        Foreground/debug mode
        """
        self.write_pid()
        atexit.register(self.shutdown)
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if not pid:
            message = "pidfile %s does not exist. Is the Daemon running?\n"
            sys.stderr.write(message % self.pidfile)
            return  # not an error in a restart

        # Try killing the daemon process
        try:
            os.kill(pid, SIGTERM)
            time.sleep(0.1)
        except OSError, err:
            if err.errno == 3:
                if os.path.exists(self.pidfile):
                    message = "Daemon's not running? removing pid file %s.\n"
                    sys.stderr.write(message % self.pidfile)
                    os.remove(self.pidfile)
            else:
                sys.stderr.write(err.strerror)
                sys.exit(1)

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def shutdown(self):
        """
        You should override this method when you subclass Daemon. It will be
        called when the process is being stopped.
        Pay attention:
        Daemon() uses atexit to call Daemon().shutdown(), as a consequence
        shutdown and any other functions registered via this module are not
        called when the program is killed by an un-handled/unknown signal.
        This is the reason of Daemon().signal_management() existence.
        """

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be
        called after the process has been daemonized by start() or restart().
        """
