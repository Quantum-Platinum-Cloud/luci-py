#!/usr/bin/env vpython3
# Copyright 2013 The LUCI Authors. All rights reserved.
# Use of this source code is governed under the Apache License, Version 2.0
# that can be found in the LICENSE file.

from __future__ import print_function

import ctypes
import errno
import itertools
import os
import platform
import signal
import sys
import tempfile
import textwrap
import time
import unittest

from nose2.tools import params

# Mutates sys.path.
import test_env

from utils import subprocess42

# Disable pre-set unbuffered output to not interfere with the testing being done
# here. Otherwise everything would test with unbuffered; which is fine but
# that's not what we specifically want to test here.
ENV = os.environ.copy()
ENV.pop('PYTHONUNBUFFERED', None)

SCRIPT_OUT = ('import signal, sys, time;\n'
              'l = [];\n'
              'def handler(signum, _):\n'
              '  l.append(signum);\n'
              '  sys.stdout.write(\'got signal %%d\\n\' %% signum);\n'
              '  sys.stdout.flush();\n'
              'signal.signal(%s, handler);\n'
              'sys.stdout.write(\'hi\\n\');\n'
              'sys.stdout.flush();\n'
              'while not l:\n'
              '  try:\n'
              '    time.sleep(0.01);\n'
              '  except IOError:\n'
              '    sys.stdout.write(\'ioerror\\n\');\n'
              '    sys.stdout.flush();\n'
              'sys.stdout.write(\'bye\\n\');\n'
              'sys.stdout.flush();\n') % ('signal.SIGBREAK' if sys.platform ==
                                          'win32' else 'signal.SIGTERM')

SCRIPT_ERR = ('import signal, sys, time;\n'
              'l = [];\n'
              'def handler(signum, _):\n'
              '  l.append(signum);\n'
              '  sys.stderr.write(\'got signal %%d\\n\' %% signum);\n'
              '  sys.stderr.flush();\n'
              'signal.signal(%s, handler);\n'
              'sys.stderr.write(\'hi\\n\');\n'
              'sys.stderr.flush();\n'
              'while not l:\n'
              '  try:\n'
              '    time.sleep(0.01);\n'
              '  except IOError:\n'
              '    sys.stderr.write(\'ioerror\\n\');\n'
              '    sys.stderr.flush();\n'
              'sys.stderr.write(\'bye\\n\');\n'
              'sys.stderr.flush();\n') % ('signal.SIGBREAK' if sys.platform ==
                                          'win32' else 'signal.SIGTERM')

OUTPUT_SCRIPT = br"""
import os
import re
import sys
import time

def main():
  try:
    for command in sys.argv[1:]:
      if re.match(r'^[0-9\.]+$', command):
        time.sleep(float(command))
        continue

      if command.startswith('out_'):
        pipe, other = sys.stdout, sys.stderr
      elif command.startswith('err_'):
        pipe, other = sys.stderr, sys.stdout
      else:
        return 1

      command = command[4:]
      if command == 'print':
        pipe.write('printing')
      elif command == 'sleeping':
        pipe.write('Sleeping.\n')
      elif command == 'slept':
        pipe.write('Slept.\n')
      elif command == 'lf':
        pipe.write('\n')
      elif command == 'flush':
        pipe.flush()
      elif command == 'leak':
        pid = os.fork()
        if pid > 0:
          return 0

        other.write("leaked child is %s %s\n" % (os.getpid(), os.getpgid(0)))
        other.write("sleeping\n")
        time.sleep(30)
        other.write("woke up\n")
        return 1
      else:
        return 1
    return 0
  except OSError:
    return 0


if __name__ == '__main__':
  sys.exit(main())
"""

_NSJAIL_CONFIG = br"""
clone_newnet: false
clone_newuser: false
clone_newns: false
clone_newpid: false
clone_newipc: false
clone_newuts: false
clone_newcgroup: false
"""


def to_native_eol(string):
  if string is None:
    return string
  if sys.platform == 'win32':
    return string.replace(b'\n', b'\r\n')
  return string


def get_output_sleep_proc(flush, unbuffered, sleep_duration):
  """Returns process with universal_newlines=True that prints to stdout before
  after a sleep.

  It also optionally sys.stdout.flush() before the sleep and optionally enable
  unbuffered output in python.
  """
  command = [
      'import sys,time',
      'print(\'A\')',
  ]
  if flush:
    # Sadly, this doesn't work otherwise in some combination.
    command.append('sys.stdout.flush()')
  command.extend((
      'time.sleep(%s)' % sleep_duration,
      'print(\'B\')',
  ))
  cmd = [sys.executable, '-c', ';'.join(command)]
  if unbuffered:
    cmd.append('-u')
  return subprocess42.Popen(
      cmd, env=ENV, stdout=subprocess42.PIPE, universal_newlines=True)


