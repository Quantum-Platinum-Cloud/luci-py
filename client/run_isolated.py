#!/usr/bin/env python
# Copyright 2012 The LUCI Authors. All rights reserved.
# Use of this source code is governed by the Apache v2.0 license that can be
# found in the LICENSE file.

"""Runs a command with optional isolated input/output.

Despite name "run_isolated", can run a generic non-isolated command specified as
args.

If input isolated hash is provided, fetches it, creates a tree of hard links,
appends args to the command in the fetched isolated and runs it.
To improve performance, keeps a local cache.
The local cache can safely be deleted.

Any ${ISOLATED_OUTDIR} on the command line will be replaced by the location of a
temporary directory upon execution of the command specified in the .isolated
file. All content written to this directory will be uploaded upon termination
and the .isolated file describing this directory will be printed to stdout.
"""

__version__ = '0.7.0'

import base64
import logging
import optparse
import os
import sys
import tempfile
import time

from third_party.depot_tools import fix_encoding

from utils import file_path
from utils import fs
from utils import large
from utils import logging_utils
from utils import on_error
from utils import subprocess42
from utils import tools
from utils import zip_package

import auth
import isolateserver


ISOLATED_OUTDIR_PARAMETER = '${ISOLATED_OUTDIR}'

# Absolute path to this file (can be None if running from zip on Mac).
THIS_FILE_PATH = os.path.abspath(__file__) if __file__ else None

# Directory that contains this file (might be inside zip package).
BASE_DIR = os.path.dirname(THIS_FILE_PATH) if __file__ else None

# Directory that contains currently running script file.
if zip_package.get_main_script_path():
  MAIN_DIR = os.path.dirname(
      os.path.abspath(zip_package.get_main_script_path()))
else:
  # This happens when 'import run_isolated' is executed at the python
  # interactive prompt, in that case __file__ is undefined.
  MAIN_DIR = None

# The name of the log file to use.
RUN_ISOLATED_LOG_FILE = 'run_isolated.log'

# The name of the log to use for the run_test_cases.py command
RUN_TEST_CASES_LOG = 'run_test_cases.log'


def get_as_zip_package(executable=True):
  """Returns ZipPackage with this module and all its dependencies.

  If |executable| is True will store run_isolated.py as __main__.py so that
  zip package is directly executable be python.
  """
  # Building a zip package when running from another zip package is
  # unsupported and probably unneeded.
  assert not zip_package.is_zipped_module(sys.modules[__name__])
  assert THIS_FILE_PATH
  assert BASE_DIR
  package = zip_package.ZipPackage(root=BASE_DIR)
  package.add_python_file(THIS_FILE_PATH, '__main__.py' if executable else None)
  package.add_python_file(os.path.join(BASE_DIR, 'isolated_format.py'))
  package.add_python_file(os.path.join(BASE_DIR, 'isolateserver.py'))
  package.add_python_file(os.path.join(BASE_DIR, 'auth.py'))
  package.add_directory(os.path.join(BASE_DIR, 'third_party'))
  package.add_directory(os.path.join(BASE_DIR, 'utils'))
  return package


def make_temp_dir(prefix, root_dir=None):
  """Returns a temporary directory.

  If root_dir is given and /tmp is on same file system as root_dir, uses /tmp.
  Otherwise makes a new temp directory under root_dir.

  Except on OSX, because it's dangerous to create hardlinks in $TMPDIR on OSX!
  /System/Library/LaunchDaemons/com.apple.bsd.dirhelper.plist runs every day at
  3:35am and deletes all files older than 3 days in $TMPDIR, but hardlinks do
  not have the inode modification time updated, so they tend to be old, thus
  they get deleted.
  """
  base_temp_dir = None
  real_temp_dir = unicode(tempfile.gettempdir())
  if sys.platform == 'darwin':
    # Nope! Nope! Nope!
    assert root_dir, 'It is unsafe to create hardlinks in $TMPDIR'
    base_temp_dir = root_dir
  elif root_dir and not file_path.is_same_filesystem(root_dir, real_temp_dir):
    base_temp_dir = root_dir
  return unicode(tempfile.mkdtemp(prefix=prefix, dir=base_temp_dir))


