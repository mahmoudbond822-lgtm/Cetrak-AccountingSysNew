from django.urls import path
from apps.accounts import views

urlpatterns = [
    path("auth/register/", views.register_view, name="auth-register"),
    path("auth/login/", views.login_view, name="auth-login"),
    path("auth/logout/", views.logout_view, name="auth-logout"),
    path("auth/refresh/", views.refresh_view, name="auth-refresh"),
    path("auth/me/", views.me_view, name="auth-me"),
    path("tenants/invitations/", views.invitation_list_create_view, name="tenant-invitations"),
    path("tenants/invitations/<uuid:invitation_id>/", views.invitation_destroy_view, name="tenant-invitation-detail"),
    path("tenants/members/", views.member_list_view, name="tenant-members"),
    path("tenants/members/<uuid:user_id>/role/", views.member_role_update_view, name="tenant-member-role"),
    path("tenants/members/<uuid:user_id>/", views.member_destroy_view, name="tenant-member-remove"),
    path("tenants/switch/<uuid:tenant_id>/", views.tenant_switch_view, name="tenant-switch"),
]
