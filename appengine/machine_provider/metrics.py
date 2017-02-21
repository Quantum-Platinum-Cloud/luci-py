# Copyright 2015 The LUCI Authors. All rights reserved.
# Use of this source code is governed under the Apache License, Version 2.0
# that can be found in the LICENSE file.

"""Metrics to track with ts_mon and event_mon."""

import gae_ts_mon


lease_requests_deduped = gae_ts_mon.CounterMetric(
    'machine_provider/lease_requests/deduped',
    'Number of lease requests deduplicated.',
    None)


lease_requests_expired = gae_ts_mon.CounterMetric(
    'machine_provider/lease_requests/expired',
    'Number of lease requests expired.',
    None)


lease_requests_fulfilled = gae_ts_mon.CounterMetric(
    'machine_provider/lease_requests/fulfilled',
    'Number of lease requests fulfilled.',
    None)


lease_requests_received = gae_ts_mon.CounterMetric(
    'machine_provider/lease_requests/received',
    'Number of lease requests received.',
    None)


pubsub_messages_sent = gae_ts_mon.CounterMetric(
    'machine_provider/pubsub_messages/sent',
    'Number of Pub/Sub messages sent.',
    [gae_ts_mon.StringField('target')])