def change_tree_read_only(rootdir, read_only):
  """Changes the tree read-only bits according to the read_only specification.

  The flag can be 0, 1 or 2, which will affect the possibility to modify files
  and create or delete files.
  """
  if read_only == 2:
    # Files and directories (except on Windows) are marked read only. This
    # inhibits modifying, creating or deleting files in the test directory,
    # except on Windows where creating and deleting files is still possible.
    file_path.make_tree_read_only(rootdir)
  elif read_only == 1:
    # Files are marked read only but not the directories. This inhibits
    # modifying files but creating or deleting files is still possible.
    file_path.make_tree_files_read_only(rootdir)
  elif read_only in (0, None):
    # Anything can be modified.
    # TODO(maruel): This is currently dangerous as long as DiskCache.touch()
    # is not yet changed to verify the hash of the content of the files it is
    # looking at, so that if a test modifies an input file, the file must be
    # deleted.
    file_path.make_tree_writeable(rootdir)
  else:
    raise ValueError(
        'change_tree_read_only(%s, %s): Unknown flag %s' %
        (rootdir, read_only, read_only))


def process_command(command, out_dir):
  """Replaces isolated specific variables in a command line."""
  def fix(arg):
    if ISOLATED_OUTDIR_PARAMETER in arg:
      arg = arg.replace(ISOLATED_OUTDIR_PARAMETER, out_dir)
      # Replace slashes only if ISOLATED_OUTDIR_PARAMETER is present
      # because of arguments like '${ISOLATED_OUTDIR}/foo/bar'
      arg = arg.replace('/', os.sep)
    return arg

  return [fix(arg) for arg in command]


def run_command(command, cwd, tmp_dir, hard_timeout, grace_period):
  """Runs the command.

  Returns:
    tuple(process exit code, bool if had a hard timeout)
  """
  logging.info('run_command(%s, %s)' % (command, cwd))

  env = os.environ.copy()
  if sys.platform == 'darwin':
    env['TMPDIR'] = tmp_dir.encode('ascii')
  elif sys.platform == 'win32':
    env['TEMP'] = tmp_dir.encode('ascii')
  else:
    env['TMP'] = tmp_dir.encode('ascii')
  exit_code = None
  had_hard_timeout = False
  with tools.Profiler('RunTest'):
    proc = None
    had_signal = []
    try:
      # TODO(maruel): This code is imperfect. It doesn't handle well signals
      # during the download phase and there's short windows were things can go
      # wrong.
      def handler(signum, _frame):
        if proc and not had_signal:
          logging.info('Received signal %d', signum)
          had_signal.append(True)
          raise subprocess42.TimeoutExpired(command, None)

      proc = subprocess42.Popen(command, cwd=cwd, env=env, detached=True)
      with subprocess42.set_signal_handler(subprocess42.STOP_SIGNALS, handler):
        try:
          exit_code = proc.wait(hard_timeout or None)
        except subprocess42.TimeoutExpired:
          if not had_signal:
            logging.warning('Hard timeout')
            had_hard_timeout = True
          logging.warning('Sending SIGTERM')
          proc.terminate()

      # Ignore signals in grace period. Forcibly give the grace period to the
      # child process.
      if exit_code is None:
        ignore = lambda *_: None
        with subprocess42.set_signal_handler(subprocess42.STOP_SIGNALS, ignore):
          try:
            exit_code = proc.wait(grace_period or None)
          except subprocess42.TimeoutExpired:
            # Now kill for real. The user can distinguish between the
            # following states:
            # - signal but process exited within grace period,
            #   hard_timed_out will be set but the process exit code will be
            #   script provided.
            # - processed exited late, exit code will be -9 on posix.
            logging.warning('Grace exhausted; sending SIGKILL')
            proc.kill()
      logging.info('Waiting for proces exit')
      exit_code = proc.wait()
    except OSError:
      # This is not considered to be an internal error. The executable simply
      # does not exit.
      sys.stderr.write(
          '<The executable does not exist or a dependent library is missing>\n'
          '<Check for missing .so/.dll in the .isolate or GN file>\n'
          '<Command: %s>\n' % command)
      if os.environ.get('SWARMING_TASK_ID'):
        # Give an additional hint when running as a swarming task.
        sys.stderr.write(
            '<See the task\'s page for commands to help diagnose this issue '
            'by reproducing the task locally>\n')
      exit_code = 1
  logging.info(
      'Command finished with exit code %d (%s)',
      exit_code, hex(0xffffffff & exit_code))
  return exit_code, had_hard_timeout


def fetch_and_measure(isolated_hash, storage, cache, outdir):
  """Fetches an isolated and returns (bundle, stats)."""
  start = time.time()
  bundle = isolateserver.fetch_isolated(
      isolated_hash=isolated_hash,
      storage=storage,
      cache=cache,
      outdir=outdir)
  return bundle, {
    'duration': time.time() - start,
    'initial_number_items': cache.initial_number_items,
    'initial_size': cache.initial_size,
    'items_cold': base64.b64encode(large.pack(sorted(cache.added))),
    'items_hot': base64.b64encode(
        large.pack(sorted(set(cache.linked) - set(cache.added)))),
  }


