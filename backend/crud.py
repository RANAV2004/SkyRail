import csv
import io
import random
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from . import models, schemas
from .auth import hash_password, verify_password

OTP_TTL_MINUTES = 10


def tickets_to_csv(tickets, username_by_id=None) -> str:
    """Serialize Ticket rows to CSV text (Ticket Management Module: store booking
    information in CSV, tracked by user ID)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "ticket_id",
            "user_id",
            "username",
            "train_number",
            "source",
            "destination",
            "booking_date",
            "class_type",
            "status",
            "created_at",
        ]
    )
    username_by_id = username_by_id or {}
    for t in tickets:
        writer.writerow(
            [
                t.ticket_id,
                t.user_id,
                username_by_id.get(t.user_id, ""),
                t.train_number,
                t.source,
                t.destination,
                t.booking_date,
                t.class_type,
                t.status,
                t.created_at.isoformat() if t.created_at else "",
            ]
        )
    return buffer.getvalue()


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(
    db: Session, user: schemas.UserCreate, auto_verify: bool = False
) -> models.User:
    db_user = models.User(
        username=user.username,
        full_name=(user.full_name or "").strip() or None,
        email=user.email,
        password=hash_password(user.password),
        role=user.role if user.role in ("user", "admin") else "user",
        access_level="full" if user.role == "admin" else "standard",
        registration_time=datetime.utcnow(),
        is_verified=auto_verify,  # default admin is pre-verified
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def set_otp(db: Session, user: models.User) -> str:
    """Generate a fresh 6-digit OTP for the user and store it with an expiry."""
    otp = f"{random.randint(0, 999999):06d}"
    user.otp_code = otp
    user.otp_expires = datetime.utcnow() + timedelta(minutes=OTP_TTL_MINUTES)
    db.commit()
    return otp


def reset_password(
    db: Session, user: models.User, otp: str, new_password: str
) -> tuple[bool, str]:
    """Validate the OTP and set a new password. Returns (ok, message)."""
    if not user.otp_code or not user.otp_expires:
        return False, "No OTP on record. Please request a reset code first."
    if datetime.utcnow() > user.otp_expires:
        return False, "OTP has expired. Please request a new code."
    if otp.strip() != user.otp_code:
        return False, "Incorrect OTP. Please try again."
    user.password = hash_password(new_password)
    user.is_verified = True  # proving email ownership also verifies it
    user.otp_code = None
    user.otp_expires = None
    db.commit()
    return True, "Password reset successfully. You can now log in."


def verify_otp(db: Session, user: models.User, otp: str) -> tuple[bool, str]:
    """Check an OTP. Returns (ok, message)."""
    if user.is_verified:
        return True, "Email already verified."
    if not user.otp_code or not user.otp_expires:
        return False, "No OTP on record. Please request a new code."
    if datetime.utcnow() > user.otp_expires:
        return False, "OTP has expired. Please request a new code."
    if otp.strip() != user.otp_code:
        return False, "Incorrect OTP. Please try again."
    user.is_verified = True
    user.otp_code = None
    user.otp_expires = None
    db.commit()
    return True, "Email verified successfully."


def authenticate_user(
    db: Session, username: str, password: str
) -> Optional[models.User]:
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.password):
        return None
    return user


def list_users(db: Session) -> List[models.User]:
    return db.query(models.User).order_by(models.User.registration_time.desc()).all()


def list_trains(db: Session) -> List[models.Train]:
    return db.query(models.Train).order_by(models.Train.train_number).all()


def get_train(db: Session, train_number: int) -> Optional[models.Train]:
    return (
        db.query(models.Train).filter(models.Train.train_number == train_number).first()
    )


def search_trains(db: Session, source: str, destination: str) -> List[models.Train]:
    q = db.query(models.Train)
    if source:
        q = q.filter(models.Train.source.ilike(source))
    if destination:
        q = q.filter(models.Train.destination.ilike(destination))
    return q.all()


def book_ticket(
    db: Session, user_id: int, ticket: schemas.TicketCreate
) -> models.Ticket:
    db_ticket = models.Ticket(
        user_id=user_id,
        train_number=ticket.train_number,
        source=ticket.source,
        destination=ticket.destination,
        booking_date=ticket.booking_date,
        class_type=ticket.class_type,
        status="CONFIRMED",
        created_at=datetime.utcnow(),
    )
    # Booking happens on IRCTC now saved trip.
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket


def list_tickets_for_user(db: Session, user_id: int) -> List[models.Ticket]:
    return (
        db.query(models.Ticket)
        .filter(models.Ticket.user_id == user_id)
        .order_by(models.Ticket.created_at.desc())
        .all()
    )


def list_all_tickets(db: Session) -> List[models.Ticket]:
    return db.query(models.Ticket).order_by(models.Ticket.created_at.desc()).all()


def get_ticket(db: Session, ticket_id: int) -> Optional[models.Ticket]:
    return db.query(models.Ticket).filter(models.Ticket.ticket_id == ticket_id).first()


def reschedule_ticket(
    db: Session, ticket: models.Ticket, data: schemas.TicketReschedule
) -> models.Ticket:
    ticket.booking_date = data.booking_date
    if data.class_type:
        ticket.class_type = data.class_type
    ticket.status = "CONFIRMED"
    db.commit()
    db.refresh(ticket)
    return ticket


def cancel_ticket(db: Session, ticket: models.Ticket) -> models.Ticket:
    ticket.status = "CANCELLED"
    db.commit()
    db.refresh(ticket)
    return ticket


def admin_set_password(
    db: Session, user: models.User, new_password: str
) -> models.User:
    user.password = hash_password(new_password)
    user.otp_code = None
    user.otp_expires = None
    db.commit()
    db.refresh(user)
    return user
