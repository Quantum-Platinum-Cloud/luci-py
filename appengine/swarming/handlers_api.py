# Copyright 2014 The Swarming Authors. All rights reserved.
# Use of this source code is governed by the Apache v2.0 license that can be
# found in the LICENSE file.

"""REST APIs handlers."""

import logging
import textwrap

import webapp2

from google.appengine.api import datastore_errors
from google.appengine.datastore import datastore_query
from google.appengine import runtime
from google.appengine.ext import ndb

from components import auth
from components import ereporter2
from components import utils
from server import acl
from server import bot_code
from server import bot_management
from server import stats
from server import task_result
from server import task_scheduler
from server import task_to_run


def log_unexpected_keys(expected_keys, actual_keys, request, source, name):
  """Logs an error if unexpected keys are present or expected keys are missing.
  """
  return log_unexpected_subset_keys(
      expected_keys, expected_keys, actual_keys, request, source, name)


def log_unexpected_subset_keys(
    expected_keys, minimum_keys, actual_keys, request, source, name):
  """Logs an error if unexpected keys are present or expected keys are missing.

  Accepts optional keys.

  This is important to catch typos.
  """
  actual_keys = frozenset(actual_keys)
  superfluous = actual_keys - expected_keys
  missing = minimum_keys - actual_keys
  if superfluous or missing:
    msg_missing = (' missing: %s' % sorted(missing)) if missing else ''
    msg_superfluous = (
        (' superfluous: %s' % sorted(superfluous)) if superfluous else '')
    message = 'Unexpected %s%s%s; did you make a typo?' % (
        name, msg_missing, msg_superfluous)
    ereporter2.log_request(
        request,
        source=source,
        message=message)
    return message


def log_missing_keys(minimum_keys, actual_keys, request, source, name):
  """Logs an error if expected keys are not present.

  Do not warn about unexpected keys.
  """
  actual_keys = frozenset(actual_keys)
  missing = minimum_keys - actual_keys
  if missing:
    msg_missing = (' missing: %s' % sorted(missing)) if missing else ''
    message = 'Unexpected %s%s; did you make a typo?' % (name, msg_missing)
    ereporter2.log_request(
        request,
        source=source,
        message=message)
    return message


def process_doc(handler):
  lines = handler.__doc__.rstrip().splitlines()
  rest = textwrap.dedent('\n'.join(lines[1:]))
  return '\n'.join((lines[0], rest)).rstrip()


### New Client APIs.


class ClientApiListHandler(auth.ApiHandler):
  """All query handlers"""

  @auth.public
  def get(self):
    # Hard to make it any simpler.
    prefix = '/swarming/api/v1/client/'
    data = {
      r.template[len(prefix):]: process_doc(r.handler) for r in get_routes()
      if r.template.startswith(prefix) and hasattr(r.handler, 'get')
    }
    self.send_response(data)


class ClientHandshakeHandler(auth.ApiHandler):
  """First request to be called to get initial data like XSRF token.

  Request body is a JSON dict:
    {
      # TODO(maruel): Add useful data.
    }

  Response body is a JSON dict:
    {
      "server_version": "138-193f1f3",
      "xsrf_token": "......",
    }
  """

  # This handler is called to get XSRF token, there's nothing to enforce yet.
  xsrf_token_enforce_on = ()

  EXPECTED_KEYS = frozenset()

  @auth.require_xsrf_token_request
  @auth.require(acl.is_bot_or_user)
  def post(self):
    request = self.parse_body()
    log_unexpected_keys(
        self.EXPECTED_KEYS, request, self.request, 'client', 'keys')
    data = {
      # This access token will be used to validate each subsequent request.
      'server_version': utils.get_app_version(),
      'xsrf_token': self.generate_xsrf_token(),
    }
    self.send_response(data)


