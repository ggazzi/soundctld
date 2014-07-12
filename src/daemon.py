"""Generic linux daemon base class for python 3.x."""

import sys, os, time, atexit, signal, argparse


def main(daemon):
    """Usual functionality of a daemon's command.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--pid-file', dest='pidfile')

    comms = parser.add_subparsers(dest='command', title='commands')

    start = comms.add_parser("start",
                             help="Start the service, if not already running, with the given options.")
    stop = comms.add_parser("stop",
                            help="Stop the service, if it is running.")
    restart = comms.add_parser("restart",
                               help="Restart the service, possibly changing the options.")
    test = comms.add_parser("test",
                            help="Run the service without daemonizing.")

    daemon.add_command_line_arguments_to(
        parser.add_argument_group('daemon options'))

    args = parser.parse_args()

    if args.pidfile:
        daemon.pidfile = args.pidfile

    if 'start' == args.command:
        daemon.start(args)
    elif 'stop' == args.command:
        daemon.stop()
    elif 'restart' == args.command:
        daemon.restart(args)
    elif 'test' == args.command:
        daemon.run()
    else:
        print(parser.format_help())


class Daemon:
    """A generic daemon class.

    Usage: subclass the daemon class and override the run() method."""

    def __init__(self, pidfile):
        self.pidfile = pidfile

    def daemonize(self):
        """Deamonize class. UNIX double fork mechanism."""

        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError as err:
            sys.stderr.write('fork #1 failed: {0}\n'.format(err))
            sys.exit(1)

        # decouple from parent environment
        os.chdir('/')
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:

                # exit from second parent
                sys.exit(0)
        except OSError as err:
            sys.stderr.write('fork #2 failed: {0}\n'.format(err))
            sys.exit(1)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(os.devnull, 'r')
        so = open(os.devnull, 'a+')
        se = open(os.devnull, 'a+')

        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # write pidfile
        atexit.register(self.delpid)

        pid = str(os.getpid())
        with open(self.pidfile,'w+') as f:
            f.write(pid + '\n')

    def delpid(self):
        os.remove(self.pidfile)

    def start(self, args):
        """Start the daemon."""

        # Check for a pidfile to see if the daemon already runs
        try:
            with open(self.pidfile,'r') as pf:

                pid = int(pf.read().strip())
        except IOError:
            pid = None

        if pid:
            message = "pidfile {0} already exist. " + \
                    "Daemon already running?\n"
            sys.stderr.write(message.format(self.pidfile))
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run(args)

    def stop(self):
        """Stop the daemon."""

        # Get the pid from the pidfile
        try:
            with open(self.pidfile,'r') as pf:
                pid = int(pf.read().strip())
        except IOError:
            pid = None

        if not pid:
            message = "pidfile {0} does not exist. " + \
                    "Daemon not running?\n"
            sys.stderr.write(message.format(self.pidfile))
            return # not an error in a restart

        # Try killing the daemon process
        try:
            while 1:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.1)
        except OSError as err:
            e = str(err.args)
            if e.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print (str(err.args))
                sys.exit(1)

    def restart(self, args):
        """Restart the daemon."""
        self.stop()
        self.start(args)

    def run(self):
        """You should override this method when you subclass Daemon.

        It will be called after the process has been daemonized by
        start() or restart().
        """

    def add_command_line_arguments_to(self, group):
        """You should override this method when you subclass Daemon.

        It will be called before any other method of this class. Any
        command-line arguments specific to this daemon should be added
        to the given parser, which will be an argparse argument-group.
        """
