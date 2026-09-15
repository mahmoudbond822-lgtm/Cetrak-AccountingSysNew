import io, os, sys, uuid
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
import django
django.setup()
from rest_framework.test import APITestCase
from django.test import Client
from apps.core.models import Tenant

class Replay(APITestCase):
    def test_replay_create(self):
        t = Tenant.objects.create(name="Replay Tenant")
        c = Client(HTTP_AUTHORIZATION="Bearer x", HTTP_X_TENANT_ID=str(t.id))
        # real payload the modal sends (code absent)
        r = c.post("/api/v1/sales/customers/", {
            "name": "Replay Co",
            "email": "a@b.co",
            "phone": "123",
            "address": "addr",
            "tax_id": "T1",
        }, content_type="application/json")
        print("REPLAY", r.status_code, r.content.decode()[:200])
