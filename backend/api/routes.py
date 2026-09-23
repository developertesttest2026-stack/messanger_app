from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import SQLModel,select
from sqlalchemy.ext.asyncio import AsyncSession
from api.database import get_session
from api.auth import verify_code, create_access_token, get_current_user
from api.models import User, LoginSession
import uuid
from datetime import datetime,timedelta,timezone

router = APIRouter()


class CreateSessionResponse(SQLModel):
    session_token: str
    bot_url: str
    expires_in: int

class VerifyCodeRequest(SQLModel):
    session_token: str
    code: str

class TokenResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

@router.post("/auth/create-session", response_model=CreateSessionResponse)
async def create_session(session: AsyncSession = Depends(get_session)):
    
    session_token = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(hours=3,minutes=10)

    login_session = LoginSession(
        session_token=session_token,
        expires_at=expires_at,
        status="pending"
    )
    session.add(login_session)
    await session.commit()

    # URL для deep link в бота
    from api.database import settings
    bot_url = f"https://t.me/{settings.BOT_USERNAME}?start={session_token}"

    return CreateSessionResponse(
        session_token=session_token,
        bot_url=bot_url,
        expires_in=600
    )
@router.post("/auth/verify", response_model=TokenResponse)
async def verify_code_endpoint(req: VerifyCodeRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(LoginSession).where(
            LoginSession.session_token == req.session_token,
            LoginSession.status == "code_sent"
        )
    )
    login_session = result.scalar_one_or_none()

    if not login_session:
        raise HTTPException(status_code=400, detail="Сессия не найдена или уже использована")

    if login_session.expires_at < datetime.now(timezone.utc)+timedelta(hours=3):
        raise HTTPException(status_code=400, detail="Сессия истекла")

    if login_session.code != req.code:
        raise HTTPException(status_code=400, detail="Неверный код")

    # Помечаем сессию как проверенную
    login_session.status = "verified"
    session.add(login_session)
    await session.commit()

    # Получаем пользователя
    result = await session.execute(
        select(User).where(User.telegram_id == login_session.telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    token = create_access_token({"sub": user.telegram_id})
    return TokenResponse(
        access_token=token,
        user={
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "full_name": user.full_name,
        }
    )

@router.get("/profile")
async def get_profile(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "full_name": user.full_name,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
