import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("CETRAK_CELERY_INTEGRATION") != "1",
    reason="Real broker/worker round-trip only runs with CETRAK_CELERY_INTEGRATION=1 "
    "(e.g. `docker compose --profile worker up`).",
)


@pytest.fixture
def real_celery():
    from config.celery import app

    always_eager = app.conf.task_always_eager
    props = app.conf.task_eager_propagates
    app.conf.task_always_eager = False
    app.conf.task_eager_propagates = False
    try:
        yield app
    finally:
        app.conf.task_always_eager = always_eager
        app.conf.task_eager_propagates = props


def test_real_broker_and_worker_roundtrip(real_celery):
    from apps.core.tasks import ping

    inspector = real_celery.control.inspect(timeout=5)
    try:
        workers = inspector.ping()
    except Exception:
        workers = None
    assert workers, "No Celery worker reachable on the configured broker."

    value = ping.apply_async(kwargs={"message": "roundtrip"}).get(timeout=15)
    assert value["message"] == "roundtrip"
    assert value["task_id"]