class ClientTaskResultBase(auth.ApiHandler):
  """Implements the common base code for task related query APIs."""

  def get_result_key(self, task_id):
    # TODO(maruel): Users can only request their own task. Privileged users can
    # request any task.
    key = None
    summary_key = None
    try:
      key = task_result.unpack_result_summary_key(task_id)
      summary_key = key
    except ValueError:
      try:
        key = task_result.unpack_run_result_key(task_id)
        summary_key = task_result.run_result_key_to_result_summary_key(key)
      except ValueError:
        self.abort_with_error(400, error='Invalid key')
    return key, summary_key

  def get_result_entity(self, task_id):
    key, _ = self.get_result_key(task_id)
    result = key.get()
    if not result:
      self.abort_with_error(404, error='Task not found')
    return result


class ClientTaskResultHandler(ClientTaskResultBase):
  """Task's result meta data"""

  @auth.require(acl.is_bot_or_user)
  def get(self, task_id):
    result = self.get_result_entity(task_id)
    self.send_response(utils.to_json_encodable(result))


class ClientTaskResultRequestHandler(ClientTaskResultBase):
  """Task's request details"""

  @auth.require(acl.is_bot_or_user)
  def get(self, task_id):
    _, summary_key = self.get_result_key(task_id)
    request_key = task_result.result_summary_key_to_request_key(summary_key)
    self.send_response(utils.to_json_encodable(request_key.get()))


class ClientTaskResultOutputHandler(ClientTaskResultBase):
  """Task's output for a single command"""

  @auth.require(acl.is_bot_or_user)
  def get(self, task_id, command_index):
    result = self.get_result_entity(task_id)
    output = result.get_command_output_async(int(command_index)).get_result()
    if output:
      output = output.decode('utf-8', 'replace')
    # JSON then reencodes to ascii compatible encoded strings, which explodes
    # the size.
    data = {
      'output': output,
    }
    self.send_response(utils.to_json_encodable(data))


class ClientTaskResultOutputAllHandler(ClientTaskResultBase):
  """All output from all commands in a task"""

  @auth.require(acl.is_bot_or_user)
  def get(self, task_id):
    result = self.get_result_entity(task_id)
    # JSON then reencodes to ascii compatible encoded strings, which explodes
    # the size.
    data = {
      'outputs': [
        i.decode('utf-8', 'replace') if i else i
        for i in result.get_outputs()
      ],
    }
    self.send_response(utils.to_json_encodable(data))


class ClientApiTasksHandler(auth.ApiHandler):
  """Requests all TaskResultSummary with filters.

  It is specifically a GET with query parameters for simplicity instead of a
  JSON POST.

  Arguments:
    name: Search by task name; str or None.
    tag: Search by task tag, can be used mulitple times; list(str) or None.
    cursor: Continue a previous query; str or None.
    limit: Maximum number of items to return.
    sort: Ordering: 'created_ts', 'modified_ts', 'completed_ts', 'abandoned_ts'.
        Defaults to 'created_ts'.
    state: Filtering: 'all', 'pending', 'running', 'pending_running',
        'completed', 'completed_success', 'completed_failure', 'bot_died',
        'expired', 'canceled'. Defaults to 'all'.

  In particular, one of `name`, `tag` or `state` can be used
  exclusively.
  """
  EXPECTED = {'cursor', 'limit', 'name', 'sort', 'state', 'tag'}

  @auth.require(acl.is_privileged_user)
  def get(self):
    extra = frozenset(self.request.GET) - self.EXPECTED
    if extra:
      self.abort_with_error(
          400,
          error='Extraneous query parameters. Did you make a typo? %s' %
          ','.join(sorted(extra)))

    # Use a similar query to /user/tasks.
    name = self.request.get('name')
    tags = self.request.get_all('tag')
    cursor_str = self.request.get('cursor')
    limit = int(self.request.get('limit', 100))
    sort = self.request.get('sort', 'created_ts')
    state = self.request.get('state', 'all')

    uses = bool(name) + bool(tags) + bool(state!='all')
    if uses > 1:
      self.abort_with_error(
          400, error='Only one of name, tag (1 or many) or state can be used')

    items, cursor_str, sort, state = task_result.get_tasks(
        name, tags, cursor_str, limit, sort, state)
    data = {
      'cursor': cursor_str,
      'items': items,
      'limit': limit,
      'sort': sort,
      'state': state,
    }
    self.send_response(utils.to_json_encodable(data))


