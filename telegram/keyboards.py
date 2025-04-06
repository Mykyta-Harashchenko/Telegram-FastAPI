from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


async def add_expense() -> KeyboardButton:
    return KeyboardButton(text="Додати статтю витрат")

async def get_review() -> KeyboardButton:
    return KeyboardButton(text="Отримати звіт")

async def remove_expense() -> KeyboardButton:
    return KeyboardButton(text="Видалити статтю витрат")

async def patch_expense() -> KeyboardButton:
    return KeyboardButton(text="Відредагувати статтю витрат")

