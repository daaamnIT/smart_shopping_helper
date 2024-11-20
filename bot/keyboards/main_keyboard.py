from aiogram.types import ReplyKeyboardMarkup, KeyboardButton # type: ignore
from aiogram.utils.keyboard import ReplyKeyboardBuilder # type: ignore
import texts

def get_main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text=texts.buttons["new_recipe"])
    builder.button(text=texts.buttons["favorite_recipes"])
    builder.button(text=texts.buttons["recipe_history"])
    builder.button(text=texts.buttons["preferences"])
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)