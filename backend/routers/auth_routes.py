from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import crud, schemas, models
from ..database import get_db
from ..auth import create_access_token, get_current_user
from ..email_utils import send_otp_email, smtp_configured

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.RegisterResponse, status_code=201)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_username(db, user.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    if crud.get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    # only one admin (made in main.py), sign-up is always a passenger
    # TODO minimum password length, it accepts "1" right now
    user.role = "user"
    db_user = crud.create_user(db, user)  # unverified by default
    otp = crud.set_otp(db, db_user)
    sent = send_otp_email(db_user.email, otp)

    return schemas.RegisterResponse(
        message="Account created. Enter the OTP sent to your email to verify.",
        email=db_user.email,
        email_sent=sent,
        dev_otp=None if smtp_configured() else otp,
    )


@router.post("/verify-otp")
def verify_otp(data: schemas.OTPVerify, db: Session = Depends(get_db)):
    # TODO limit wrong guesses, 6 digits can be brute forced
    user = crud.get_user_by_email(db, data.email)
    if not user:
        raise HTTPException(status_code=404, detail="No account with that email")

    ok, message = crud.verify_otp(db, user, data.otp)
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message, "verified": True}


@router.post("/resend-otp")
def resend_otp(data: schemas.EmailOnly, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, data.email)
    if not user:
        raise HTTPException(status_code=404, detail="No account with that email")
    if user.is_verified:
        return {"message": "Email already verified. You can log in."}

    otp = crud.set_otp(db, user)
    sent = send_otp_email(user.email, otp)
    return {
        "message": "A new OTP has been sent.",
        "email_sent": sent,
        "dev_otp": None if smtp_configured() else otp,
    }


@router.post("/forgot-password")
def forgot_password(data: schemas.EmailOnly, db: Session = Depends(get_db)):
    """Send a reset OTP to the account's email."""
    user = crud.get_user_by_email(db, data.email)
    if not user:
        raise HTTPException(status_code=404, detail="No account with that email")

    otp = crud.set_otp(db, user)
    sent = send_otp_email(user.email, otp)
    return {
        "message": "A password-reset OTP has been sent to your email.",
        "email_sent": sent,
        "dev_otp": None if smtp_configured() else otp,
    }


@router.post("/reset-password")
def reset_password(data: schemas.ResetPassword, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, data.email)
    if not user:
        raise HTTPException(status_code=404, detail="No account with that email")

    ok, message = crud.reset_password(db, user, data.otp, data.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}


@router.post("/login", response_model=schemas.Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2-compatible login (username + password form fields)."""
    user = crud.authenticate_user(db, form.username, form.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify the OTP sent to your email.",
        )
    token = create_access_token({"sub": user.username, "role": user.role})
    return schemas.Token(
        access_token=token,
        token_type="bearer",
        role=user.role,
        username=user.username,
    )


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user