def delete_and_upload(storage, out_dir, leak_temp_dir):
  """Deletes the temporary run directory and uploads results back.

  Returns:
    tuple(outputs_ref, success, stats)
    - outputs_ref: a dict referring to the results archived back to the isolated
          server, if applicable.
    - success: False if something occurred that means that the task must
          forcibly be considered a failure, e.g. zombie processes were left
          behind.
    - stats: uploading stats.
  """

  # Upload out_dir and generate a .isolated file out of this directory. It is
  # only done if files were written in the directory.
  outputs_ref = None
  cold = []
  hot = []
  start = time.time()

  if fs.isdir(out_dir) and fs.listdir(out_dir):
    with tools.Profiler('ArchiveOutput'):
      try:
        results, f_cold, f_hot = isolateserver.archive_files_to_storage(
            storage, [out_dir], None)
        outputs_ref = {
          'isolated': results[0][0],
          'isolatedserver': storage.location,
          'namespace': storage.namespace,
        }
        cold = sorted(i.size for i in f_cold)
        hot = sorted(i.size for i in f_hot)
      except isolateserver.Aborted:
        # This happens when a signal SIGTERM was received while uploading data.
        # There is 2 causes:
        # - The task was too slow and was about to be killed anyway due to
        #   exceeding the hard timeout.
        # - The amount of data uploaded back is very large and took too much
        #   time to archive.
        sys.stderr.write('Received SIGTERM while uploading')
        # Re-raise, so it will be treated as an internal failure.
        raise

  success = False
  try:
    if (not leak_temp_dir and fs.isdir(out_dir) and
        not file_path.rmtree(out_dir)):
      logging.error('Had difficulties removing out_dir %s', out_dir)
    else:
      success = True
  except OSError as e:
    # When this happens, it means there's a process error.
    logging.exception('Had difficulties removing out_dir %s: %s', out_dir, e)
  stats = {
    'duration': time.time() - start,
    'items_cold': base64.b64encode(large.pack(cold)),
    'items_hot': base64.b64encode(large.pack(hot)),
  }
  return outputs_ref, success, stats