def get_output_sleep_proc_err(sleep_duration):
  """Returns process with universal_newlines=True that prints to stderr before
  and after a sleep.
  """
  command = [
      'import sys,time',
      'sys.stderr.write(\'A\\n\')',
  ]
  command.extend((
      'time.sleep(%s)' % sleep_duration,
      'sys.stderr.write(\'B\\n\')',
  ))
  cmd = [sys.executable, '-c', ';'.join(command)]
  return subprocess42.Popen(
      cmd, env=ENV, stderr=subprocess42.PIPE, universal_newlines=True)


class Subprocess42Test(unittest.TestCase):

  def setUp(self):
    self._output_script = None
    super(Subprocess42Test, self).setUp()

  def tearDown(self):
    try:
      if self._output_script:
        os.remove(self._output_script)
    finally:
      super(Subprocess42Test, self).tearDown()

  @property
  def output_script(self):
    if not self._output_script:
      handle, self._output_script = tempfile.mkstemp(
          prefix='subprocess42', suffix='.py')
      os.write(handle, OUTPUT_SCRIPT)
      os.close(handle)
    return self._output_script

  def test_communicate_timeout(self):
    timedout = 1 if sys.platform == 'win32' else -9
    # Format is:
    # ( (cmd, stderr_pipe, timeout), (stdout, stderr, returncode) ), ...
    # See OUTPUT script for the meaning of the commands.
    test_data = [
        # 0 means no timeout, like None.
        (
            (['out_sleeping', '0.001', 'out_slept', 'err_print'], None, 0),
            (b'Sleeping.\nSlept.\n', None, 0),
        ),
        (
            (['err_print'], subprocess42.STDOUT, 0),
            (b'printing', None, 0),
        ),
        (
            (['err_print'], subprocess42.PIPE, 0),
            (b'', b'printing', 0),
        ),

        # On a loaded system, this can be tight.
        (
            (['out_sleeping', 'out_flush', '60', 'out_slept'], None, 1),
            (b'Sleeping.\n', None, timedout),
        ),
        (
            (
                # Note that err_flush is necessary on Windows but not on the
                # other OSes. This means the likelihood of missing stderr output
                # from a killed child process on Windows is much higher than on
                # other OSes.
                [
                    'out_sleeping',
                    'out_flush',
                    'err_print',
                    'err_flush',
                    '60',
                    'out_slept',
                ],
                subprocess42.PIPE,
                1),
            (b'Sleeping.\n', b'printing', timedout),
        ),
        (
            (['out_sleeping', '0.001', 'out_slept'], None, 60),
            (b'Sleeping.\nSlept.\n', None, 0),
        ),
        (
            ([], None, 60),
            (b'', None, 0),
        ),
        (
            ([], subprocess42.PIPE, 60),
            (b'', b'', 0),
        ),
    ]
    for i, ((args, errpipe, timeout), expected) in enumerate(test_data):
      proc = subprocess42.Popen(
          [sys.executable, self.output_script] + args,
          env=ENV,
          stdout=subprocess42.PIPE,
          stderr=errpipe)
      try:
        stdout, stderr = proc.communicate(timeout=timeout)
        code = proc.returncode
      except subprocess42.TimeoutExpired as e:
        stdout = e.output
        stderr = e.stderr
        self.assertTrue(proc.kill())
        code = proc.wait()
      finally:
        duration = proc.duration()
      expected_duration = 0.0001 if not timeout or timeout == 60 else timeout
      self.assertTrue(duration >= expected_duration, (i, expected_duration))
      self.assertEqual((i, stdout, stderr, code), (i, to_native_eol(
          expected[0]), to_native_eol(expected[1]), expected[2]))

      # Try again with universal_newlines=True.
      proc = subprocess42.Popen(
          [sys.executable, self.output_script] + args,
          env=ENV,
          stdout=subprocess42.PIPE,
          stderr=errpipe,
          universal_newlines=True)
      try:
        stdout, stderr = proc.communicate(timeout=timeout)
        code = proc.returncode
      except subprocess42.TimeoutExpired as e:
        # With communicate() in the native subprocess.py, output/stderr becomes
        # bytes even if universal_newlines = True in Python3.
        # They are str on Windows because the communicate() in subprocess42.py
        # is used.
        stdout = e.output
        stderr = e.stderr
        if sys.platform != 'win32':
          stdout = stdout.decode() if stdout else None
          stderr = stderr.decode() if stderr else None
        self.assertTrue(proc.kill())
        code = proc.wait()
      finally:
        duration = proc.duration()
      self.assertTrue(duration >= expected_duration, (i, expected_duration))
      self.assertEqual((i, None if stdout is None else stdout.encode(),
                        None if stderr is None else stderr.encode(), code),
                       (i,) + expected)

  def test_communicate_input(self):
    cmd = [
        sys.executable,
        '-u',
        '-c',
        'import sys; sys.stdout.write(sys.stdin.read(5))',
    ]
    proc = subprocess42.Popen(
        cmd, stdin=subprocess42.PIPE, stdout=subprocess42.PIPE)
    out, err = proc.communicate(input=b'12345')
    self.assertEqual(b'12345', out)
    self.assertEqual(None, err)

  def test_communicate_input_timeout(self):
    cmd = [sys.executable, '-u', '-c', 'import time; time.sleep(60)']
    proc = subprocess42.Popen(cmd, stdin=subprocess42.PIPE)
    try:
      proc.communicate(input=b'12345', timeout=0.5)
      self.fail()
    except subprocess42.TimeoutExpired as e:
      self.assertEqual(None, e.output)
      self.assertEqual(None, e.stderr)
      self.assertTrue(proc.kill())
      proc.wait()
      self.assertLessEqual(0.5, proc.duration())

  def test_communicate_input_stdout_timeout(self):
    cmd = [
        sys.executable,
        '-u',
        '-c',
        """
import sys, time
sys.stdout.write(sys.stdin.read(5))
sys.stdout.flush()
time.sleep(60)
        """,
    ]
    proc = subprocess42.Popen(
        cmd, stdin=subprocess42.PIPE, stdout=subprocess42.PIPE)
    try:
      proc.communicate(input=b'12345', timeout=2)
      self.fail()
    except subprocess42.TimeoutExpired as e:
      self.assertEqual(b'12345', e.output)
      self.assertEqual(None, e.stderr)
      self.assertTrue(proc.kill())
      proc.wait()
      self.assertLessEqual(0.5, proc.duration())

  def test_communicate_timeout_no_pipe(self):
    # In this case, it's effectively a wait() call.
    cmd = [sys.executable, '-u', '-c', 'import time; time.sleep(60)']
    proc = subprocess42.Popen(cmd)
    try:
      proc.communicate(timeout=0.5)
      self.fail()
    except subprocess42.TimeoutExpired as e:
      self.assertEqual(None, e.output)
      self.assertEqual(None, e.stderr)
      self.assertTrue(proc.kill())
      proc.wait()
      self.assertLessEqual(0.5, proc.duration())

  def _test_lower_priority(self, lower_priority):
    if sys.platform == 'win32':
      cmd = [
          sys.executable, '-u', '-c',
          'import ctypes,sys; v=ctypes.windll.kernel32.GetPriorityClass(-1);'
          'sys.stdout.write(hex(v))'
      ]
    else:
      cmd = [
          sys.executable,
          '-u',
          '-c',
          'import os,sys;sys.stdout.write(str(os.nice(0)))',
      ]
    proc = subprocess42.Popen(
        cmd, stdout=subprocess42.PIPE, lower_priority=lower_priority)
    out, err = proc.communicate()
    self.assertEqual(None, err)
    return out

  @unittest.skipIf(sys.platform == 'win32', 'crbug.com/1148174')
  def test_lower_priority(self):
    out = self._test_lower_priority(True)
    if sys.platform == 'win32':
      # See
      # https://docs.microsoft.com/en-us/windows/desktop/api/processthreadsapi/nf-processthreadsapi-getpriorityclass
      BELOW_NORMAL_PRIORITY_CLASS = 0x4000
      self.assertEqual(hex(BELOW_NORMAL_PRIORITY_CLASS), out)
    else:
      self.assertEqual(str(os.nice(0) + 1).encode(), out)

  def test_lower_priority_False(self):
    out = self._test_lower_priority(False)
    if sys.platform == 'win32':
      # Should be NORMAL_PRIORITY_CLASS.
      p = ctypes.windll.kernel32.GetPriorityClass(-1)
      self.assertEqual(hex(p).encode(), out)
    else:
      self.assertEqual(str(os.nice(0)).encode(), out)

  @staticmethod
  def _cmd_print_good():
    # Used in test_containment_auto and test_containment_auto_limit_process.
    return [
        sys.executable,
        '-u',
        '-c',
        'import subprocess,sys; '
        'subprocess.call([sys.executable, "-c", "print(\\"good\\")"])',
    ]

  def test_containment_none(self):
    # Minimal test case. Starts two processes.
    cmd = self._cmd_print_good()
    containment = subprocess42.Containment(
        containment_type=subprocess42.Containment.NONE)
    self.assertEqual(0, subprocess42.check_call(cmd, containment=containment))

  def test_containment_auto(self):
    # Minimal test case. Starts two processes.
    cmd = self._cmd_print_good()
    containment = subprocess42.Containment(
        containment_type=subprocess42.Containment.AUTO,
        limit_processes=2,
        limit_total_committed_memory=1024 * 1024 * 1024)
    self.assertEqual(0, subprocess42.check_call(cmd, containment=containment))

  @unittest.skipUnless(sys.platform == 'linux',
                       'nsjail is only supported on linux')
  def test_containment_nsjail(self):
    # Tests that nsjail containment runs the given command in an nsjail.
    handle, cfg_path = tempfile.mkstemp(prefix='test_nsjail', suffix='.cfg')
    os.write(handle, _NSJAIL_CONFIG)
    os.close(handle)
    nsjail_bin_path = os.path.join(
        os.path.dirname(test_env.CLIENT_DIR), 'nsjail', 'nsjail')
    cmd = self._cmd_print_good()

    with tempfile.NamedTemporaryFile(delete=True) as log_file:
      containment = subprocess42.Containment(
          containment_type=subprocess42.Containment.NSJAIL,
          nsjail_bin_path=nsjail_bin_path,
          nsjail_config_file=cfg_path,
          nsjail_log_path=log_file.name)
      p = subprocess42.Popen(
          cmd,
          stdout=subprocess42.PIPE,
          stderr=subprocess42.PIPE,
          containment=containment)
      out, err = p.communicate()
      self.assertIn(b'NSJAIL', log_file.read())
      self.assertEqual(0, p.returncode)
      self.assertEqual(b'good\n', out)
      self.assertEqual(b'', err)
    os.remove(cfg_path)

  def test_containment_auto_limit_process(self):
    # Process creates a children process. It should fail, throwing not enough
    # quota.
    cmd = self._cmd_print_good()
    containment = subprocess42.Containment(
        containment_type=subprocess42.Containment.JOB_OBJECT, limit_processes=1)
    start = lambda: subprocess42.Popen(
        cmd,
        stdout=subprocess42.PIPE,
        stderr=subprocess42.PIPE,
        containment=containment)

    if sys.platform == 'win32':
      p = start()
      out, err = p.communicate()
      self.assertEqual(1, p.returncode)
      self.assertEqual(b'', out)
      self.assertIn(b'WinError', err)
      # Value for ERROR_NOT_ENOUGH_QUOTA. See
      # https://docs.microsoft.com/windows/desktop/debug/system-error-codes--1700-3999-
      self.assertIn(b'1816', err)
    else:
      # JOB_OBJECT is not usable on non-Windows.
      with self.assertRaises(NotImplementedError):
        start()

  def test_containment_auto_kill(self):
    # Test process killing.
    cmd = [
        sys.executable,
        '-u',
        '-c',
        'import sys,time; print("hi");time.sleep(60)',
    ]
    containment = subprocess42.Containment(
        containment_type=subprocess42.Containment.AUTO,
        limit_processes=1,
        limit_total_committed_memory=1024 * 1024 * 1024)
    p = subprocess42.Popen(
        cmd, stdout=subprocess42.PIPE, containment=containment)
    itr = p.yield_any_line()
    self.assertEqual(('stdout', b'hi'), next(itr))
    p.kill()
    p.wait()
    if sys.platform != 'win32':
      # signal.SIGKILL is not defined on Windows. Validate our assumption here.
      self.assertEqual(9, signal.SIGKILL)
    if sys.platform == 'win32':
      # p.returncode is unsigned in python3 on windows
      self.assertEqual(4294967287, p.returncode)
    else:
      self.assertEqual(-9, p.returncode)

  @unittest.skipIf(sys.platform == 'win32', 'pgid test')
  def test_kill_background(self):
    # Test process group killing.

    # Leaking a pipe through to the grandchild process is the only way to be
    # sure that we have a way to detect that this grandchild process is still
    # running or not. When all handles to the `w` end of the pipe have been
    # dropped, the `r` end will unblock.
    r, w = os.pipe()

    # Use fcntl instead of os.set_blocking because of python2
    import fcntl
    fcntl.fcntl(r, fcntl.F_SETFL, fcntl.fcntl(r, fcntl.F_GETFL) | os.O_NONBLOCK)

    p = subprocess42.Popen(
        [sys.executable, self.output_script, 'out_leak'],
        stdout=w, detached=True)
    os.close(w)  # close so we don't think that a child is hanging onto it.

    self.assertEqual(p.wait(), 0)  # our immediate child has exited!

    with self.assertRaises(OSError):
      # oops, something still has a handle to this pipe! it's the grandchild!
      os.read(r, 1)

    # kill the group! That'll show 'em (unless the child actually daemonized, in
    # which case we're hosed).
    p.kill()

    # sleepy-loop until the pipe is closed, should take O(ms) but we generously
    # wait up to 5s. The sub-child will wait 30s and should outlive this loop if
    # somehow it survived the kill.
    now = time.time()
    while True:
      try:
        self.assertEqual(os.read(r, 1), b'')  # i.e. EOF
        return
      except OSError as ex:
        if ex.errno != errno.EWOULDBLOCK:
          raise
        time.sleep(0.1)
        if time.time() - now > 5:
          raise Exception('pipe not unblocked after 5s, bailing')

  @staticmethod
  def _cmd_large_memory():
    # Used in test_large_memory and test_containment_auto_limit_memory.
    return [
        sys.executable,
        '-u',
        '-c',
        'list(range(50*1024*1024)); print("hi")',
    ]

  def test_large_memory(self):
    # Just assert the process works normally.
    cmd = self._cmd_large_memory()
    self.assertEqual(b'hi', subprocess42.check_output(cmd).strip())

  def test_containment_auto_limit_memory(self):
    # Process allocates a lot of memory. It should fail due to quota.
    cmd = self._cmd_large_memory()
    containment = subprocess42.Containment(
        containment_type=subprocess42.Containment.JOB_OBJECT,
        # 20 MiB.
        limit_total_committed_memory=20 * 1024 * 1024)
    start = lambda: subprocess42.Popen(
        cmd,
        stdout=subprocess42.PIPE,
        stderr=subprocess42.PIPE,
        containment=containment)

    if sys.platform == 'win32':
      p = start()
      out, err = p.communicate()
      self.assertEqual(1, p.returncode)
      self.assertEqual(b'', out)
      self.assertIn(b'MemoryError', err)
    else:
      # JOB_OBJECT is not usable on non-Windows.
      with self.assertRaises(NotImplementedError):
        start()

  def test_call(self):
    cmd = [sys.executable, '-u', '-c', 'import sys; sys.exit(0)']
    self.assertEqual(0, subprocess42.call(cmd))

    cmd = [sys.executable, '-u', '-c', 'import sys; sys.exit(1)']
    self.assertEqual(1, subprocess42.call(cmd))

  def test_check_call(self):
    cmd = [sys.executable, '-u', '-c', 'import sys; sys.exit(0)']
    self.assertEqual(0, subprocess42.check_call(cmd))

    cmd = [sys.executable, '-u', '-c', 'import sys; sys.exit(1)']
    try:
      self.assertEqual(1, subprocess42.check_call(cmd))
      self.fail()
    except subprocess42.CalledProcessError as e:
      self.assertEqual(None, e.output)

  def test_check_output(self):
    cmd = [sys.executable, '-u', '-c', 'print(\'.\')']
    self.assertEqual('.\n',
                     subprocess42.check_output(cmd, universal_newlines=True))

    cmd = [sys.executable, '-u', '-c', 'import sys; print(\'.\'); sys.exit(1)']
    try:
      subprocess42.check_output(cmd, universal_newlines=True)
      self.fail()
    except subprocess42.CalledProcessError as e:
      self.assertEqual('.\n', e.output)

  def test_recv_any(self):
    # Test all pipe direction and output scenarios.
    combinations = [
        {
            'cmd': ['out_print', 'err_print'],
            'stdout': None,
            'stderr': None,
            'expected': {},
            'universal_newlines': False,
        },
        {
            'cmd': ['out_print', 'err_print'],
            'stdout': None,
            'stderr': subprocess42.STDOUT,
            'universal_newlines': False,
            'expected': {},
        },
        {
            'cmd': ['out_print'],
            'stdout': subprocess42.PIPE,
            'stderr': subprocess42.PIPE,
            'universal_newlines': False,
            'expected': {
                'stdout': b'printing'
            },
        },
        {
            'cmd': ['out_print'],
            'stdout': subprocess42.PIPE,
            'stderr': None,
            'universal_newlines': False,
            'expected': {
                'stdout': b'printing'
            },
        },
        {
            'cmd': ['out_print'],
            'stdout': subprocess42.PIPE,
            'stderr': subprocess42.STDOUT,
            'universal_newlines': False,
            'expected': {
                'stdout': b'printing'
            },
        },
        {
            'cmd': ['err_print'],
            'stdout': subprocess42.PIPE,
            'stderr': subprocess42.PIPE,
            'universal_newlines': False,
            'expected': {
                'stderr': b'printing'
            },
        },
        {
            'cmd': ['err_print'],
            'stdout': None,
            'stderr': subprocess42.PIPE,
            'universal_newlines': False,
            'expected': {
                'stderr': b'printing'
            },
        },
        {
            'cmd': ['err_print'],
            'stdout': subprocess42.PIPE,
            'stderr': subprocess42.STDOUT,
            'universal_newlines': False,
            'expected': {
                'stdout': b'printing'
            },
        },
        {
            'cmd': ['out_print', 'err_print'],
            'stdout': subprocess42.PIPE,
            'stderr': subprocess42.PIPE,
            'universal_newlines': False,
            'expected': {
                'stderr': b'printing',
                'stdout': b'printing'
            },
        },
        {
            'cmd': ['out_print', 'err_print'],
            'stdout': subprocess42.PIPE,
            'stderr': subprocess42.STDOUT,
            'universal_newlines': False,
            'expected': {
                'stdout': b'printingprinting'
            },
        },
        {
            'cmd': ['out_print', 'err_print'],
            'stdout': subprocess42.PIPE,
            'stderr': subprocess42.PIPE,
            'universal_newlines': True,
            'expected': {
                'stderr': 'printing',
                'stdout': 'printing'
            },
        },
    ]
    for i, testcase in enumerate(combinations):
      default = '' if testcase['universal_newlines'] else b''
      cmd = [sys.executable, self.output_script] + testcase['cmd']
      p = subprocess42.Popen(
          cmd,
          env=ENV,
          stdout=testcase['stdout'],
          stderr=testcase['stderr'],
          universal_newlines=testcase['universal_newlines'])
      actual = {}
      while p.poll() is None:
        pipe, data = p.recv_any()
        if data:
          actual.setdefault(pipe, default)
          actual[pipe] += data

      # The process exited, read any remaining data in the pipes.
      while True:
        pipe, data = p.recv_any()
        if pipe is None:
          break
        actual.setdefault(pipe, default)
        actual[pipe] += data
      self.assertEqual(testcase['expected'], actual,
                       (i, testcase['cmd'], testcase['expected'], actual))
      self.assertEqual((None, None), p.recv_any())
      self.assertEqual(0, p.returncode)

  def test_recv_any_different_buffering(self):
    # Specifically test all buffering scenarios.
    for flush, unbuffered in itertools.product([True, False], [True, False]):
      actual = ''
      proc = get_output_sleep_proc(flush, unbuffered, 0.5)
      while True:
        p, data = proc.recv_any()
        if not p:
          break
        self.assertEqual('stdout', p)
        self.assertTrue(data, (p, data))
        actual += data

      self.assertEqual('A\nB\n', actual)
      # Contrary to yield_any() or recv_any(0), wait() needs to be used here.
      proc.wait()
      self.assertEqual(0, proc.returncode)

  def test_recv_any_timeout_0(self):
    self._test_recv_any_timeout(False, False)
    self._test_recv_any_timeout(False, True)
    self._test_recv_any_timeout(True, False)
    self._test_recv_any_timeout(True, True)

  def _test_recv_any_timeout(self, flush, unbuffered):
    # rec_any() is expected to timeout and return None with no data pending at
    # least once, due to the sleep of 'duration' and the use of timeout=0.
    for duration in (0.05, 0.1, 0.5, 2):
      got_none = False
      actual = ''
      try:
        proc = get_output_sleep_proc(flush, unbuffered, duration)
        try:
          while True:
            p, data = proc.recv_any(timeout=0)
            if p:
              self.assertEqual('stdout', p)
              self.assertTrue(data, (p, data))
              actual += data
              continue
            if proc.poll() is None:
              got_none = True
              continue
            break

          self.assertEqual('A\nB\n', actual)
          self.assertEqual(0, proc.returncode)
          self.assertEqual(True, got_none)
          break
        finally:
          proc.kill()
          proc.wait()
      except AssertionError:
        if duration != 2:
          print('Sleeping rocks. Trying slower.')
          continue
        raise

  def test_yield_any_no_timeout(self):
    for duration in (0.05, 0.1, 0.5, 2):
      try:
        proc = get_output_sleep_proc(True, True, duration)
        try:
          expected = [
              'A\n',
              'B\n',
          ]
          for p, data in proc.yield_any():
            self.assertEqual('stdout', p)
            self.assertEqual(expected.pop(0), data)
          self.assertEqual(0, proc.returncode)
          self.assertEqual([], expected)
          break
        finally:
          proc.kill()
          proc.wait()
      except AssertionError:
        if duration != 2:
          print('Sleeping rocks. Trying slower.')
          continue
        raise

  def test_yield_any_timeout_0(self):
    # rec_any() is expected to timeout and return None with no data pending at
    # least once, due to the sleep of 'duration' and the use of timeout=0.
    for duration in (0.05, 0.1, 0.5, 2):
      try:
        proc = get_output_sleep_proc(True, True, duration)
        try:
          expected = [
              'A\n',
              'B\n',
          ]
          got_none = False
          for p, data in proc.yield_any(timeout=0):
            if not p:
              got_none = True
              continue
            self.assertEqual('stdout', p)
            self.assertEqual(expected.pop(0), data)
          self.assertEqual(0, proc.returncode)
          self.assertEqual([], expected)
          self.assertEqual(True, got_none)
          break
        finally:
          proc.kill()
          proc.wait()
      except AssertionError:
        if duration != 2:
          print('Sleeping rocks. Trying slower.')
          continue
        raise

  def test_yield_any_timeout_0_called(self):
    # rec_any() is expected to timeout and return None with no data pending at
    # least once, due to the sleep of 'duration' and the use of timeout=0.
    for duration in (0.05, 0.1, 0.5, 2):
      got_none = False
      expected = ['A\n', 'B\n']
      called = []

      def timeout():
        # pylint: disable=cell-var-from-loop
        called.append(0)
        return 0

      try:
        proc = get_output_sleep_proc(True, True, duration)
        try:
          for p, data in proc.yield_any(timeout=timeout):
            if not p:
              got_none = True
              continue
            self.assertEqual('stdout', p)
            self.assertEqual(expected.pop(0), data)
          self.assertEqual(0, proc.returncode)
          self.assertEqual([], expected)
          self.assertEqual(True, got_none)
          self.assertTrue(called)
          break
        finally:
          proc.kill()
          proc.wait()
      except AssertionError:
        if duration != 2:
          print('Sleeping rocks. Trying slower.')
          continue
        raise

  def test_yield_any_returncode(self):
    proc = subprocess42.Popen(
        [sys.executable, '-c', 'import sys;sys.stdout.write("yo");sys.exit(1)'],
        stdout=subprocess42.PIPE)
    for p, d in proc.yield_any():
      self.assertEqual('stdout', p)
      self.assertEqual(b'yo', d)
    # There was a bug where the second call to wait() would overwrite
    # proc.returncode with 0 when timeout is not None.
    self.assertEqual(1, proc.wait())
    self.assertEqual(1, proc.wait(timeout=0))
    self.assertEqual(1, proc.poll())
    self.assertEqual(1, proc.returncode)
    # On Windows, the clock resolution is 15ms so Popen.duration() will likely
    # be 0.
    self.assertLessEqual(0, proc.duration())

  def _wait_for_hi(self, proc, err):
    actual = b''
    while True:
      if err:
        data = proc.recv_err(timeout=5)
      else:
        data = proc.recv_out(timeout=5)
      if not data:
        self.fail('%r' % actual)
      self.assertTrue(data)
      actual += data
      if actual in (b'hi\n', b'hi\r\n'):
        break

  def _proc(self, err, **kwargs):
    # Do not use the -u flag here, we want to test when it is buffered by
    # default. See reference above about PYTHONUNBUFFERED.
    # That's why the two scripts uses .flush(). Sadly, the flush() call is
    # needed on Windows even for sys.stderr (!)
    cmd = [sys.executable, '-c', SCRIPT_ERR if err else SCRIPT_OUT]
    # TODO(maruel): Make universal_newlines=True work and not hang.
    if err:
      kwargs['stderr'] = subprocess42.PIPE
    else:
      kwargs['stdout'] = subprocess42.PIPE
    return subprocess42.Popen(cmd, **kwargs)

  def test_detached(self):
    self._test_detached(False)
    self._test_detached(True)

  def _test_detached(self, err):
    is_win = (sys.platform == 'win32')
    key = 'stderr' if err else 'stdout'
    proc = self._proc(err, detached=True)
    try:
      self._wait_for_hi(proc, err)
      proc.terminate()
      if is_win:
        # What happens on Windows is that the process is immediately killed
        # after handling SIGBREAK.
        self.assertEqual(0, proc.wait())
        # Windows...
        self.assertIn(proc.recv_any(), (
            (key, b'got signal 21\r\nioerror\r\nbye\r\n'),
            (key, b'got signal 21\nioerror\nbye\n'),
            (key, b'got signal 21\r\nbye\r\n'),
            (key, b'got signal 21\nbye\n'),
        ))
      else:
        self.assertEqual(0, proc.wait())
        self.assertEqual((key, b'got signal 15\nbye\n'), proc.recv_any())
    finally:
      # In case the test fails.
      proc.kill()
      proc.wait()

  def test_attached(self):
    self._test_attached(False)
    self._test_attached(True)

  def _test_attached(self, err):
    is_win = (sys.platform == 'win32')
    key = 'stderr' if err else 'stdout'
    proc = self._proc(err, detached=False)
    try:
      self._wait_for_hi(proc, err)
      proc.terminate()
      if is_win:
        # If attached, it's hard killed.
        self.assertEqual(1, proc.wait())
        self.assertEqual((None, None), proc.recv_any())
      else:
        self.assertEqual(0, proc.wait())
        self.assertEqual((key, b'got signal 15\nbye\n'), proc.recv_any())
    finally:
      # In case the test fails.
      proc.kill()
      proc.wait()

  def test_split(self):
    data = [
        ('stdout', b'o1\no2\no3\n'),
        ('stderr', b'e1\ne2\ne3\n'),
        ('stdout', b'\n\n'),
        ('stdout', b'\n'),
        ('stdout', b'o4\no5'),
        ('stdout', b'_sameline\npart1 of one line '),
        ('stderr', b'err inserted between two parts of stdout\n'),
        ('stdout', b'part2 of one line\n'),
        ('stdout', b'incomplete last stdout'),
        ('stderr', b'incomplete last stderr'),
    ]
    expected = [
        ('stdout', b'o1'),
        ('stdout', b'o2'),
        ('stdout', b'o3'),
        ('stderr', b'e1'),
        ('stderr', b'e2'),
        ('stderr', b'e3'),
        ('stdout', b''),
        ('stdout', b''),
        ('stdout', b''),
        ('stdout', b'o4'),
        ('stdout', b'o5_sameline'),
        ('stderr', b'err inserted between two parts of stdout'),
        ('stdout', b'part1 of one line part2 of one line'),
        ('stderr', b'incomplete last stderr'),
        ('stdout', b'incomplete last stdout'),
    ]
    if sys.platform == 'win32':
      data = [(d[0], d[1].replace(b'\n', b'\r\n')) for d in data]

    # With universal_newlines=False
    self.assertEqual(list(subprocess42.split(data, False)), expected)

    # With universal_newlines=True
    data = [(d[0], d[1].decode()) for d in data]
    expected = [(e[0], e[1].decode()) for e in expected]
    self.assertEqual(list(subprocess42.split(data, True)), expected)

  @params((None,), (10,))
  def test_wait_can_be_interrupted(self, timeout):
    cmd = [
        sys.executable,
        '-c',
        textwrap.dedent(r"""
            import signal
            import sys
            import textwrap
            import time

            from utils import subprocess42

            class ExitError(Exception):
              pass
            def handler(signum, _frame):
              raise ExitError

            sleep_script = textwrap.dedent('''
                import time
                for _ in range(50):
                  time.sleep(0.2)
            ''')
            proc = subprocess42.Popen([sys.executable, '-c', sleep_script],
                                      detached=True)
            sig = signal.SIGBREAK if sys.platform =='win32' else signal.SIGTERM
            with subprocess42.set_signal_handler([sig], handler):
              try:
                sys.stdout.write('hi\n')
                sys.stdout.flush()
                proc.wait(%s)
              except ExitError:
                sys.stdout.write('wait is interrupted')
                sys.stdout.flush()
                proc.kill()
        """ % timeout),
    ]
    # Set cwd to CLIENT_DIR so that the script can import subprocess42.
    proc = subprocess42.Popen(cmd, stdout=subprocess42.PIPE,
                              cwd=test_env.CLIENT_DIR, detached=True)
    self._wait_for_hi(proc, False)
    time.sleep(0.5)
    proc.terminate()
    # proc is waiting for 'timeout' and SIGTERM/SIGBREAK is sent at 0.5s mark.
    # Expect proc to write to stdout and exit almost immediately (decided
    # by the poll interval of wait method). We wait for 8 second to give
    # some buffer here.
    start = time.time()
    got = proc.recv_out(timeout=8)
    want = b'wait is interrupted'
    self.assertEqual(
        got, want,
        "%s != %s after %s seconds" % (got, want, time.time() - start))


if __name__ == '__main__':
  test_env.main()