class ClientApiBots(auth.ApiHandler):
  """Bots known to the server"""

  @auth.require(acl.is_privileged_user)
  def get(self):
    now = utils.utcnow()
    limit = int(self.request.get('limit', 1000))
    cursor = datastore_query.Cursor(urlsafe=self.request.get('cursor'))
    q = bot_management.Bot.query().order(bot_management.Bot.key)
    bots, cursor, more = q.fetch_page(limit, start_cursor=cursor)
    data = {
      'cursor': cursor.urlsafe() if cursor and more else None,
      'death_timeout': bot_management.BOT_DEATH_TIMEOUT.total_seconds(),
      'items': [b.to_dict_with_now(now) for b in bots],
      'limit': limit,
      'now': now,
    }
    self.send_response(utils.to_json_encodable(data))


class ClientApiBot(auth.ApiHandler):
  """Bot's meta data"""

  @auth.require(acl.is_privileged_user)
  def get(self, bot_id):
    bot = bot_management.get_bot_key(bot_id).get()
    if not bot:
      self.abort_with_error(404, error='Bot not found')
    now = utils.utcnow()
    self.send_response(utils.to_json_encodable(bot.to_dict_with_now(now)))

  @auth.require(acl.is_admin)
  def delete(self, bot_id):
    bot_key = bot_management.get_bot_key(bot_id)
    found = False
    if bot_key.get():
      bot_key.delete()
      found = True
    self.send_response({'deleted': bool(found)})


class ClientApiBotTask(auth.ApiHandler):
  """Tasks executed on a specific bot"""

  @auth.require(acl.is_privileged_user)
  def get(self, bot_id):
    limit = int(self.request.get('limit', 100))
    cursor = datastore_query.Cursor(urlsafe=self.request.get('cursor'))
    run_results, cursor, more = task_result.TaskRunResult.query(
        task_result.TaskRunResult.bot_id == bot_id).order(
            -task_result.TaskRunResult.started_ts).fetch_page(
                limit, start_cursor=cursor)
    now = utils.utcnow()
    data = {
      'cursor': cursor.urlsafe() if cursor and more else None,
      'items': run_results,
      'limit': limit,
      'now': now,
    }
    self.send_response(utils.to_json_encodable(data))


class ClientApiServer(auth.ApiHandler):
  """Server details"""

  @auth.require(acl.is_privileged_user)
  def get(self):
    data = {
      'bot_version': bot_code.get_bot_version(self.request.host_url),
    }
    self.send_response(utils.to_json_encodable(data))


class ClientRequestHandler(auth.ApiHandler):
  """Creates a new request, returns all the meta data about the request."""
  @auth.require(acl.is_bot_or_user)
  def post(self):
    request = self.parse_body()
    # If the priority is below 100, make the the user has right to do so.
    if request.get('priority', 255) < 100 and not acl.is_bot_or_admin():
      # Silently drop the priority of normal users.
      request['priority'] = 100

    try:
      request, result_summary = task_scheduler.make_request(request)
    except (datastore_errors.BadValueError, TypeError, ValueError) as e:
      self.abort_with_error(400, error=str(e))

    data = {
      'request': request.to_dict(),
      'task_id': task_result.pack_result_summary_key(result_summary.key),
    }
    self.send_response(utils.to_json_encodable(data))


class ClientCancelHandler(auth.ApiHandler):
  """Cancels a task."""

  # TODO(maruel): Allow privileged users to cancel, and users to cancel their
  # own task.
  @auth.require(acl.is_admin)
  def post(self):
    request = self.parse_body()
    task_id = request.get('task_id')
    summary_key = task_result.unpack_result_summary_key(task_id)

    ok, was_running = task_scheduler.cancel_task(summary_key)
    out = {
      'ok': ok,
      'was_running': was_running,
    }
    self.send_response(out)


### Bot APIs


class BootstrapHandler(auth.AuthenticatingHandler):
  """Returns python code to run to bootstrap a swarming bot."""

  @auth.require(acl.is_bot)
  def get(self):
    self.response.headers['Content-Type'] = 'text/x-python'
    self.response.headers['Content-Disposition'] = (
        'attachment; filename="swarming_bot_bootstrap.py"')
    self.response.out.write(bot_code.get_bootstrap(self.request.host_url))


