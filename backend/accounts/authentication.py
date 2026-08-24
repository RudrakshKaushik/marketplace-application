from django.contrib.auth import get_user_model
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token

from backend.cache_utils import cache_delete, cache_delete_many, cache_get, cache_set

User = get_user_model()
TOKEN_USER_CACHE_TTL = 120


class CachedTokenAuthentication(TokenAuthentication):
    """
    Cache authenticated users briefly to avoid a Neon round-trip on every request.
    """

    def authenticate_credentials(self, key):
        cache_key = f"auth:token-user:{key}"
        cached_user = cache_get(cache_key)
        if cached_user is not None:
            if cached_user.is_active:
                return cached_user, key
            cache_delete(cache_key)

        user, token = super().authenticate_credentials(key)
        cache_set(cache_key, user, TOKEN_USER_CACHE_TTL)
        return user, token


def invalidate_token_user_cache(user_id: int) -> None:
    tokens = Token.objects.filter(user_id=user_id).values_list("key", flat=True)
    cache_delete_many([f"auth:token-user:{key}" for key in tokens])
