"""FastAPI dependencies for authentication."""

from fastapi import HTTPException, Request

from app.db.models import ClientUser
from app.db.repositories.user_repo import UserRepository
from app.utils.session import COOKIE_NAME, verify_session


async def get_current_user(request: Request) -> ClientUser:
    """Extract user from session cookie. Raises 401 if invalid."""
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = verify_session(cookie)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    repo = UserRepository()
    user = await repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user
