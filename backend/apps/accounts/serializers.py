from rest_framework import serializers
from apps.accounts.models import User, Membership, Invitation


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    company_name = serializers.CharField(max_length=255)
    invitation_token = serializers.CharField(required=False, write_only=True)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    remember_me = serializers.BooleanField(default=False, required=False)


class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "display_name", "status"]


class InvitationSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = Invitation
        fields = ["id", "email", "role", "expires_at", "status"]

    def get_status(self, obj):
        if obj.is_accepted():
            return "accepted"
        if obj.is_expired():
            return "expired"
        return "pending"


class InvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=Invitation.Role.choices)


class MemberSerializer(serializers.Serializer):
    user_id = serializers.UUIDField(source="user.id")
    email = serializers.EmailField(source="user.email")
    display_name = serializers.CharField(source="user.display_name", allow_null=True)
    role = serializers.CharField()
    status = serializers.CharField(source="user.status")
    joined_at = serializers.DateTimeField(source="created_at")


class RoleChangeSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Membership.Role.choices)
