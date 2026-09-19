import secrets
import smtplib
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    hash_password,
    password_hash,
    verify_password,
)
from app.models.password_reset import PasswordReset
from app.models.user import User
from app.schemas.auth import (
    PasswordResetComplete,
    PasswordResetRequest,
    PasswordResetVerify,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)


router = APIRouter(prefix="/api/auth", tags=["authentication"])


def _email_settings_configured() -> bool:
    return bool(
        settings.smtp_host
        and settings.smtp_from_email
        and settings.smtp_username
        and settings.smtp_password
    )


def _send_reset_email(recipient: str, otp: str) -> None:
    if not _email_settings_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password reset email delivery is not configured",
        )
    message = EmailMessage()
    message["Subject"] = "BuildSync password reset code"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(
        "Your BuildSync password reset code is "
        f"{otp}. It expires in {settings.password_reset_expire_minutes} minutes."
    )
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
            if settings.smtp_use_tls:
                client.starttls()
            client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password reset email delivery is unavailable",
        ) from exc


def _is_expired(expires_at: datetime, now: datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= now


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)) -> User:
    duplicate_fields = []
    if user_data.email is not None:
        duplicate_fields.append(User.email == user_data.email)
    if user_data.phone is not None:
        duplicate_fields.append(User.phone == user_data.phone)
    existing = db.scalar(select(User).where(or_(*duplicate_fields))) if duplicate_fields else None
    if existing:
        raise HTTPException(status_code=409, detail="Email or phone is already registered")

    user = User(
        full_name=user_data.full_name,
        email=str(user_data.email) if user_data.email else None,
        phone=user_data.phone,
        hashed_password=hash_password(user_data.password),
        role=user_data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(
        select(User).where(
            or_(User.email == credentials.identifier, User.phone == credentials.identifier)
        )
    )
    if user is None or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        user=UserResponse.model_validate(user),
    )


@router.post("/password-reset/request")
def request_password_reset(
    request: PasswordResetRequest, db: Session = Depends(get_db)
) -> dict[str, str]:
    if not _email_settings_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password reset email delivery is not configured",
        )
    email = str(request.email).lower()
    user = db.scalar(select(User).where(User.email == email, User.is_active.is_(True)))
    if user is None:
        return {"message": "If that account exists, a verification code was sent."}

    now = datetime.now(UTC)
    db.query(PasswordReset).filter(
        PasswordReset.user_id == user.id,
        PasswordReset.used_at.is_(None),
    ).update({"used_at": now})
    otp = f"{secrets.randbelow(1_000_000):06d}"
    reset = PasswordReset(
        user_id=user.id,
        otp_hash=hash_password(otp),
        expires_at=now + timedelta(minutes=settings.password_reset_expire_minutes),
        created_at=now,
    )
    db.add(reset)
    db.commit()
    try:
        _send_reset_email(email, otp)
    except HTTPException:
        db.delete(reset)
        db.commit()
        raise
    return {"message": "If that account exists, a verification code was sent."}


@router.post("/password-reset/verify")
def verify_password_reset(
    request: PasswordResetVerify, db: Session = Depends(get_db)
) -> dict[str, str]:
    email = str(request.email).lower()
    reset = db.scalar(
        select(PasswordReset)
        .join(User, User.id == PasswordReset.user_id)
        .where(
            User.email == email,
            PasswordReset.used_at.is_(None),
            PasswordReset.verified_at.is_(None),
        )
        .order_by(PasswordReset.created_at.desc())
    )
    now = datetime.now(UTC)
    if (
        reset is None
        or _is_expired(reset.expires_at, now)
        or not password_hash.verify(request.otp, reset.otp_hash)
    ):
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    reset.verified_at = now
    reset_token = secrets.token_urlsafe(32)
    reset.reset_token_hash = hash_password(reset_token)
    db.commit()
    return {"reset_token": reset_token}


@router.post("/password-reset/complete")
def complete_password_reset(
    request: PasswordResetComplete, db: Session = Depends(get_db)
) -> dict[str, str]:
    email = str(request.email).lower()
    reset = db.scalar(
        select(PasswordReset)
        .join(User, User.id == PasswordReset.user_id)
        .where(
            User.email == email,
            PasswordReset.used_at.is_(None),
            PasswordReset.verified_at.is_not(None),
        )
        .order_by(PasswordReset.created_at.desc())
    )
    now = datetime.now(UTC)
    if (
        reset is None
        or _is_expired(reset.expires_at, now)
        or reset.reset_token_hash is None
        or not password_hash.verify(request.reset_token, reset.reset_token_hash)
    ):
        raise HTTPException(status_code=400, detail="Invalid or expired password reset")
    user = db.get(User, reset.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid or expired password reset")
    user.hashed_password = hash_password(request.new_password)
    reset.used_at = now
    db.commit()
    return {"message": "Password updated successfully"}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
