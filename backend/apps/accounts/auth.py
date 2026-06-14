from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from apps.accounts.models import BlacklistedToken


class BlacklistCheckingJWTAuth(JWTAuthentication):
    def get_validated_token(self, raw_token):
        validated_token = super().get_validated_token(raw_token)
        jti = validated_token.get("jti")
        if jti and BlacklistedToken.objects.filter(jti=jti).exists():
            raise InvalidToken("Token has been blacklisted.")
        return validated_token
