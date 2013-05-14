import sys
import tempfile

from subprocess import Popen, PIPE
from threading import Thread

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty


ON_POSIX = 'posix' in sys.builtin_module_names
__STDOUTBUF__ = ''


def exec_cmd(cmd):
    ret = {}
    stdout = tempfile.TemporaryFile(mode='w+t')
    stderr = tempfile.TemporaryFile(mode='w+t')
    try:
        proc = Popen(cmd, shell=True, universal_newlines=True,
                     stdout=stdout, stderr=stderr)
        ret_code = proc.wait()

        stdout.flush()
        stderr.flush()

        out = ''
        stdout.seek(0)
        for line in stdout:
            out += line.rstrip()

        err = ''
        stderr.seek(0)
        for line in stderr:
            err += line.rstrip()

        ret['cmd'] = cmd
        ret['stdout'] = out
        ret['stderr'] = err
        ret['returncode'] = ret_code
        ret['pid'] = proc.pid

    finally:
        stdout.close()
        stderr.close()

    return ret


def exec_threaded_cmd(cmd):
    proc = Popen(cmd,
                 shell=True,
                 bufsize=64,
                 close_fds=ON_POSIX,
                 stdout=PIPE,
                 stderr=PIPE)
    bufqueue = Queue()
    t = Thread(target=_enqueue_output, args=(proc.stdout, bufqueue))
    t.daemon = True
    t.start()

    try:
        global __STDOUTBUF__
        line = bufqueue.get(timeout=.1)
    except Empty:
        pass
    else:
        __STDOUTBUF__ += line


def _enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()
