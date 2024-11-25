from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from bot.keyboards.main_keyboard import get_main_keyboard
from bot import texts
from bot.settings import BOT_TOKEN

from backend.services.ai_service.ai import get_recipe

# Define states for the conversation flow
class RecipeStates(StatesGroup):
    waiting_for_recipe_request = State()

# Create router for command handling
router = Router()

# Start command handler
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        str(texts.welcome_message(message)),
        reply_markup=get_main_keyboard()
    )

# New recipe request handler
@router.message(lambda msg: msg.text == texts.buttons["new_recipe"])
async def new_recipe_request(message: types.Message, state: FSMContext):
    # Send instruction message and set state
    await message.answer(
        "Пожалуйста, напишите название блюда и количество порций.\n"
        "Например: 'борщ на 2 порции' или 'паста карбонара на 4 порции'"
    )
    await state.set_state(RecipeStates.waiting_for_recipe_request)

# Handle the actual recipe request
@router.message(StateFilter(RecipeStates.waiting_for_recipe_request))
async def process_recipe_request(message: types.Message, state: FSMContext):
    # Send "typing" action while processing
    await message.bot.send_chat_action(message.chat.id, "typing")
    
    try:
        # Get recipe from GPT
        recipe_text, ingredients = await get_recipe(message.text)
        
        # Send the recipe
        await message.answer(recipe_text, reply_markup=get_main_keyboard())
        
        # Clear the state
        await state.clear()
        
    except Exception as e:
        print(e)
        await message.answer(
            "Извините, произошла ошибка при получении рецепта. Попробуйте еще раз или выберите другое блюдо.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()

# Other button handlers
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
    # Initialize bot and dispatcher
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Include router
    dp.include_router(router)
    
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())