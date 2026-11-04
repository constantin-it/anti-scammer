from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [
            KeyboardButton(text="🔍 Проверить текст / схему"),
            KeyboardButton(text="🚨 Дропперство и переводы")
        ],
        [
            KeyboardButton(text="🎮 Схемы в играх (валюта/скины)"),
            KeyboardButton(text="🛡 Памятка безопасности")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
    ])

def get_actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Проверить ещё сообщение", callback_data="start_check")],
        [InlineKeyboardButton(text="⚠️ Что делать, если уже перевёл?", callback_data="what_if_scammed")]
    ])
