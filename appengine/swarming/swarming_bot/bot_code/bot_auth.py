# Copyright 2016 The LUCI Authors. All rights reserved.
# Use of this source code is governed under the Apache License, Version 2.0
# that can be found in the LICENSE file.

import collections
import logging
import threading
import time

from utils import auth_server

import file_reader


class AuthSystemError(Exception):
  """Fatal errors raised by AuthSystem class."""


# Parsed value of JSON at path specified by --auth-params-file task_runner arg.
AuthParams = collections.namedtuple('AuthParams', [
  # Dict with HTTP headers to use when calling Swarming backend (specifically).
  # They identify the bot to the Swarming backend. Ultimately generated by
  # 'get_authentication_headers' in bot_config.py.
  'swarming_http_headers',

  # Unix timestamp of when swarming_http_headers expire, or 0 if unknown.
  'swarming_http_headers_exp',

  # Indicates the service account to use for internal bot processes. One of:
  #   - 'none' to not use authentication at all.
  #   - 'bot' to use whatever bot is using to authenticate itself to Swarming.
  #   - <email> to get tokens through API calls to Swarming.
  'system_service_account',

  # Indicates the service account the task runs as. Same range of values as for
  # 'system_service_account'.
  #
  # It is distinct from 'system_service_account' to allow user-supplied payloads
  # to use a service account also supplied by the user (and not the one used
  # internally by the bot).
  'task_service_account',
])


def prepare_auth_params_json(bot, manifest):
  """Returns a dict to put into JSON file passed to task_runner.

  This JSON file contains various tokens and configuration parameters that allow
  task_runner to make HTTP calls authenticated by bot's own credentials.

  The file is managed by bot_main.py (main Swarming bot process) and consumed by
  task_runner.py.

  It lives it the task work directory.

  Args:
    bot: instance of bot.Bot.
    manifest: dict with the task manifest, as generated by the backend in /poll.
  """
  def account(acc_id):
    acc = (manifest.get('service_accounts') or {}).get(acc_id) or {}
    return acc.get('service_account') or 'none'
  return {
    'swarming_http_headers': bot.remote.get_authentication_headers(),
    'swarming_http_headers_exp': bot.remote.authentication_headers_expiration,
    'system_service_account': account('system'),
    'task_service_account': account('task'),
  }


def process_auth_params_json(val):
  """Takes a dict loaded from auth params JSON file and validates it.

  Args:
    val: decoded JSON value read from auth params JSON file.

  Returns:
    AuthParams tuple.

  Raises:
    ValueError if val has invalid format.
  """
  if not isinstance(val, dict):
    raise ValueError('Expecting dict, got %r' % (val,))

  headers = val.get('swarming_http_headers') or {}
  if not isinstance(headers, dict):
    raise ValueError(
        'Expecting "swarming_http_headers" to be dict, got %r' % (headers,))

  exp = val.get('swarming_http_headers_exp') or 0
  if not isinstance(exp, (int, long)):
    raise ValueError(
        'Expecting "swarming_http_headers_exp" to be int, got %r' % (exp,))

  # The headers must be ASCII for sure, so don't bother with picking the
  # correct unicode encoding, default would work. If not, it'll raise
  # UnicodeEncodeError, which is subclass of ValueError.
  headers = {str(k): str(v) for k, v in headers.iteritems()}

  def read_account(key):
    acc = val.get(key) or 'none'
    if not isinstance(acc, basestring):
      raise ValueError('Expecting "%s" to be a string, got %r' % (key, acc))
    return str(acc)

  return AuthParams(
      swarming_http_headers=headers,
      swarming_http_headers_exp=exp,
      system_service_account=read_account('system_service_account'),
      task_service_account=read_account('task_service_account'))


