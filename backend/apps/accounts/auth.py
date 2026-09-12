from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken

from apps.accounts.models import BlacklistedToken, User
from apps.core.audit import clear_request_context, set_request_context


class BlacklistCheckingJWTAuth(JWTAuthentication):
    def get_validated_token(self, raw_token):
        validated_token = super().get_validated_token(raw_token)
        jti = validated_token.get("jti")
        if jti and BlacklistedToken.objects.filter(jti=jti).exists():
            raise InvalidToken("Token has been blacklisted.")
        return validated_token

    def authenticate(self, request):
        clear_request_context()
        result = super().authenticate(request)
        if result is not None:
            user, validated_token = result
            if getattr(user, "status", None) != User.Status.ACTIVE:
                raise AuthenticationFailed(
                    "Account has been disabled. Contact your administrator."
                )
            set_request_context(
                actor_id=str(user.pk),
                tenant_id=validated_token.get("tenant_id"),
                metadata={
                    "path": request.path,
                    "method": request.method,
                    "ip": request.META.get("REMOTE_ADDR"),
                    "user_agent": request.META.get("HTTP_USER_AGENT") or None,
                },
            )
        return result