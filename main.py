from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode


from bot.keyboards.main_keyboard import get_main_keyboard
from bot import texts
from bot.settings import BOT_TOKEN
from backend.services.ai_service.ai import get_recipe
from backend.handler import Handler  # Import the Handler class

# Define states for the conversation flow
class RecipeStates(StatesGroup):
    waiting_for_recipe_request = State()

# Create router for command handling
router = Router()
handler = Handler()  # Initialize the handler

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
        user_id = message.from_user.id
        
        # Get recipe from GPT
        recipe_text, ingredients = await get_recipe(message.text)
        
        # Handle the new recipe with the handler
        recipe_data = {
            'text': recipe_text,
            'ingredients': ingredients,
            'request': message.text
        }
        
        # Process the recipe with handler
        await handler.new_recipe_handler(user_id, recipe_data)
        
        # Send the recipe
        await message.answer(recipe_text, reply_markup=get_main_keyboard())
        
        # Clear the state
        await state.clear()
        
    except Exception as e:
        print(f"Error processing recipe request: {e}")
        await message.answer(
            "Извините, произошла ошибка при получении рецепта. Попробуйте еще раз или выберите другое блюдо.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()


# Update other handlers to use the Handler class
@router.message(lambda msg: msg.text == texts.buttons["favorite_recipes"])
async def favorite_recipes(message: types.Message):
    user_id = message.from_user.id
    favorites = await handler.get_favorite_recipes(user_id)
    if favorites:
        await message.answer(favorites)
    else:
        await message.answer(texts.favourite_recipes_response)

@router.message(lambda msg: msg.text == texts.buttons["recipe_history"])
async def recipe_history(message: types.Message):
    user_id = message.from_user.id
    history = await handler.get_recipe_history(user_id)
    if history:
        await message.answer(history)
    else:
        await message.answer(texts.recipe_history_response)

@router.message(lambda msg: msg.text == texts.buttons["preferences"])
async def preferences(message: types.Message):
    user_id = message.from_user.id
    user_preferences = await handler.get_user_preferences(user_id)
    if user_preferences:
        await message.answer(user_preferences)
    else:
        await message.answer(texts.preferences_response)

# Start command handler with user registration
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    await handler.add_new_user(user_id)  # Register new user
    await message.answer(
        str(texts.welcome_message(message)),
        reply_markup=get_main_keyboard()
    )

async def main():
    default = DefaultBotProperties(parse_mode=ParseMode.HTML)

    bot = Bot(token=BOT_TOKEN, default=default)
    dp = Dispatcher()
    
    # Include router
    dp.include_router(router)
    
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())