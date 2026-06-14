from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.serializers import (
    RegisterSerializer,
    LoginSerializer,
    TokenRefreshSerializer,
    UserSerializer,
)
from apps.accounts.serializers import LogoutSerializer, InvitationSerializer, InvitationCreateSerializer, MemberSerializer, RoleChangeSerializer
from apps.accounts.services import AuthService, InvitationService, TeamService
from apps.accounts.models import BlacklistedToken, Membership, User
from apps.accounts.permissions import IsAdminUser


@api_view(["POST"])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    invitation_token = serializer.validated_data.get("invitation_token")

    if invitation_token:
        inv_service = InvitationService()
        invitation, error = inv_service.validate_token(invitation_token)
        if error:
            return Response({"invitation_token": [error]}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=serializer.validated_data["email"]).exists():
            user = User.objects.get(email=serializer.validated_data["email"])
            membership, error = inv_service.accept_invitation(invitation_token, user)
            if error:
                return Response({"invitation_token": [error]}, status=status.HTTP_400_BAD_REQUEST)
        else:
            user = User.objects.create_user(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
            )
            membership, error = inv_service.accept_invitation(invitation_token, user)
            if error:
                user.delete()
                return Response({"invitation_token": [error]}, status=status.HTTP_400_BAD_REQUEST)

        refresh = RefreshToken()
        refresh["user_id"] = str(user.id)
        refresh["tenant_id"] = str(membership.tenant.id)

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

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
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

    service = AuthService()
    try:
        result = service.register(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            company_name=serializer.validated_data["company_name"],
        )
    except ValueError as e:
        return Response({"email": [str(e)]}, status=status.HTTP_400_BAD_REQUEST)
    return Response(result, status=status.HTTP_201_CREATED)


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

    return Response(result)


@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_view(request):
    serializer = TokenRefreshSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        refresh = RefreshToken(serializer.validated_data["refresh"])
        jti = refresh.get("jti")
        if jti and BlacklistedToken.objects.filter(jti=jti).exists():
            raise Exception("Token blacklisted")
        return Response({"access": str(refresh.access_token)})
    except Exception:
        return Response(
            {"detail": "Invalid or expired refresh token."},
            status=status.HTTP_401_UNAUTHORIZED,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def logout_view(request):
    serializer = LogoutSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    service = AuthService()
    service.logout(serializer.validated_data["refresh"])
    return Response(status=status.HTTP_205_RESET_CONTENT)


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
    from rest_framework_simplejwt.tokens import RefreshToken

    from apps.accounts.models import Membership

    try:
        membership = Membership.objects.select_related("tenant").get(
            user=request.user, tenant_id=tenant_id
        )
    except Membership.DoesNotExist:
        return Response(
            {"detail": "Tenant not found or no membership."},
            status=status.HTTP_404_NOT_FOUND,
        )

    refresh = RefreshToken()
    refresh["user_id"] = str(request.user.id)
    refresh["tenant_id"] = str(tenant_id)

    return Response(
        {
            "access": str(refresh.access_token),
            "tenant": {
                "id": str(membership.tenant.id),
                "name": membership.tenant.name,
                "role": membership.role,
            },
        }
    )


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