class GetSlaveCodeHandler(auth.AuthenticatingHandler):
  """Returns a zip file with all the files required by a bot.

  Optionally specify the hash version to download. If so, the returned data is
  cacheable.
  """

  @auth.require(acl.is_bot)
  def get(self, version=None):
    if version:
      expected = bot_code.get_bot_version(self.request.host_url)
      if version != expected:
        logging.error('Requested Swarming bot %s, have %s', version, expected)
        self.abort(404)
      self.response.headers['Cache-Control'] = 'public, max-age=3600'
    else:
      self.response.headers['Cache-Control'] = 'no-cache, no-store'
    self.response.headers['Content-Type'] = 'application/octet-stream'
    self.response.headers['Content-Disposition'] = (
        'attachment; filename="swarming_bot.zip"')
    self.response.out.write(
        bot_code.get_swarming_bot_zip(self.request.host_url))


class BotHandshakeHandler(auth.ApiHandler):
  """First request to be called to get initial data like XSRF token.

  The bot is server-controled so the server doesn't have to support multiple API
  version. Only the current one and the last one, since the bot are finishing
  their currently running task, they'll be immediately be upgraded after on
  their next poll.

  Request body is a JSON dict:
    {
      "dimensions": <dict of properties>,
      "state": <dict of properties>,
      "version": <sha-1 of swarming_bot.zip uncompressed content>,
    }

  Response body is a JSON dict:
    {
      "bot_version": <sha-1 of swarming_bot.zip uncompressed content>,
      "server_version": "138-193f1f3",
      "xsrf_token": "......",
    }
  """

  # This handler is called to get XSRF token, there's nothing to enforce yet.
  xsrf_token_enforce_on = ()

  # TODO(maruel): Enforce the correct keys once all rolled out.
  ACCEPTED_KEYS = {u'attributes', u'dimensions', u'state', u'version'}
  EXPECTED_KEYS = frozenset()

  @auth.require_xsrf_token_request
  @auth.require(acl.is_bot)
  def post(self):
    # In particular, this endpoint does not return commands to the bot, for
    # example to upgrade itself. It'll be told so when it does its first poll.
    request = self.parse_body()
    log_unexpected_subset_keys(
        self.ACCEPTED_KEYS, self.EXPECTED_KEYS, request, self.request, 'bot',
        'keys')

    dimensions = request.get('dimensions', {})
    # TODO(maruel): Remove and move to 'state'.
    state = request.get('state', {})
    hostnames = state.get('hostname')
    if isinstance(hostnames, list) and len(hostnames) == 1:
      hostname = hostnames[0]
    else:
      hostname = hostnames
    bot_id = (dimensions.get('id') or ['unknown'])[0]
    quarantined = dimensions.get('quarantined', False)
    if bot_id:
      bot_management.tag_bot_seen(
          bot_id,
          hostname,
          state.get('ip'),
          self.request.remote_addr,
          dimensions,
          request.get('version', ''),
          quarantined,
          state)
    # Let it live even if bot_id is not set, so the bot has a chance to
    # self-update. It won't be assigned any task anyway.
    data = {
      # This access token will be used to validate each subsequent request.
      'bot_version': bot_code.get_bot_version(self.request.host_url),
      'server_version': utils.get_app_version(),
      'xsrf_token': self.generate_xsrf_token(),
    }
    self.send_response(data)


