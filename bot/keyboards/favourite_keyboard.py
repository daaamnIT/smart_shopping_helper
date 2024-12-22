from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton # type: ignore
from aiogram.utils.keyboard import ReplyKeyboardBuilder # type: ignore
from .. import texts

def get_preferences_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text=texts.preferences["allergies"])
    builder.button(text=texts.preferences["price_limit"])
    builder.button(text=texts.preferences["disliked_products"])
    builder.button(text=texts.preferences["view_preferences"])
    builder.button(text=texts.preferences["back"])
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)