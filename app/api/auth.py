"""Auth routes — signup, login, logout, me, delete account.

Cookie-based sessions using itsdangerous signed cookies.
No JWT, no tokens in frontend — the browser manages the httpOnly cookie.
"""

import logging
from uuid import uuid4

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.db.models import ClientUser
from app.db.repositories.client_repo import ClientRepository
from app.db.repositories.user_repo import UserRepository
from app.utils.session import COOKIE_MAX_AGE, COOKIE_NAME, sign_session

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ── Request / Response schemas ──


class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    client_id: str
    onboarding_complete: bool


def _user_response(user: ClientUser) -> dict:
    return {
        "user": UserResponse(
            user_id=user.user_id,
            email=user.email,
            full_name=user.full_name,
            client_id=user.client_id,
            onboarding_complete=user.onboarding_complete,
        ).model_dump()
    }


def _set_session_cookie(response: Response, user_id: str):
    """Set the signed session cookie on the response."""
    response.set_cookie(
        key=COOKIE_NAME,
        value=sign_session(user_id),
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=False,  # Set True in production with HTTPS
        samesite="lax",
        path="/",
    )


# ── Endpoints ──


@auth_router.post("/signup")
async def signup(req: SignupRequest, response: Response):
    """Create a new account. Sets session cookie."""
    repo = UserRepository()

    # Check duplicate email
    existing = await repo.get_by_email(req.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    user = ClientUser(
        user_id=str(uuid4()),
        email=req.email.lower().strip(),
        hashed_password=hash_password(req.password),
        full_name=req.full_name.strip(),
    )

    await repo.create(user)
    _set_session_cookie(response, user.user_id)

    logger.info("User signed up: %s", user.email)
    return _user_response(user)


@auth_router.post("/login")
async def login(req: LoginRequest, response: Response):
    """Login with email + password. Sets session cookie."""
    repo = UserRepository()
    user = await repo.get_by_email(req.email)

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    _set_session_cookie(response, user.user_id)

    logger.info("User logged in: %s", user.email)
    return _user_response(user)


@auth_router.post("/logout")
async def logout(response: Response):
    """Clear session cookie."""
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"success": True}


@auth_router.get("/me")
async def get_me(user: ClientUser = Depends(get_current_user)):
    """Get current authenticated user."""
    return _user_response(user)


@auth_router.delete("/me")
async def delete_account(
    response: Response,
    user: ClientUser = Depends(get_current_user),
):
    """Delete user account + linked ClientConfig. Bookings are preserved."""
    user_repo = UserRepository()
    client_repo = ClientRepository()

    # Delete ClientConfig if onboarded
    if user.client_id:
        await client_repo.update_one(
            {"client_id": user.client_id},
            {"is_active": False},
        )
        logger.info("Client '%s' deactivated (account deleted)", user.client_id)

    # Delete user record
    await user_repo.delete_user(user.user_id)
    response.delete_cookie(key=COOKIE_NAME, path="/")

    logger.info("User deleted: %s", user.email)
    return {"success": True}