class BotPollHandler(auth.ApiHandler):
  """The bot polls for a task; returns either a task, update command or sleep.

  In case of exception on the bot, this is enough to get it just far enough to
  eventually self-update to a working version. This is to ensure that coding
  errors in bot code doesn't kill all the fleet at once, they should still be up
  just enough to be able to self-update again even if they don't get task
  assigned anymore.
  """
  ACCEPTED_KEYS = {u'attributes', u'dimensions', u'state', u'version'}
  EXPECTED_KEYS = {u'dimensions', u'state', u'version'}
  REQUIRED_STATE_KEYS = {u'running_time', u'sleep_streak'}

  @auth.require(acl.is_bot)
  def post(self):
    request = self.parse_body()

    msg = log_unexpected_subset_keys(
        self.ACCEPTED_KEYS, self.EXPECTED_KEYS, request, self.request, 'bot',
        'keys')

    state = request.get('state', {})
    log_missing_keys(
        self.REQUIRED_STATE_KEYS, state, self.request, 'bot', 'state')

    # Be very permissive on missing values. This can happen because of errors on
    # the bot, *we don't want to deny them the capacity to update*, so that the
    # bot code is eventually fixed and the bot self-update to this working code.
    # It makes fleet management much easier.
    dimensions = request.get('dimensions', {})
    bot_id = (dimensions.get('id') or ['unknown'])[0]
    # The bot may decide to "self-quarantine" itself.
    quarantined = dimensions.get('quarantined', False)

    if quarantined:
      logging.info('Bot self-quarantined: %s', dimensions)

    # The bot version is host-specific, because the host determines the version
    # being used.
    expected_version = bot_code.get_bot_version(self.request.host_url)
    if msg or request.get('version') != expected_version:
      self._cmd_update(expected_version)
      return

    # At that point, the bot should be in relatively good shape since it's
    # running the right version.

    sleep_streak = state.get('sleep_streak', 0)
    if not bot_id:
      self._cmd_sleep(sleep_streak, True)
      return

    # TODO(maruel): Add support for Admin-enforced quarantine. This will be done
    # with a separate entity type from bot_management.Bot. It is important to
    # differentiate between a bot self-quarantining and an admin forcibly
    # quarantining a bot.
    # https://code.google.com/p/swarming/issues/detail?id=115

    if not quarantined:
      if not all(
          isinstance(key, unicode) and
          isinstance(values, list) and
          all(isinstance(value, unicode) for value in values)
          for key, values in dimensions.iteritems()):
        # It's a big deal, alert the admins.
        ereporter2.log_request(
            self.request,
            source='bot',
            message='Invalid dimensions on bot')
        quarantined = True
      else:
        dimensions_count = task_to_run.dimensions_powerset_count(dimensions)
        if dimensions_count > task_to_run.MAX_DIMENSIONS:
          # It's a big deal, alert the admins.
          ereporter2.log_request(
              self.request,
              source='bot',
              message='Too many dimensions (%d) on bot' % dimensions_count)
          quarantined = True

    if not quarantined:
      # Note its existence at two places, one for stats at 1 minute resolution,
      # the other for the list of known bots.
      stats.add_entry(action='bot_active', bot_id=bot_id, dimensions=dimensions)

    # TODO(maruel): Remove and move to 'state'.
    hostnames = dimensions.get('hostname')
    if isinstance(hostnames, list) and len(hostnames) == 1:
      hostname = hostnames[0]
    else:
      hostname = hostnames
    bot_management.tag_bot_seen(
        bot_id,
        hostname,
        state.get('ip'),
        self.request.remote_addr,
        dimensions,
        request.get('version', ''),
        quarantined,
        state)

    if quarantined:
      self._cmd_sleep(sleep_streak, quarantined)
      return

    # Bot may need a reboot if it is running for too long.
    needs_restart, restart_message = bot_management.should_restart_bot(
        bot_id, request, state)
    if needs_restart:
      self._cmd_restart(restart_message)
      return

    # The bot is in good shape. Try to grab a task.
    try:
      # This is a fairly complex function call, exceptions are expected.
      request, run_result = task_scheduler.bot_reap_task(
          dimensions, bot_id, request.get('version', ''))
      if not request:
        # No task found, tell it to sleep a bit.
        self._cmd_sleep(sleep_streak, False)
        return

      self._cmd_run(request, run_result.key, bot_id)
    except runtime.DeadlineExceededError:
      # If the timeout happened before a task was assigned there is no problems.
      # If the timeout occurred after a task was assigned, that task will
      # timeout (BOT_DIED) since the bot didn't get the details required to
      # run it) and it will automatically get retried (TODO) when the task times
      # out.
      # TODO(maruel): Note the task if possible and hand it out on next poll.
      # https://code.google.com/p/swarming/issues/detail?id=130
      self.abort(500, 'Deadline')

  def _cmd_run(self, request, run_result_key, bot_id):
    out = {
      'cmd': 'run',
      'manifest': {
        'bot_id': bot_id,
        'commands': request.properties.commands,
        'data': request.properties.data,
        'env': request.properties.env,
        'host': utils.get_versioned_hosturl(),
        'hard_timeout': request.properties.execution_timeout_secs,
        'io_timeout': request.properties.io_timeout_secs,
        'task_id': task_result.pack_run_result_key(run_result_key),
      },
    }
    self.send_response(out)

  def _cmd_sleep(self, sleep_streak, quarantined):
    out = {
      'cmd': 'sleep',
      'duration': task_scheduler.exponential_backoff(sleep_streak),
      'quarantined': quarantined,
    }
    self.send_response(out)

  def _cmd_update(self, expected_version):
    out = {
      'cmd': 'update',
      'version': expected_version,
    }
    self.send_response(out)

  def _cmd_restart(self, message):
    logging.info('Rebooting bot: %s', message)
    out = {
      'cmd': 'restart',
      'message': message,
    }
    self.send_response(out)


