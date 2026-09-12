import datetime as dt_mod

from django.conf import settings
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserSerializer,
    InvitationSerializer,
    InvitationCreateSerializer,
    MemberSerializer,
    RoleChangeSerializer,
    MemberStatusSerializer,
)
from apps.accounts.services import AuthService, InvitationService, TeamService
from apps.accounts.models import BlacklistedToken, Membership, User
from apps.accounts.permissions import IsAdminUser
from apps.accounts.cookies import (
    csrf_invalid,
    set_csrf_cookie,
    set_refresh_cookie,
    delete_refresh_cookie,
)
from apps.accounts.services import _email_key
from apps.core.models import Tenant
from apps.core.audit import AuditService


def _mint_refresh(user_id, tenant_id=None, remember_me=False):
    lifetime = (
        settings.SIMPLE_JWT.get("REFRESH_TOKEN_LIFETIME_REMEMBER_ME", dt_mod.timedelta(days=30))
        if remember_me
        else settings.SIMPLE_JWT.get("REFRESH_TOKEN_LIFETIME", dt_mod.timedelta(days=7))
    )
    refresh = RefreshToken()
    refresh.set_exp(lifetime=lifetime)
    refresh["user_id"] = str(user_id)
    if tenant_id:
        refresh["tenant_id"] = str(tenant_id)
    return refresh


def _remember_me_from_token(token):
    issued_at = token.get("iat")
    expires_at = token.get("exp")
    if not issued_at or not expires_at:
        return False
    lifetime = expires_at - issued_at
    return lifetime > 14 * 24 * 3600


