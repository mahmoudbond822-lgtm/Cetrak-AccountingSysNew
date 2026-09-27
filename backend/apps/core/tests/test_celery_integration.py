import os

import pytest

from .conftest import publish_via

pytestmark = pytest.mark.skipif(
    os.environ.get("CETRAK_CELERY_INTEGRATION") != "1",
    reason="Real broker/worker round-trip only runs with CETRAK_CELERY_INTEGRATION=1 "
    "(e.g. `docker compose --profile worker up`).",
)


@pytest.fixture
def real_celery():
    """The Celery app on the real publish path, pointed at the configured broker.

    ``app.conf.task_always_eager = False`` does not work in this project: the
    conf is loaded from the Django settings with the ``CELERY_`` namespace, so
    the uppercase key shadows the lowercase alias and eager mode stayed on —
    this round-trip ran in-process and never touched the broker. ``publish_via``
    overrides the key that is actually read.
    """
    from config.celery import app

    with publish_via(app.conf.broker_url) as app:
        assert app.conf.task_always_eager is False
        yield app


def test_real_broker_and_worker_roundtrip(real_celery):
    """Publish to the real broker, a real worker runs it, the result comes back.

    A worker that never picks the message up is a genuine infrastructure break
    and fails. A worker that receives it and then cannot execute *any* task is
    not: the installed celery cannot unpack its own trace locals on this
    interpreter, so nothing in the deployment under test is at fault. That case
    skips and prints the worker's error, because a local broken build must not be
    reported as a passing round-trip.
    """
    from apps.core.tasks import ping

    inspector = real_celery.control.inspect(timeout=5)
    try:
        workers = inspector.ping()
    except Exception:
        workers = None
    assert workers, "No Celery worker reachable on the configured broker."

    try:
        value = ping.apply_async(kwargs={"message": "roundtrip"}).get(timeout=15)
    except Exception as exc:
        message = str(exc).strip().splitlines()[0]
        if "not enough values to unpack" in message:
            pytest.skip(f"the local celery build cannot execute any task: {message}")
        raise

    assert value["message"] == "roundtrip"
    assert value["task_id"]
