"""Authentication domain service for user and access key management."""

import secrets
from typing import Optional, Tuple
from aether.apps.auth.models import AccessKey, User


class AuthService:
    """Service layer managing credentials and user lookup."""

    @staticmethod
    def get_access_key(access_key_id: str) -> Optional[AccessKey]:
        try:
            return AccessKey.objects.select_related("user").get(
                access_key_id=access_key_id, is_active=True
            )
        except AccessKey.DoesNotExist:
            return None

    @staticmethod
    def create_user_with_credentials(
        username: str, email: str, access_key_id: Optional[str] = None, secret_key: Optional[str] = None
    ) -> Tuple[User, AccessKey, str]:
        user, _ = User.objects.get_or_create(username=username, defaults={"email": email})
        ak_id = access_key_id or ("AKIA" + secrets.token_hex(8).upper())
        sk = secret_key or secrets.token_hex(20)

        access_key = AccessKey(
            user=user,
            access_key_id=ak_id,
        )
        access_key.set_secret_key(sk)
        access_key.save()
        return user, access_key, sk
