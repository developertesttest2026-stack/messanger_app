import asyncio
import secrets
from datetime import datetime, timedelta,timezone
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from sqlmodel import select
from api.database import async_session_maker
from api.models import LoginSession,User 
import settings



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    username = update.effective_user.username or ""
    full_name = update.effective_user.full_name or ""

    # Получаем session_token из deep link
    session_token = context.args[0] if context.args else None

    if not session_token:
        await update.message.reply_text(
            "❌ Сессия не найдена.\n\n"
            "Открой сайт и нажми 'Войти через Telegram', "
            "чтобы получить ссылку."
        )
        return

    # Ищем сессию
    async with async_session_maker() as session:
        result = await session.execute(
            select(LoginSession).where(
                LoginSession.session_token == session_token,
                LoginSession.status == "pending"
            )
        )
        login_session = result.scalar_one_or_none()

        if not login_session:
            await update.message.reply_text(
                "❌ Сессия не найдена или уже использована.\n\n"
                "Обнови страницу сайта и попробуй снова."
            )
            return

        if login_session.expires_at < datetime.now(timezone.utc)+timedelta(hours=3):
            await update.message.reply_text(
                "❌ Сессия истекла.\n\n"
                "Обнови страницу сайта и попробуй снова."
            )
            return

        # Создаём/обновляем пользователя
        result = await session.execute(
            select(User).where(User.telegram_id == tg_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                telegram_id=tg_id,
                username=username,
                full_name=full_name
            )
            session.add(user)
            await session.flush()

        # Генерируем код
        code = "".join(secrets.choice("0123456789") for _ in range(6))
        expires_at = datetime.now(timezone.utc) + timedelta(hours=3,minutes=5)

        # Обновляем сессию
        login_session.telegram_id = tg_id
        login_session.code = code
        login_session.status = "code_sent"
        login_session.expires_at = expires_at
        session.add(login_session)
        await session.commit()

    await update.message.reply_text(
        f"👋 Привет, {update.effective_user.first_name}!\n\n"
        f"🔐 Твой код подтверждения:\n\n"
        f"<b>{code}</b>\n\n"
        f"⏳ Код действителен 5 минут.\n"
        f"Введи его на сайте.",
        parse_mode="HTML"
    )
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Используй /start чтобы получить код для входа на сайт."
    )

def main():
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    print("Бот запущен!")
    main()