def _blacklist(refresh):
    jti = refresh.get("jti")
    exp = refresh.get("exp")
    if jti and exp:
        BlacklistedToken.objects.get_or_create(
            jti=jti,
            defaults={
                "expires_at": dt_mod.datetime.fromtimestamp(exp, tz=dt_mod.timezone.utc)
            },
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    invitation_token = serializer.validated_data.get("invitation_token")
    company_name = serializer.validated_data.get("company_name")
    email = serializer.validated_data["email"]

    if invitation_token:
        if company_name:
            display_name = company_name
        else:
            display_name = None
        inv_service = InvitationService()
        invitation, error = inv_service.validate_token(invitation_token)
        if error:
            return Response({"invitation_token": [error]}, status=status.HTTP_400_BAD_REQUEST)
        if _email_key(email) != _email_key(invitation.email):
            return Response(
                {
                    "invitation_token": [
                        "This invitation is bound to a different email address. "
                        "Register with the email address it was sent to."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.db import IntegrityError

        try:
            user = User.objects.get(email=email)
            created = False
        except User.DoesNotExist:
            try:
                user = User.objects.create_user(
                    email=email,
                    password=serializer.validated_data["password"],
                    display_name=display_name,
                )
                created = True
            except IntegrityError:
                user = User.objects.get(email=email)
                created = False

        membership, error = inv_service.accept_invitation(invitation_token, user)
        if error:
            if created:
                User.objects.filter(id=user.id).delete()
            return Response({"invitation_token": [error]}, status=status.HTTP_400_BAD_REQUEST)

        refresh = _mint_refresh(user.id, tenant_id=membership.tenant.id)

        memberships_data = [
            {
                "id": str(m.tenant.id),
                "name": m.tenant.name,
                "role": m.role,
            }
            for m in Membership.objects.filter(user=user).select_related("tenant")
        ]

        active_tenant = {
            "id": str(membership.tenant.id),
            "name": membership.tenant.name,
            "role": membership.role,
        }

        response = Response(
            {
                "access": str(refresh.access_token),
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "display_name": user.display_name,
                    "status": user.status,
                },
                "tenants": memberships_data,
                "active_tenant": active_tenant,
            },
            status=status.HTTP_201_CREATED,
        )
        set_refresh_cookie(response, refresh)
        set_csrf_cookie(response, get_token(request))
        return response

    service = AuthService()
    try:
        result = service.register(
            email=email,
            password=serializer.validated_data["password"],
            company_name=serializer.validated_data["company_name"],
        )
    except ValueError as e:
        return Response({"email": [str(e)]}, status=status.HTTP_400_BAD_REQUEST)

    refresh_value = result.pop("refresh")
    refresh = RefreshToken(refresh_value)
    response = Response(result, status=status.HTTP_201_CREATED)
    set_refresh_cookie(response, refresh)
    set_csrf_cookie(response, get_token(request))
    return response


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    service = AuthService()
    result, error = service.login(
        email=serializer.validated_data["email"],
        password=serializer.validated_data["password"],
        remember_me=serializer.validated_data.get("remember_me", False),
    )
    if error:
        if "disabled" in error.lower():
            return Response({"detail": error}, status=status.HTTP_403_FORBIDDEN)
        return Response({"detail": error}, status=status.HTTP_401_UNAUTHORIZED)

    remember_me = serializer.validated_data.get("remember_me", False)
    refresh_value = result.pop("refresh")
    refresh = RefreshToken(refresh_value)

    response = Response(result)
    set_refresh_cookie(response, refresh, remember_me=remember_me)
    set_csrf_cookie(response, get_token(request))
    return response


@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_view(request):
    if csrf_invalid(request):
        return Response(
            {"detail": "CSRF verification failed."},
            status=status.HTTP_403_FORBIDDEN,
        )

    refresh_token = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
    if not refresh_token:
        return Response(
            {"detail": "Refresh token not provided."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        old_refresh = RefreshToken(refresh_token)
        jti = old_refresh.get("jti")
        if jti and BlacklistedToken.objects.filter(jti=jti).exists():
            raise Exception("Token blacklisted")

        user_id = old_refresh.get("user_id")
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                if user.status == User.Status.DISABLED:
                    return Response(
                        {"detail": "Account has been disabled. Contact your administrator."},
                        status=status.HTTP_403_FORBIDDEN,
                    )
            except User.DoesNotExist:
                raise Exception("User not found")

        _blacklist(old_refresh)

        new_refresh = _mint_refresh(
            old_refresh.get("user_id"),
            tenant_id=old_refresh.get("tenant_id"),
            remember_me=_remember_me_from_token(old_refresh),
        )

        response = Response({"access": str(new_refresh.access_token)})
        set_refresh_cookie(response, new_refresh, remember_me=_remember_me_from_token(old_refresh))
        return response
    except Exception:
        return Response(
            {"detail": "Invalid or expired refresh token."},
            status=status.HTTP_401_UNAUTHORIZED,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def logout_view(request):
    refresh_token = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
    if refresh_token:
        if csrf_invalid(request):
            return Response(
                {"detail": "CSRF verification failed."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            refresh = RefreshToken(refresh_token)
            _blacklist(refresh)
        except Exception:
            pass
    response = Response(status=status.HTTP_205_RESET_CONTENT)
    delete_refresh_cookie(response)
    return response


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsAdminUser])
def invitation_list_create_view(request):
    if request.method == "GET":
        invitations = InvitationService().list_pending(request.tenant_id)
        serializer = InvitationSerializer(invitations, many=True)
        return Response({"count": len(serializer.data), "results": serializer.data})

    serializer = InvitationCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    service = InvitationService()
    try:
        invitation = service.create_invitation(
            email=serializer.validated_data["email"],
            role=serializer.validated_data["role"],
            tenant_id=request.tenant_id,
        )
    except ValueError as e:
        return Response(
            {"email": [str(e)]}, status=status.HTTP_400_BAD_REQUEST
        )

    result = InvitationSerializer(invitation)
    return Response(result.data, status=status.HTTP_201_CREATED)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated, IsAdminUser])
def invitation_destroy_view(request, invitation_id):
    service = InvitationService()
    try:
        service.cancel_invitation(invitation_id, request.tenant_id)
    except ValueError:
        return Response(
            {"detail": "Invitation not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
def member_list_view(request):
    members = TeamService().list_members(request.tenant_id)
    serializer = MemberSerializer(members, many=True)
    return Response({"count": len(serializer.data), "results": serializer.data})


@api_view(["PATCH"])
@permission_classes([IsAuthenticated, IsAdminUser])
def member_status_update_view(request, user_id):
    serializer = MemberStatusSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        membership = TeamService().set_user_status(
            tenant_id=request.tenant_id,
            member_user_id=user_id,
            new_status=serializer.validated_data["status"],
            requesting_user_id=request.user.id,
        )
    except Membership.DoesNotExist:
        return Response(
            {"detail": "Member not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except ValueError as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    result = MemberSerializer(membership)
    return Response(result.data)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated, IsAdminUser])
def member_role_update_view(request, user_id):
    serializer = RoleChangeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        membership = TeamService().change_role(
            tenant_id=request.tenant_id,
            member_user_id=user_id,
            new_role=serializer.validated_data["role"],
            requesting_user_id=request.user.id,
        )
    except Membership.DoesNotExist:
        return Response(
            {"detail": "Member not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except ValueError as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    result = MemberSerializer(membership)
    return Response(result.data)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated, IsAdminUser])
def member_destroy_view(request, user_id):
    try:
        TeamService().remove_member(
            tenant_id=request.tenant_id,
            member_user_id=user_id,
            requesting_user_id=request.user.id,
        )
    except Membership.DoesNotExist:
        return Response(
            {"detail": "Member not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except ValueError as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def tenant_switch_view(request, tenant_id):
    try:
        membership = Membership.objects.select_related("tenant").get(
            user=request.user, tenant_id=tenant_id
        )
    except Membership.DoesNotExist:
        return Response(
            {"detail": "Tenant not found or no membership."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if membership.tenant.status != Tenant.Status.ACTIVE:
        return Response(
            {"detail": "Tenant is not active. Contact your administrator."},
            status=status.HTTP_403_FORBIDDEN,
        )

    old_jti = request.auth.get("jti") if request.auth else None
    old_exp = request.auth.get("exp") if request.auth else None
    if old_jti and old_exp:
        BlacklistedToken.objects.get_or_create(
            jti=old_jti,
            defaults={
                "expires_at": dt_mod.datetime.fromtimestamp(old_exp, tz=dt_mod.timezone.utc)
            },
        )

    from_tenant_id = request.auth.get("tenant_id") if request.auth else None

    refresh_cookie = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
    if refresh_cookie:
        try:
            _blacklist(RefreshToken(refresh_cookie))
        except Exception:
            pass

    refresh = _mint_refresh(request.user.id, tenant_id=str(tenant_id))

    AuditService.record(
        action="tenant.switch",
        tenant_id=tenant_id,
        actor=request.user,
        before={"from_tenant_id": from_tenant_id},
        after={
            "to_tenant_id": str(tenant_id),
            "to_tenant_name": membership.tenant.name,
            "role": membership.role,
        },
    )

    response = Response(
        {
            "access": str(refresh.access_token),
            "tenant": {
                "id": str(membership.tenant.id),
                "name": membership.tenant.name,
                "role": membership.role,
            },
        }
    )
    set_refresh_cookie(response, refresh)
    return response


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def me_view(request):
    if request.method == "GET":
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    serializer = UserSerializer(request.user, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save()
    return Response(serializer.data)