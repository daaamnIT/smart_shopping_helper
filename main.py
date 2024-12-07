from aiogram import Bot, Dispatcher, types, Router, F   #type: ignore
from aiogram.filters import Command, StateFilter    #type: ignore
from aiogram.fsm.context import FSMContext  #type: ignore
from aiogram.fsm.state import State, StatesGroup    #type: ignore
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton   #type: ignore
from aiogram.client.default import DefaultBotProperties   #type: ignore
from aiogram.enums import ParseMode  #type: ignore


from bot.keyboards.main_keyboard import get_main_keyboard
from bot import texts
from bot.settings import BOT_TOKEN
from backend.services.ai_service.ai import get_recipe
from backend.handler import Handler
from backend.parser.parser import data_parser

class RecipeStates(StatesGroup):
    waiting_for_recipe_request = State()

router = Router()
handler = Handler()

@router.message(lambda msg: msg.text == texts.buttons["new_recipe"])
async def new_recipe_request(message: types.Message, state: FSMContext):
    await message.answer(
        "Пожалуйста, напишите название блюда и количество порций.\n"
        "Например: 'борщ на 2 порции' или 'паста карбонара на 4 порции'"
    )
    await state.set_state(RecipeStates.waiting_for_recipe_request)

@router.message(StateFilter(RecipeStates.waiting_for_recipe_request))
async def process_recipe_request(message: types.Message, state: FSMContext):
    await message.bot.send_chat_action(message.chat.id, "typing")
    
    try:
        user_id = message.from_user.id
        
        recipe_text, ingredients = await get_recipe(message.text)
        
        ingredients = {key.replace(' ', "+"): value for key, value in ingredients.items()}

        print(f'ingredients:\n {ingredients}')


        links = await data_parser(ingredients)


        recipe_text = recipe_text.replace('**', '')
        recipe_text = recipe_text.replace('*', '•')
        key_word = "Приготовление"
        key_word_pos = recipe_text.find(key_word)
        if key_word_pos != -1:
            recipe_text =  recipe_text[:key_word_pos] + "\n" + recipe_text[key_word_pos:]
        
        recipe_data = {
            'text': recipe_text,
            'ingredients': ingredients,
            'request': message.text
        }
        
        await handler.new_recipe_handler(user_id, recipe_data)

        products_message = ""
        for product in links:
            products_message += f"{product["name"]}:\nЦена: {product["price"]}\nСсылка: {product["link"]}\n\n"

        print(products_message)

        result_message = recipe_text + "\n\n" + "Ссылки на продукты:\n" + "\n" + products_message
        
        await message.answer(result_message, reply_markup=get_main_keyboard())
        
        await state.clear()
        
    except Exception as e:
        print(f"Error processing recipe request: {e}")
        await message.answer(
            "Извините, произошла ошибка при получении рецепта. Попробуйте еще раз или выберите другое блюдо.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()


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

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    await handler.add_new_user(user_id)
    await message.answer(
        str(texts.welcome_message(message)),
        reply_markup=get_main_keyboard()
    )

async def main():
    default = DefaultBotProperties(parse_mode=ParseMode.HTML)

    bot = Bot(token=BOT_TOKEN, default=default)
    dp = Dispatcher()
    
    dp.include_router(router)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())