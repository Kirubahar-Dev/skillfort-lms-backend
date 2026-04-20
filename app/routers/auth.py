import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.models import EmailLog, PasswordResetToken, User
from app.services.mail_service import MailService
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.utils.config import get_settings
from app.utils.database import get_db
from app.utils.security import create_access_token, create_refresh_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()
limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("30/minute")
def login(request: Request, payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account has been deactivated. Please contact support.")

    access_token = create_access_token(subject=user.email, role=user.role)
    refresh_token = create_refresh_token(subject=user.email, role=user.role)
    response.set_cookie("refresh_token", refresh_token, httponly=True, secure=False, samesite="lax")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserOut(id=user.id, full_name=user.full_name, email=user.email, role=user.role),
    )


@router.post("/register")
@limiter.limit("5/minute")
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(full_name=payload.full_name, email=payload.email, password_hash=hash_password(payload.password), role="student")
    db.add(user)
    db.commit()
    mailer = MailService()
    result = {"status": "skipped", "reason": "mail disabled"}
    try:
        result = __import__("asyncio").run(
            mailer.send(payload.email, "Welcome to Skillfort LMS", "<p>Your account was created successfully.</p>")
        )
    except Exception:
        pass
    db.add(EmailLog(recipient=payload.email, subject="Welcome to Skillfort LMS", status=result.get("status", "unknown"), error=result.get("reason")))
    db.commit()
    return {"message": "Registration successful. Verification email queued."}


@router.post("/refresh")
def refresh_token(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    try:
        payload = jwt.decode(refresh_token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        email = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account has been deactivated.")

    access = create_access_token(subject=user.email, role=user.role)
    new_refresh = create_refresh_token(subject=user.email, role=user.role)
    response.set_cookie("refresh_token", new_refresh, httponly=True, secure=False, samesite="lax")
    return {"access_token": access, "refresh_token": new_refresh, "token_type": "bearer"}


@router.post("/forgot-password")
@limiter.limit("3/minute")
def forgot_password(request: Request, email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"message": "If your email exists, a reset link has been sent."}

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    db.add(PasswordResetToken(email=email, token=token, expires_at=expires_at, used=False))
    db.commit()

    reset_link = f"{settings.frontend_url}/reset-password?token={token}"
    mailer = MailService()
    result = {"status": "skipped", "reason": "mail disabled"}
    try:
        result = __import__("asyncio").run(
            mailer.send(email, "Reset your Skillfort password", f"<p>Reset link: <a href='{reset_link}'>{reset_link}</a></p>")
        )
    except Exception:
        pass
    db.add(EmailLog(recipient=email, subject="Reset your Skillfort password", status=result.get("status", "unknown"), error=result.get("reason")))
    db.commit()
    return {"message": "If your email exists, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    row = db.query(PasswordResetToken).filter(PasswordResetToken.token == token, PasswordResetToken.used == False).first()
    if not row or row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = db.query(User).filter(User.email == row.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(new_password)
    row.used = True
    db.commit()
    return {"message": "Password reset successful"}
