import logging
import os
from datetime import datetime, timedelta
from typing import Callable

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import database, google_device, models, schemas
from ..limiter import limiter

router = APIRouter()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def get_secret_key() -> str:
    secret = os.getenv("SECRET_KEY")
    if not secret:
        raise RuntimeError("SECRET_KEY must be set in the backend environment")
    return secret


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def get_password_hash(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        raise ValueError("Password must be at most 72 UTF-8 bytes")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = models.utcnow() + expires_delta
    else:
        expire = models.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, get_secret_key(), algorithm=ALGORITHM)


@router.post("/token", response_model=schemas.TokenResponse)
@limiter.limit("5/minute")
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db),
):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not user.is_active or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer", "user": user}


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not isinstance(username, str):
            raise credentials_exception
    except (JWTError, RuntimeError):
        raise credentials_exception

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not user.is_active:
        raise credentials_exception
    return user


async def get_current_user_ws(
    token: str,
    db: Session
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials"
    )
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not isinstance(username, str):
            raise credentials_exception
    except (JWTError, RuntimeError):
        raise credentials_exception

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not user.is_active:
        raise credentials_exception
    return user


def require_roles(*roles: str) -> Callable:
    def dependency(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return dependency


@router.get("/methods")
def auth_methods():
    """Which sign-in buttons the dashboard should draw.

    The TV has its own copy of this at /api/screens/auth-methods; they are deliberately
    separate because they answer about different OAuth clients. A deployment can perfectly
    well have the browser half configured and not the TV half, or the reverse.
    """
    return {"google": google_device.is_web_configured(), "password": True}


@router.post("/google", response_model=schemas.TokenResponse)
@limiter.limit("10/minute")
def sign_in_with_google(
    request: Request,
    body: schemas.GoogleWebSignInRequest,
    db: Session = Depends(database.get_db),
):
    """Sign in to the dashboard with a Google account.

    Google authenticates a person; it does not authorise them. The verified address must
    already belong to an OLRAC user, exactly as the TV flow requires -- otherwise anyone
    holding any Gmail address could sign in to somebody's workspace. This route therefore
    creates nothing.
    """
    if not google_device.is_web_configured():
        raise HTTPException(status_code=503, detail="Google sign-in is not enabled on this server")

    try:
        claims = google_device.exchange_code(body.code, body.redirect_uri)
    except google_device.GoogleError as error:
        logging.getLogger(__name__).warning("Google web exchange failed: %s", error)
        raise HTTPException(status_code=502, detail="Could not complete Google sign-in. Try again.")

    email = (claims.get("email") or "").strip().lower()
    if not email or not claims.get("email_verified"):
        # An unverified address proves nothing about who owns it.
        raise HTTPException(status_code=403, detail="That Google account has no verified email address.")

    # Matched on username OR email: workspaces created before this existed identify people
    # by a username that is usually their address, and requiring the columns to agree would
    # lock out every account already in the database.
    user = (
        db.query(models.User)
        .filter((func.lower(models.User.email) == email) | (func.lower(models.User.username) == email))
        .first()
    )
    if not user or not user.is_active:
        # Same message either way: never reveal which addresses have accounts here.
        raise HTTPException(
            status_code=403,
            detail="No active OLRAC account matches that Google address. Ask your workspace owner to add you.",
        )

    logging.getLogger(__name__).info("Google web sign-in for %s", user.username)
    return {
        "access_token": create_access_token(data={"sub": user.username}),
        "token_type": "bearer",
        "user": user,
    }


@router.get("/me", response_model=schemas.UserResponse)
def read_current_user(user: models.User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=schemas.UserResponse)
def update_current_user(
    patch: schemas.ProfileUpdate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Self-service profile edit, for the account menu.

    Separate from PUT /api/users/{id}, which is owner-gated because it can change role and
    is_active. Anyone may edit their own display name and email; nobody gets to change
    their own privileges here.
    """
    updates = patch.model_dump(exclude_unset=True)
    if "email" in updates and updates["email"] is not None:
        updates["email"] = str(updates["email"])
        clash = (
            db.query(models.User)
            .filter(models.User.email == updates["email"], models.User.id != user.id)
            .first()
        )
        if clash:
            raise HTTPException(status_code=409, detail="That email is already in use")

    for field, value in updates.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
def change_own_password(
    request: Request,
    payload: schemas.PasswordChange,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Change your own password.

    Requires the current password. PUT /api/users/{id} can also set a password but is
    owner-only and verifies nothing, so it is an admin reset, not a self-service change --
    without this route a non-owner could never rotate their own credentials, and a
    borrowed session could change the password of whoever was logged in.
    """
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=403, detail="Current password is incorrect")

    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail="New password must differ from the current one")

    user.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    return None


def get_or_create_default_organization(db: Session) -> models.Organization:
    organization = db.query(models.Organization).filter(models.Organization.slug == "default").first()
    if not organization:
        organization = models.Organization(name="Default Organization", slug="default")
        db.add(organization)
        db.flush()
    return organization


def ensure_initial_owner(db: Session) -> None:
    """Create the first real owner only when explicit bootstrap credentials are supplied."""
    username = os.getenv("INITIAL_ADMIN_USERNAME")
    password = os.getenv("INITIAL_ADMIN_PASSWORD")
    if not username or not password or db.query(models.User).count() > 0:
        return
    if len(password) < 8:
        raise RuntimeError("INITIAL_ADMIN_PASSWORD must be at least 8 characters")

    organization = get_or_create_default_organization(db)

    db.add(
        models.User(
            organization_id=organization.id,
            username=username,
            hashed_password=get_password_hash(password),
            role="owner",
            is_active=True,
        )
    )
    db.commit()
