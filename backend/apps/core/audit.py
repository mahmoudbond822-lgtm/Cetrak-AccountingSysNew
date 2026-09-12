import datetime
import decimal
import threading
import uuid

from apps.core.models import AuditLog

_SENSITIVE_KEYS = {
    "password",
    "refresh",
    "access",
    "token",
    "secret",
    "authorization",
    "api_key",
    "session",
}

_request_context = threading.local()


def set_request_context(*, actor_id=None, tenant_id=None, metadata=None):
    _request_context.value = {
        "actor_id": actor_id,
        "tenant_id": tenant_id,
        "metadata": metadata or {},
    }


def clear_request_context():
    _request_context.value = None


def get_request_context():
    return getattr(_request_context, "value", None)


def _jsonable(value):
    if isinstance(value, dict):
        return {key: _jsonable(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    return value


def _is_sensitive_key(key):
    lowered = str(key).lower()
    return any(term in lowered for term in _SENSITIVE_KEYS)


def _sanitize(value):
    """Recursively strip sensitive keys and normalize JSON-serializable values."""
    if isinstance(value, dict):
        return {
            _jsonable(key): _sanitize(val)
            for key, val in value.items()
            if not _is_sensitive_key(key)
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    return _jsonable(value)


class AuditService:
    """Thin helper used exclusively from the service layer to write audit rows."""

    @staticmethod
    def record(*, action, tenant_id=None, target=None, actor=None,
               before=None, after=None, metadata=None):
        from apps.accounts.models import User
        from apps.core.models import Tenant

        context = get_request_context() or {}
        actor_id = str(actor.pk) if actor is not None else context.get("actor_id")
        tenant_pk = tenant_id if tenant_id is not None else context.get("tenant_id")

        if actor_id is not None and not User.objects.filter(pk=actor_id).exists():
            actor_id = None
        if tenant_pk is not None and not Tenant.objects.filter(pk=tenant_pk).exists():
            tenant_pk = None

        target_type = ""
        target_id = ""
        if target is not None:
            target_type = f"{target._meta.app_label}.{target._meta.model_name}"
            target_id = str(target.pk)

        if metadata is None:
            metadata = context.get("metadata", {})

        AuditLog.objects.create(
            tenant_id=tenant_pk,
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            before_data=_sanitize(before or {}),
            after_data=_sanitize(after or {}),
            metadata=_sanitize(metadata or {}),
        )
        return None