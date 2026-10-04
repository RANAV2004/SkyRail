from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, default="user")
    access_level = Column(String, default="standard")
    registration_time = Column(DateTime, default=datetime.utcnow)

    # Email OTP verification
    is_verified = Column(Boolean, default=False)
    otp_code = Column(String, nullable=True)
    otp_expires = Column(DateTime, nullable=True)

    tickets = relationship(
        "Ticket", back_populates="owner", cascade="all, delete-orphan"
    )


class Train(Base):
    __tablename__ = "trains"

    train_number = Column(Integer, primary_key=True, index=True)
    train_name = Column(String, nullable=False)
    source = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    departure = Column(String, default="")
    arrival = Column(String, default="")
    total_seats = Column(Integer, default=120)
    available_seats = Column(Integer, default=120)
    fare = Column(Float, default=0.0)
    stops = Column(String, default="")  # "Delhi,Jaipur,Mumbai"
    duration_minutes = Column(Integer, nullable=True)

    @property
    def stop_list(self):
        return [s for s in (self.stops or "").split(",") if s] or [
            self.source,
            self.destination,
        ]


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    train_number = Column(Integer, ForeignKey("trains.train_number"), nullable=False)
    source = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    booking_date = Column(String, nullable=False)
    class_type = Column(String, default="Sleeper")
    status = Column(String, default="CONFIRMED")
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="tickets")


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    distance = Column(Float, nullable=False)
    estimated_time = Column(Float, nullable=False)
