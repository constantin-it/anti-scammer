from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from database import save_message

class ChatLoggingMiddleware(BaseMiddleware):
    """
    Middleware, который автоматически перехватывает входящие сообщения от пользователей
    и сохраняет их в базу данных.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message):
            if event.from_user and not event.from_user.is_bot:
                # Если это текст сообщения
                text_to_save = event.text or event.caption
                if text_to_save:
                    await save_message(user_id=event.from_user.id, sender="user", text=text_to_save)
        elif isinstance(event, CallbackQuery):
            if event.from_user and event.data:
                await save_message(
                    user_id=event.from_user.id,
                    sender="user",
                    text=f"[Нажата кнопка: {event.data}]"
                )

        return await handler(event, data)
