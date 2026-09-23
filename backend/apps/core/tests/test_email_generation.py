import datetime as dt_mod

import pytest
from django.conf import settings
from django.utils import timezone

from apps.accounts.models import Invitation, User
from apps.core.mail import (
    build_invitation_message,
    invitation_action_url,
    redact_email,
)
from apps.core.models import Tenant


def _make_invitation(email="invited@example.com", tenant_name="Acme Inc", role="Accountant"):
    tenant = Tenant.objects.create(name=tenant_name)
    return Invitation.objects.create(
        email=email,
        role=role,
        token="inv-token-abc123",
        tenant_id=tenant.id,
        expires_at=timezone.now() + dt_mod.timedelta(days=7),
    )


class TestRedactEmail:
    @pytest.mark.parametrize("email,expected", [
        ("jane@example.com", "j**e@example.com"),
        ("ab@example.com", "a@example.com"),
        ("a@example.com", "a@example.com"),
        ("", "***"),
        ("not-an-email", "***"),
        ("user@sub.domain.com", "u**r@sub.domain.com"),
    ])
    def test_redacts_local_part_keeps_domain(self, email, expected):
        assert redact_email(email) == expected


class TestActionUrl:
    def test_uses_configured_frontend_url(self, monkeypatch):
        monkeypatch.setattr(settings, "FRONTEND_URL", "https://app.example.com")
        assert invitation_action_url("tok") == "https://app.example.com/register?token=tok"

    def test_strips_trailing_slash(self, monkeypatch):
        monkeypatch.setattr(settings, "FRONTEND_URL", "https://app.example.com/")
        assert invitation_action_url("tok") == "https://app.example.com/register?token=tok"


class TestBuildInvitationMessage:
    @pytest.mark.django_db
    def test_recipient_subject_and_alternatives(self):
        invitation = _make_invitation()
        message = build_invitation_message(invitation)
        assert message.to == ["invited@example.com"]
        assert message.subject == "You're invited to join Acme Inc on Cetrak"
        assert message.from_email == settings.DEFAULT_FROM_EMAIL
        assert len(message.alternatives) == 1
        assert message.alternatives[0][1] == "text/html"

    @pytest.mark.django_db
    def test_action_link_contains_token_and_frontend_url(self, monkeypatch):
        monkeypatch.setattr(settings, "FRONTEND_URL", "https://app.example.com")
        invitation = _make_invitation()
        message = build_invitation_message(invitation)
        assert "https://app.example.com/register?token=inv-token-abc123" in message.body
        assert "https://app.example.com/register?token=inv-token-abc123" in message.alternatives[0][0]

    @pytest.mark.django_db
    def test_html_escapes_user_controlled_tenant_name(self):
        invitation = _make_invitation(tenant_name="<script>alert(1)</script>")
        message = build_invitation_message(invitation)
        html = message.alternatives[0][0]
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html

    @pytest.mark.django_db
    def test_plain_text_does_not_contain_html(self):
        invitation = _make_invitation()
        message = build_invitation_message(invitation)
        assert "<html" not in message.body
        assert "<a href" not in message.body

    @pytest.mark.django_db
    def test_template_contains_role_expiry_and_tenant(self):
        invitation = _make_invitation(role="Manager")
        message = build_invitation_message(invitation)
        html = message.alternatives[0][0]
        assert "Acme Inc" in html
        assert "Manager" in html
        assert "expires" in html.lower()