def map_and_run(
    command, isolated_hash, storage, cache, leak_temp_dir, root_dir,
    hard_timeout, grace_period, extra_args):
  """Runs a command with optional isolated input/output.

  See run_tha_test for argument documentation.

  Returns metadata about the result.
  """
  assert bool(command) ^ bool(isolated_hash)
  result = {
    'duration': None,
    'exit_code': None,
    'had_hard_timeout': False,
    'internal_failure': None,
    'stats': {
    #  'download': {
    #    'duration': 0.,
    #    'initial_number_items': 0,
    #    'initial_size': 0,
    #    'items_cold': '<large.pack()>',
    #    'items_hot': '<large.pack()>',
    #  },
    #  'upload': {
    #    'duration': 0.,
    #    'items_cold': '<large.pack()>',
    #    'items_hot': '<large.pack()>',
    #  },
    },
    'outputs_ref': None,
    'version': 3,
  }
  if root_dir:
    file_path.ensure_tree(root_dir, 0700)
    prefix = u''
  else:
    root_dir = os.path.dirname(cache.cache_dir) if cache.cache_dir else None
    prefix = u'isolated_'
  run_dir = make_temp_dir(prefix + u'run', root_dir)
  out_dir = make_temp_dir(prefix + u'out', root_dir)
  tmp_dir = make_temp_dir(prefix + u'tmp', root_dir)
  cwd = run_dir

  try:
    if isolated_hash:
      bundle, result['stats']['download'] = fetch_and_measure(
          isolated_hash=isolated_hash,
          storage=storage,
          cache=cache,
          outdir=run_dir)
      if not bundle.command:
        # Handle this as a task failure, not an internal failure.
        sys.stderr.write(
            '<The .isolated doesn\'t declare any command to run!>\n'
            '<Check your .isolate for missing \'command\' variable>\n')
        if os.environ.get('SWARMING_TASK_ID'):
          # Give an additional hint when running as a swarming task.
          sys.stderr.write('<This occurs at the \'isolate\' step>\n')
        result['exit_code'] = 1
        return result

      change_tree_read_only(run_dir, bundle.read_only)
      cwd = os.path.normpath(os.path.join(cwd, bundle.relative_cwd))
      command = bundle.command + extra_args
    file_path.ensure_command_has_abs_path(command, cwd)
    sys.stdout.flush()
    start = time.time()
    try:
      result['exit_code'], result['had_hard_timeout'] = run_command(
          process_command(command, out_dir), cwd, tmp_dir, hard_timeout,
          grace_period)
    finally:
      result['duration'] = max(time.time() - start, 0)
  except Exception as e:
    # An internal error occured. Report accordingly so the swarming task will be
    # retried automatically.
    logging.exception('internal failure: %s', e)
    result['internal_failure'] = str(e)
    on_error.report(None)
  finally:
    try:
      if leak_temp_dir:
        logging.warning(
            'Deliberately leaking %s for later examination', run_dir)
      else:
        # On Windows rmtree(run_dir) call above has a synchronization effect: it
        # finishes only when all task child processes terminate (since a running
        # process locks *.exe file). Examine out_dir only after that call
        # completes (since child processes may write to out_dir too and we need
        # to wait for them to finish).
        if fs.isdir(run_dir):
          try:
            success = file_path.rmtree(run_dir)
          except OSError as e:
            logging.error('Failure with %s', e)
            success = False
          if not success:
            print >> sys.stderr, (
                'Failed to delete the run directory, forcibly failing\n'
                'the task because of it. No zombie process can outlive a\n'
                'successful task run and still be marked as successful.\n'
                'Fix your stuff.')
            if result['exit_code'] == 0:
              result['exit_code'] = 1
        if fs.isdir(tmp_dir):
          try:
            success = file_path.rmtree(tmp_dir)
          except OSError as e:
            logging.error('Failure with %s', e)
            success = False
          if not success:
            print >> sys.stderr, (
                'Failed to delete the temporary directory, forcibly failing\n'
                'the task because of it. No zombie process can outlive a\n'
                'successful task run and still be marked as successful.\n'
                'Fix your stuff.')
            if result['exit_code'] == 0:
              result['exit_code'] = 1

      # This deletes out_dir if leak_temp_dir is not set.
      result['outputs_ref'], success, result['stats']['upload'] = (
          delete_and_upload(storage, out_dir, leak_temp_dir))
      if not success and result['exit_code'] == 0:
        result['exit_code'] = 1
    except Exception as e:
      # Swallow any exception in the main finally clause.
      logging.exception('Leaking out_dir %s: %s', out_dir, e)
      result['internal_failure'] = str(e)
  return result


def run_tha_test(
    command, isolated_hash, storage, cache, leak_temp_dir, result_json,
    root_dir, hard_timeout, grace_period, extra_args):
  """Runs an executable and records execution metadata.

  Either command or isolated_hash must be specified.

  If isolated_hash is specified, downloads the dependencies in the cache,
  hardlinks them into a temporary directory and runs the command specified in
  the .isolated.

  A temporary directory is created to hold the output files. The content inside
  this directory will be uploaded back to |storage| packaged as a .isolated
  file.

  Arguments:
    command: the command to run, a list of strings. Mutually exclusive with
             isolated_hash.
    isolated_hash: the SHA-1 of the .isolated file that must be retrieved to
                   recreate the tree of files to run the target executable.
                   The command specified in the .isolated is executed.
                   Mutually exclusive with command argument.
    storage: an isolateserver.Storage object to retrieve remote objects. This
             object has a reference to an isolateserver.StorageApi, which does
             the actual I/O.
    cache: an isolateserver.LocalCache to keep from retrieving the same objects
           constantly by caching the objects retrieved. Can be on-disk or
           in-memory.
    leak_temp_dir: if true, the temporary directory will be deliberately leaked
                   for later examination.
    result_json: file path to dump result metadata into. If set, the process
                 exit code is always 0 unless an internal error occured.
    root_dir: directory to the path to use to create the temporary directory. If
              not specified, a random temporary directory is created.
    hard_timeout: kills the process if it lasts more than this amount of
                  seconds.
    grace_period: number of seconds to wait between SIGTERM and SIGKILL.
    extra_args: optional arguments to add to the command stated in the .isolate
                file. Ignored if isolate_hash is empty.

  Returns:
    Process exit code that should be used.
  """
  assert bool(command) ^ bool(isolated_hash)
  extra_args = extra_args or []
  if any(ISOLATED_OUTDIR_PARAMETER in a for a in (command or extra_args)):
    assert storage is not None, 'storage is None although outdir is specified'

  if result_json:
    # Write a json output file right away in case we get killed.
    result = {
      'exit_code': None,
      'had_hard_timeout': False,
      'internal_failure': 'Was terminated before completion',
      'outputs_ref': None,
      'version': 2,
    }
    tools.write_json(result_json, result, dense=True)

  # run_isolated exit code. Depends on if result_json is used or not.
  result = map_and_run(
      command, isolated_hash, storage, cache, leak_temp_dir, root_dir,
      hard_timeout, grace_period, extra_args)
  logging.info('Result:\n%s', tools.format_json(result, dense=True))
  if result_json:
    # We've found tests to delete 'work' when quitting, causing an exception
    # here. Try to recreate the directory if necessary.
    file_path.ensure_tree(os.path.dirname(result_json))
    tools.write_json(result_json, result, dense=True)
    # Only return 1 if there was an internal error.
    return int(bool(result['internal_failure']))

  # Marshall into old-style inline output.
  if result['outputs_ref']:
    data = {
      'hash': result['outputs_ref']['isolated'],
      'namespace': result['outputs_ref']['namespace'],
      'storage': result['outputs_ref']['isolatedserver'],
    }
    sys.stdout.flush()
    print(
        '[run_isolated_out_hack]%s[/run_isolated_out_hack]' %
        tools.format_json(data, dense=True))
    sys.stdout.flush()
  return result['exit_code'] or int(bool(result['internal_failure']))


