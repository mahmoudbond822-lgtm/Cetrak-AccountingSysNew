import base64
import json

from django.urls import reverse


def login(client, email, password, remember_me=None):
    data = {"email": email, "password": password}
    if remember_me is not None:
        data["remember_me"] = remember_me
    return client.post(reverse("auth-login"), data, format="json")


def refresh_cookie_value(client):
    cookie = client.cookies.get("refresh_token")
    return cookie.value if cookie is not None else None


def csrf_headers(client):
    cookie = client.cookies.get("csrftoken")
    if cookie is None:
        return {}
    return {"HTTP_X_CSRFTOKEN": cookie.value}


def post_refresh(client):
    return client.post(reverse("auth-refresh"), {}, format="json", **csrf_headers(client))


def post_logout(client):
    return client.post(reverse("auth-logout"), {}, format="json", **csrf_headers(client))


def jwt_payload(token):
    payload = token.split(".")[1]
    padded = payload + "=" * (4 - len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))


def tenant_id_of(token):
    return jwt_payload(token).get("tenant_id")