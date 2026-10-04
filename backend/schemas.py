from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    username: str
    full_name: Optional[str] = None
    email: EmailStr
    password: str
    role: str = "user"


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    user_id: int
    username: str
    full_name: Optional[str] = None
    email: EmailStr
    role: str
    access_level: str
    registration_time: datetime

    class Config:
        from_attributes = True


class UserAdminOut(UserOut):

    password: str
    is_verified: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class RegisterResponse(BaseModel):
    message: str
    email: EmailStr
    email_sent: bool
    dev_otp: Optional[str] = None


class OTPVerify(BaseModel):
    email: EmailStr
    otp: str


class EmailOnly(BaseModel):
    email: EmailStr


class ResetPassword(BaseModel):
    email: EmailStr
    otp: str
    new_password: str


#Train 
class TrainBase(BaseModel):
    train_name: str
    source: str
    destination: str
    departure: str = ""
    arrival: str = ""
    total_seats: int = 120
    fare: float = 0.0


class TrainCreate(TrainBase):
    train_number: int


class TrainOut(TrainBase):
    train_number: int
    available_seats: int
    stop_list: List[str] = []
    duration_minutes: Optional[int] = None

    class Config:
        from_attributes = True


class TicketCreate(BaseModel):
    train_number: int
    source: str
    destination: str
    booking_date: str
    class_type: str = "Sleeper"

    @field_validator("booking_date")
    @classmethod
    def real_date(cls, v):
        try:
            return date.fromisoformat(v).isoformat()
        except ValueError:
            raise ValueError("booking_date must be a date like 2026-10-05")


class TicketReschedule(BaseModel):
    booking_date: str
    class_type: Optional[str] = None


class TicketOut(BaseModel):
    ticket_id: int
    user_id: int
    train_number: int
    source: str
    destination: str
    booking_date: str
    class_type: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class RouteRequest(BaseModel):
    source: str
    destination: str


class RouteHop(BaseModel):
    frm: str
    to: str
    distance: float


class RouteResult(BaseModel):
    source: str
    destination: str
    path: List[str]
    total_distance: float
    estimated_time: float
    hops: List[RouteHop]


class WeatherRouteRequest(BaseModel):
    source: str
    destination: str
    departure: Optional[datetime] = None  
    k: int = Field(4, ge=1, le=6)  


class AdminPasswordReset(BaseModel):
    new_password: str = Field(min_length=6)
