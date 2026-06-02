"""Session cookie signing and verification using itsdangerous.

The session cookie contains only the user_id. On each request,
the server loads the full ClientUser from MongoDB — so onboarding_complete
and client_id are always fresh (no stale data in the cookie).
"""

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import settings

_serializer = URLSafeTimedSerializer(settings.session_secret_key)

COOKIE_NAME = "session"
COOKIE_MAX_AGE = settings.session_max_age_days * 86400  # seconds


def sign_session(user_id: str) -> str:
    """Create a signed session cookie value containing user_id."""
    return _serializer.dumps({"user_id": user_id})


def verify_session(cookie_value: str) -> str | None:
    """Verify and decode session cookie. Returns user_id or None."""
    try:
        data = _serializer.loads(cookie_value, max_age=COOKIE_MAX_AGE)
        return data.get("user_id")
    except (BadSignature, SignatureExpired):
        return None
