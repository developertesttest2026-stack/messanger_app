from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, select
from api.models import ChatRoom, RoomMember, Message,User
from api.auth import get_current_user
from api.database import get_session

router = APIRouter(prefix="/rooms", tags=["rooms"])

@router.get("/")
async def get_rooms(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    statement = (
        select(ChatRoom)
        .join(RoomMember, RoomMember.room_id == ChatRoom.id)
        .where(RoomMember.user_id == user.telegram_id)
        .order_by(ChatRoom.created_at.desc())
    )
    result = await session.execute(statement)
    rooms = result.scalars().all()
    return [
        {
            "id": room.id,
            "name": room.name,
            "description": room.description,
            "created_by": room.created_by,
            "created_at": room.created_at.isoformat() if room.created_at else None,
        }
        for room in rooms
    ]

class CreateRoomRequest(SQLModel):
    name: str
    description: str | None = None


@router.post("/")
async def create_room(req: CreateRoomRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    room = ChatRoom(
        name=req.name,
        description=req.description,
        created_by=user.telegram_id,
    )
    session.add(room)
    await session.commit()
    await session.refresh(room)

    member = RoomMember(room_id=room.id, user_id=user.telegram_id)
    session.add(member)
    await session.commit()

    return {
        "id": room.id,
        "name": room.name,
        "description": room.description,
    }



@router.get("/{room_id}")
async def get_room(room_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    room = await session.get(ChatRoom, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")

    member = await session.execute(
        select(RoomMember).where(
            RoomMember.room_id == room_id,
            RoomMember.user_id == user.telegram_id,
        )
    )
    if not member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Вы не участник комнаты")

    return {
        "id": room.id,
        "name": room.name,
        "description": room.description,
    }


@router.get("/{room_id}/messages")
async def get_room_messages(room_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    room = await session.get(ChatRoom, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")

    result = await session.execute(
        select(Message)
        .where(Message.room_id == room_id)
        .order_by(Message.created_at.asc())
    )
    messages = result.scalars().all()

    return [
        {
            "id": message.id,
            "room_id": message.room_id,
            "user_id": message.user_id,
            "text": message.text,
            "created_at": message.created_at.isoformat() if message.created_at else None,
        }
        for message in messages
    ]


class CreateMessageRequest(SQLModel):
    text: str


@router.post("/{room_id}/messages")
async def create_message(room_id: int, req: CreateMessageRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    room = await session.get(ChatRoom, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")

    message = Message(
        room_id=room_id,
        user_id=user.telegram_id,
        text=req.text,
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)

    return {
        "id": message.id,
        "room_id": message.room_id,
        "user_id": message.user_id,
        "text": message.text,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }
