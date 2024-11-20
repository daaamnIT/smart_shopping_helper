from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from keyboards.main_keyboard import get_main_keyboard

import texts

from settings import BOT_TOKEN

# Создаем роутер для обработки команд
router = Router()

# Обработчик команды /start
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        str(texts.welcome_message(message)),
        reply_markup=get_main_keyboard()
    )

# Обработчики кнопок меню
@router.message(lambda msg: msg.text == texts.buttons["new_recipe"])
async def new_recipe(message: types.Message):
    await message.answer(texts.new_recipe_response)

@router.message(lambda msg: msg.text == texts.buttons["favorite_recipes"])
async def favorite_recipes(message: types.Message):
    await message.answer(texts.favourite_recipes_response)

@router.message(lambda msg: msg.text == texts.buttons["recipe_history"])
async def recipe_history(message: types.Message):
    await message.answer(texts.recipe_history_response)

@router.message(lambda msg: msg.text == texts.buttons["preferences"])
async def preferences(message: types.Message):
    await message.answer(texts.preferences_response)

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())