class BotErrorHandler(auth.ApiHandler):
  """Specialized version of ereporter2's /ereporter2/api/v1/on_error.

  This formally quarantines the bot and sends an alert to the admins. It is
  meant to be used by bot_main.py for non-recoverable issues, for example when
  failing to self update.
  """
  EXPECTED_KEYS = {u'id', u'message'}

  @auth.require(acl.is_bot)
  def post(self):
    request = self.parse_body()
    log_unexpected_keys(
        self.EXPECTED_KEYS, request, self.request, 'bot', 'keys')

    bot_id = request.get('id', 'unknown')
    # When a bot reports here, it is borked, quarantine the bot.
    bot = bot_management.get_bot_key(bot_id).get()
    if not bot:
      bot_management.tag_bot_seen(
          bot_id,
          None,
          None,
          self.request.remote_addr,
          None,
          None,
          True,
          None)
    else:
      bot.quarantined = True
      bot.put()

    ereporter2.log(source='bot', message=request.get('message', 'unknown'))
    self.send_response({})


class BotTaskUpdateHandler(auth.ApiHandler):
  """Receives updates from a Bot for a task.

  The handler verifies packets are processed in order and will refuse
  out-of-order packets.
  """
  ACCEPTED_KEYS = {
    u'command_index', u'duration', u'exit_code', u'hard_timeout', u'id',
    u'io_timeout', u'output', u'output_chunk_start', u'task_id',
  }
  REQUIRED_KEYS = {u'command_index', u'id', u'task_id'}

  @auth.require(acl.is_bot)
  def post(self, task_id=None):
    # Unlike handshake and poll, we do not accept invalid keys here. This code
    # path is much more strict.
    request = self.parse_body()
    msg = log_unexpected_subset_keys(
        self.ACCEPTED_KEYS, self.REQUIRED_KEYS, request, self.request, 'bot',
        'keys')
    if msg:
      self.abort_with_error(400, error=msg)

    bot_id = request['id']
    command_index = request['command_index']
    task_id = request['task_id']

    duration = request.get('duration')
    exit_code = request.get('exit_code')
    output = request.get('output')
    output_chunk_start = request.get('output_chunk_start')

    # TODO(maruel): Make use of io_timeout and hard_timeout.

    run_result_key = task_result.unpack_run_result_key(task_id)
    # Side effect: zaps out any binary content on stdout.
    if output is not None:
      output = output.encode('utf-8', 'replace')

    try:
      with task_scheduler.bot_update_task(
          run_result_key, bot_id, command_index, output, output_chunk_start,
          exit_code, duration) as entities:
        # The reason for writing in a transaction is to get rid of partial DB
        # writes, e.g. a few entities got written but not others. This is a
        # problem with TaskOutputChunk where some stdout stream chunks would be
        # written but not other, causing irrecoverable errors.
        ndb.transaction(lambda: ndb.put_multi(entities), retries=1)
    except ValueError as e:
      ereporter2.log_request(
          request=self.request,
          source='server',
          category='task_failure',
          message='Failed to update task: %s' % e)
      self.abort_with_error(400, error=str(e))

    # TODO(maruel): When a task is canceled, reply with 'DIE' so that the bot
    # reboots itself to abort the task abruptly. It is useful when a task hangs
    # and the timeout was set too long or the task was superseded by a newer
    # task with more recent executable (e.g. a new Try Server job on a newer
    # patchset on Rietveld).
    self.send_response({'ok': True})