class AuthSystem(object):
  """Authentication subsystem used by task_runner.

  Contains two threads:
    * One thread periodically rereads the file with bots own authentication
      information (auth_params_file). This file is generated by bot_main.
    * Another thread hosts local HTTP server that servers authentication tokens
      to local processes. This is enabled only if the task is running in a
      context of some service account (as specified by 'service_account_token'
      parameter supplied when the task was created).

  The local HTTP server exposes /rpc/LuciLocalAuthService.GetOAuthToken
  endpoint that the processes running inside Swarming tasks can use to request
  an OAuth access token associated with the task.

  They can discover the port to connect to by looking at LUCI_CONTEXT
  environment variable. This variables is only set if the task is running in
  the context of some service account.
  """

  def __init__(self, auth_params_file):
    self._auth_params_file = auth_params_file
    self._auth_params_reader = None
    self._local_server = None
    self._lock = threading.Lock()
    self._remote_client = None

  def set_remote_client(self, remote_client):
    """Sets an RPC client to use when calling Swarming.

    Note that there can be a circular dependency between the RPC client and
    the auth system (the client may be using AuthSystem's get_bot_headers).

    That's the reason we allow it to be set after 'start'.

    Args:
      remote_client: instance of remote_client.RemoteClient.
    """
    with self._lock:
      self._remote_client = remote_client

  def start(self):
    """Grabs initial bot auth headers and starts all auth related threads.

    If the task is configured to use service accounts (based on data in
    'auth_params_file'), launches the local auth service and returns a dict that
    contains its parameters. It can be placed into LUCI_CONTEXT['local_auth']
    slot.

    By default LUCI subprocesses will be using "task" service account (or none
    at all, it the task has no associated service account). Internal Swarming
    processes (like run_isolated.py) can switch to using "system" account.

    If task is not using service accounts, returns None (meaning, there's no
    need to setup LUCI_CONTEXT['local_auth'] at all).

    Format of the returned dict:
    {
      'rpc_port': <int with port number>,
      'secret': <str with a random string to send with RPCs>,
      'accounts': [{'id': <str>}, ...],
      'default_account_id': <str> or None
    }

    Raises:
      AuthSystemError on fatal errors.
    """
    assert not self._auth_params_reader, 'already running'
    try:
      # Read headers more often than bot_main writes them (which is 15 sec), to
      # reduce maximum possible latency between header updates and reads.
      #
      # TODO(vadimsh): Replace this with real IPC, like local sockets.
      reader = file_reader.FileReaderThread(
          self._auth_params_file, interval_sec=10)
      reader.start()
    except file_reader.FatalReadError as e:
      raise AuthSystemError('Cannot start FileReaderThread: %s' % e)

    # Initial validation.
    try:
      params = process_auth_params_json(reader.last_value)
    except ValueError as e:
      reader.stop()
      raise AuthSystemError('Cannot parse bot_auth_params.json: %s' % e)

    logging.info('Using following service accounts:')
    logging.info('  system: %s', params.system_service_account)
    logging.info('  task:   %s', params.task_service_account)

    # Expose all defined accounts (if any) to subprocesses via LUCI_CONTEXT.
    #
    # Use 'task' account as default for everything. Internal Swarming processes
    # will pro-actively switch to 'system'.
    #
    # If 'task' is not defined, then do not set default account at all! It means
    # processes will use non-authenticated calls by default (which is precisely
    # the meaning of un-set task account).
    default_account_id = None
    available_accounts = []
    if params.system_service_account != 'none':
      available_accounts.append('system')
    if params.task_service_account != 'none':
      default_account_id = 'task'
      available_accounts.append('task')

    # If using service accounts, launch local HTTP server that serves tokens
    # (let OS assign the port).
    server = None
    local_auth_context = None
    if available_accounts:
      server = auth_server.LocalAuthServer()
      local_auth_context = server.start(
          token_provider=self,
          accounts=available_accounts,
          default_account_id=default_account_id)

    # Good to go.
    with self._lock:
      self._auth_params_reader = reader
      self._local_server = server
    return local_auth_context

  def stop(self):
    """Shuts down all the threads if they are running."""
    with self._lock:
      reader, self._auth_params_reader = self._auth_params_reader, None
      server, self._local_server = self._local_server, None
    if server:
      server.stop()
    if reader:
      reader.stop()

  def get_bot_headers(self):
    """HTTP headers that contain bots own credentials and their expiration time.

    Such headers can be sent to Swarming server's /bot/* API. Must be used only
    after 'start' and before 'stop'.

    Returns:
      Tuple (dict with headers, expiration timestamp or 0 if not known).

    Raises:
      AuthSystemError if auth_params_file is suddenly no longer valid.
    """
    with self._lock:
      assert self._auth_params_reader, '"start" was not called'
      raw_val = self._auth_params_reader.last_value
    try:
      val = process_auth_params_json(raw_val)
      return val.swarming_http_headers, val.swarming_http_headers_exp
    except ValueError as e:
      raise AuthSystemError('Cannot parse bot_auth_params.json: %s' % e)

  def generate_token(self, account_id, scopes):
    """Generates a new access token with given scopes.

    Called by LocalAuthServer from some internal thread whenever new token is
    needed. It happens infrequently, approximately once per hour per combination
    of scopes (when the previously cached token expires).

    See TokenProvider for more details.

    Returns:
      AccessToken.

    Raises:
      RPCError, TokenError, AuthSystemError.
    """
    # Grab AuthParams supplied by the main bot process.
    with self._lock:
      if not self._auth_params_reader:
        raise auth_server.RPCError(503, 'Stopped already.')
      val = self._auth_params_reader.last_value
      rpc_client = self._remote_client
    params = process_auth_params_json(val)

    # Note: 'account_id' here is "task" or "system", it's checked below.
    logging.info('Getting %r token, scopes %r', account_id, scopes)

    # Grab service account email (or 'none'/'bot' placeholders) of requested
    # logical account. This is part of the task manifest.
    service_account = None
    if account_id == 'task':
      service_account = params.task_service_account
    elif account_id == 'system':
      service_account = params.system_service_account
    else:
      raise auth_server.RPCError(404, 'Unknown account %r' % account_id)

    # Note: correctly behaving clients aren't supposed to hit this, since they
    # should use only accounts specified in 'accounts' section of LUCI_CONTEXT.
    if service_account == 'none':
      raise auth_server.TokenError(
          1, 'The task has no %r account associated with it' % account_id)

    if service_account == 'bot':
      # This works only for bots that use OAuth for authentication (e.g. GCE
      # bots). It will raise TokenError if the bot is not using OAuth.
      tok = self._grab_bot_oauth_token(params)
    else:
      # Ask Swarming server to generate a new token for us.
      if not rpc_client:
        raise auth_server.RPCError(500, 'No RPC client, can\'t fetch token')
      tok = self._grab_oauth_token_via_rpc(rpc_client, account_id, scopes)

    logging.info(
        'Got %r token (belongs to %r), expires in %d sec',
        account_id, service_account, tok.expiry - time.time())
    return tok

  def _grab_bot_oauth_token(self, auth_params):
    # Piggyback on the bot own credentials. This works only for bots that use
    # OAuth for authentication (e.g. GCE bots). Also it totally ignores scopes.
    # It relies on bot_main to keep the bot OAuth token sufficiently fresh.
    # See remote_client.AUTH_HEADERS_EXPIRATION_SEC.
    bot_auth_hdr = auth_params.swarming_http_headers.get('Authorization') or ''
    if not bot_auth_hdr.startswith('Bearer '):
      raise auth_server.TokenError(2, 'The bot is not using OAuth')
    tok = bot_auth_hdr[len('Bearer '):]

    # Default to some safe small expiration in case bot_main doesn't report it
    # to us. This may happen if get_authentication_header bot hook is not
    # reporting expiration time.
    exp = auth_params.swarming_http_headers_exp or (time.time() + 4*60)

    # TODO(vadimsh): For GCE bots specifically we can pass a list of OAuth
    # scopes granted to the GCE token and verify it contains all the requested
    # scopes.
    return auth_server.AccessToken(tok, exp)

  def _grab_oauth_token_via_rpc(self, _rpc_client, _account_id, _scopes):
    # TODO(vadimsh): Send a request to /swarming/api/v1/bot/oauth_token using
    # given RPC client.
    raise auth_server.TokenError(3, 'Not implemented yet')
