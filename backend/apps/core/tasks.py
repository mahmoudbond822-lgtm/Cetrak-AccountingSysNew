from config.celery import app as celery_app


@celery_app.task(name="core.ping")
def ping(message=None):
    """Infrastructure proof: exercises broker -> worker -> result backend."""
    return {"task_id": ping.request.id, "message": message}