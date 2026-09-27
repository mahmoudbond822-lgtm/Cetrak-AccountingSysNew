"""Test support for driving the real (non-eager) Celery publish path (B1).

Celery configuration cannot be overridden the obvious way here. ``app.conf`` is
loaded from ``django.conf:settings`` with the ``CELERY_`` namespace, so the conf
map holds the *uppercase* Django keys, and ``_to_keys`` resolves a lookup to
``CELERY_TASK_ALWAYS_EAGER`` before ``task_always_eager``. Writing the lowercase
alias therefore lands in the map but is never read — the pre-existing
``real_celery`` fixture in ``test_celery_integration.py`` did exactly that and
left eager mode on, so its "real broker" round-trip ran in-process. The uppercase
key is what has to be overridden. ``broker_url``/``result_backend`` are
properties that read ``os.environ`` first, so the environment is the honest way
to move the broker.

A context manager rather than a fixture: the tests that need this are Django
``APITestCase``/``TestCase`` classes, and pytest cannot inject fixtures into
unittest test methods.
"""

import contextlib
import os

from config.celery import app as celery_app

# A host in the reserved .invalid TLD (RFC 2606): it can never resolve, so "the
# broker is unreachable" is a deterministic condition rather than a hopeful
# guess at a free port.
UNREACHABLE_BROKER = "redis://cetrak-broker.invalid:6379/0"

# Fail fast: kombu's production retry budget is measured in minutes and the
# result backend retries on its own, neither of which belongs in a test run.
#
# The two eager keys are spelled the Django way because those are the keys this
# project actually sets; the rest have no Django-namespaced counterpart here, so
# their plain Celery names are what gets read.
_FAST_FAILURE_CONF = {
    "CELERY_TASK_ALWAYS_EAGER": False,
    "CELERY_TASK_EAGER_PROPAGATES": False,
    "broker_connection_retry_on_startup": False,
    "broker_connection_max_retries": 0,
    "broker_connection_timeout": 1,
    "broker_transport_options": {
        "max_retries": 0,
        "socket_connect_timeout": 1,
        "socket_timeout": 1,
    },
    "task_publish_retry": False,
    "redis_socket_connect_timeout": 1,
    "redis_socket_timeout": 1,
    "result_backend_always_retry": False,
    "result_backend_max_retries": 0,
    "result_backend_transport_options": {
        "max_retries": 0,
        "socket_connect_timeout": 1,
        "socket_timeout": 1,
        # RedisBackend.retry_policy is a class-level default of 20 tries, one
        # second apart; only a nested retry_policy overrides it.
        "retry_policy": {
            "max_retries": 0,
            "interval_start": 0,
            "interval_step": 0,
            "interval_max": 0,
        },
    },
}

_BROKER_ENV_VARS = ("CELERY_BROKER_URL", "CELERY_RESULT_BACKEND")


def _reset_connections(app):
    """Drop the cached result backend and broker pool so the conf takes effect.

    Celery builds the result backend and the broker connection pool once and
    reuses them, so a conf change made mid-process would otherwise be ignored —
    including the retry budgets this module is trying to shrink. ``_backend`` is
    a property whose setter rejects ``None``, hence the two attributes behind it.
    """
    app._backend_cache = None
    app._local.backend = None
    app._pool = None
    try:
        app.__dict__["amqp"]._producer_pool = None
    except (AttributeError, KeyError):
        pass


@contextlib.contextmanager
def publish_via(broker_url, result_backend=None):
    """Publish through a real broker at *broker_url* for the duration of the block.

    Yields the Celery app with eager mode off. The conf, the environment, and the
    cached connections are all restored on exit.
    """
    saved_env = {name: os.environ.get(name) for name in _BROKER_ENV_VARS}
    saved_conf = dict(celery_app.conf.changes)
    os.environ["CELERY_BROKER_URL"] = broker_url
    os.environ["CELERY_RESULT_BACKEND"] = result_backend or broker_url
    celery_app.conf.update(_FAST_FAILURE_CONF)
    _reset_connections(celery_app)
    try:
        yield celery_app
    finally:
        celery_app.conf.changes.clear()
        celery_app.conf.changes.update(saved_conf)
        _reset_connections(celery_app)
        for name, value in saved_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