class BotTaskErrorHandler(auth.ApiHandler):
  """It is a specialized version of ereporter2's /ereporter2/api/v1/on_error
  that also attaches a task id to it.

  This formally kills the task, marking it as an internal failure. This can be
  used by bot_main.py to kill the task when task_runner misbehaved.
  """
  EXPECTED_KEYS = {u'id', u'message', u'task_id'}

  @auth.require(acl.is_bot)
  def post(self, task_id=None):
    request = self.parse_body()
    msg = log_unexpected_keys(
        self.EXPECTED_KEYS, request, self.request, 'bot', 'keys')

    ereporter2.log(source='bot', message=request.get('message', 'unknown'))
    if msg:
      self.abort_with_error(400, error=msg)

    bot_id = request['id']
    task_id = request['task_id']
    run_result = task_result.unpack_run_result_key(task_id).get()
    if run_result.bot_id != bot_id:
      msg = 'Bot %s sent task kill for task %s owned by bot %s' % (
          bot_id, run_result.bot_id, run_result.key)
      logging.error(msg)
      self.abort_with_error(400, error=msg)

    task_scheduler.bot_kill_task(run_result)
    self.send_response({})


class ServerPingHandler(webapp2.RequestHandler):
  """Handler to ping when checking if the server is up.

  This handler should be extremely lightweight. It shouldn't do any
  computations, it should just state that the server is up. It's open to
  everyone for simplicity and performance.
  """

  def get(self):
    self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
    self.response.out.write('Server up')


def get_routes():
  routes = [
      # New Client API:
      ('/swarming/api/v1/client/bots', ClientApiBots),
      ('/swarming/api/v1/client/bot/<bot_id:[^/]+>', ClientApiBot),
      ('/swarming/api/v1/client/bot/<bot_id:[^/]+>/tasks', ClientApiBotTask),
      ('/swarming/api/v1/client/cancel', ClientCancelHandler),
      ('/swarming/api/v1/client/handshake', ClientHandshakeHandler),
      ('/swarming/api/v1/client/list', ClientApiListHandler),
      ('/swarming/api/v1/client/request', ClientRequestHandler),
      ('/swarming/api/v1/client/server', ClientApiServer),
      ('/swarming/api/v1/client/task/<task_id:[0-9a-f]+>',
          ClientTaskResultHandler),
      ('/swarming/api/v1/client/task/<task_id:[0-9a-f]+>/request',
          ClientTaskResultRequestHandler),
      ('/swarming/api/v1/client/task/<task_id:[0-9a-f]+>/output/'
        '<command_index:[0-9]+>',
          ClientTaskResultOutputHandler),
      ('/swarming/api/v1/client/task/<task_id:[0-9a-f]+>/output/all',
          ClientTaskResultOutputAllHandler),
      ('/swarming/api/v1/client/tasks', ClientApiTasksHandler),

      # Bot
      ('/bootstrap', BootstrapHandler),
      ('/get_slave_code', GetSlaveCodeHandler),
      ('/get_slave_code/<version:[0-9a-f]{40}>', GetSlaveCodeHandler),
      ('/server_ping', ServerPingHandler),
      ('/swarming/api/v1/bot/error', BotErrorHandler),
      ('/swarming/api/v1/bot/handshake', BotHandshakeHandler),
      ('/swarming/api/v1/bot/poll', BotPollHandler),
      ('/swarming/api/v1/bot/task_update', BotTaskUpdateHandler),
      ('/swarming/api/v1/bot/task_update/<task_id:[a-f0-9]+>',
          BotTaskUpdateHandler),
      ('/swarming/api/v1/bot/task_error', BotTaskErrorHandler),
      ('/swarming/api/v1/bot/task_error/<task_id:[a-f0-9]+>',
          BotTaskErrorHandler),
  ]
  return [webapp2.Route(*i) for i in routes]