def main(args):
  parser = logging_utils.OptionParserWithLogging(
      usage='%prog <options> [command to run or extra args]',
      version=__version__,
      log_file=RUN_ISOLATED_LOG_FILE)
  parser.add_option(
      '--clean', action='store_true',
      help='Cleans the cache, trimming it necessary and remove corrupted items '
           'and returns without executing anything; use with -v to know what '
           'was done')
  parser.add_option(
      '--json',
      help='dump output metadata to json file. When used, run_isolated returns '
           'non-zero only on internal failure')
  parser.add_option(
      '--hard-timeout', type='float', help='Enforce hard timeout in execution')
  parser.add_option(
      '--grace-period', type='float',
      help='Grace period between SIGTERM and SIGKILL')
  data_group = optparse.OptionGroup(parser, 'Data source')
  data_group.add_option(
      '-s', '--isolated',
      help='Hash of the .isolated to grab from the isolate server.')
  isolateserver.add_isolate_server_options(data_group)
  parser.add_option_group(data_group)

  isolateserver.add_cache_options(parser)
  parser.set_defaults(cache='cache')

  debug_group = optparse.OptionGroup(parser, 'Debugging')
  debug_group.add_option(
      '--leak-temp-dir',
      action='store_true',
      help='Deliberately leak isolate\'s temp dir for later examination '
           '[default: %default]')
  debug_group.add_option(
      '--root-dir', help='Use a directory instead of a random one')
  parser.add_option_group(debug_group)

  auth.add_auth_options(parser)
  options, args = parser.parse_args(args)

  cache = isolateserver.process_cache_options(options)
  if options.clean:
    if options.isolated:
      parser.error('Can\'t use --isolated with --clean.')
    if options.isolate_server:
      parser.error('Can\'t use --isolate-server with --clean.')
    if options.json:
      parser.error('Can\'t use --json with --clean.')
    cache.cleanup()
    return 0

  if not options.isolated and not args:
    parser.error('--isolated or command to run is required.')

  auth.process_auth_options(parser, options)

  isolateserver.process_isolate_server_options(
    parser, options, True, False)
  if not options.isolate_server:
    if options.isolated:
      parser.error('--isolated requires --isolate-server')
    if ISOLATED_OUTDIR_PARAMETER in args:
      parser.error(
        '%s in args requires --isolate-server' % ISOLATED_OUTDIR_PARAMETER)

  if options.root_dir:
    options.root_dir = unicode(os.path.abspath(options.root_dir))
  if options.json:
    options.json = unicode(os.path.abspath(options.json))

  command = [] if options.isolated else args
  if options.isolate_server:
    storage = isolateserver.get_storage(
      options.isolate_server, options.namespace)
    # Hashing schemes used by |storage| and |cache| MUST match.
    assert storage.hash_algo == cache.hash_algo
    return run_tha_test(
        command, options.isolated, storage, cache, options.leak_temp_dir,
        options.json, options.root_dir, options.hard_timeout,
        options.grace_period, args)
  else:
    return run_tha_test(
        command, options.isolated, None, cache, options.leak_temp_dir,
        options.json, options.root_dir, options.hard_timeout,
        options.grace_period, args)


if __name__ == '__main__':
  # Ensure that we are always running with the correct encoding.
  fix_encoding.fix_encoding()
  sys.exit(main(sys.argv[1:]))
