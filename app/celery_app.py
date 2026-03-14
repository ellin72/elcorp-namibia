"""Celery application factory."""

from celery import Celery

from app.config import config_by_name

_cfg = config_by_name.get("development")


def make_celery(app=None) -> Celery:
    celery = Celery(
        "elcorp",
        broker=_cfg.CELERY_BROKER_URL,
        backend=_cfg.CELERY_RESULT_BACKEND,
    )
    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_default_queue="default",
        task_queues={
            "default": {},
            "verification": {},
            "email": {},
        },
        beat_schedule={
            "check-pending-verifications": {
                "task": "app.workers.verification_worker.check_pending_verifications",
                "schedule": 300.0,  # every 5 minutes
            },
        },
    )

    if app is not None:
        celery.conf.update(
            broker_url=app.config["CELERY_BROKER_URL"],
            result_backend=app.config["CELERY_RESULT_BACKEND"],
        )

        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask

    return celery


celery_app = make_celery()
