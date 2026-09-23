from sqlmodel import SQLModel, Field
from datetime import datetime,timezone,timedelta
from typing import Optional


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int = Field(unique=True, index=True, nullable=False)
    username: Optional[str] = Field(default=None)
    full_name: Optional[str] = Field(default=None)
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc)+timedelta(hours=3))


class LoginSession(SQLModel, table=True):
    __tablename__ = "login_sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_token: str = Field(unique=True, index=True, max_length=64)
    telegram_id: Optional[int] = Field(default=None, index=True)
    code: Optional[str] = Field(default=None, max_length=6)
    status: str = Field(default="pending", max_length=20)  # pending, code_sent, verified, expired
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc)+timedelta(hours=3))
  
    expires_at: datetime = Field(nullable=False)
