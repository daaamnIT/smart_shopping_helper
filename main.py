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
from bot.keyboards.preferences_keyboard import get_preferences_keyboard

class RecipeStates(StatesGroup):
    waiting_for_recipe_request = State()

class PreferenceStates(StatesGroup):
    waiting_for_menu_choice = State()
    waiting_for_allergies = State()
    waiting_for_price_limit = State()
    waiting_for_disliked_products = State()

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
async def preferences(message: types.Message, state: FSMContext):
    await message.answer(
        "Выберите, что хотите настроить:",
        reply_markup=get_preferences_keyboard()
    )
    await state.set_state(PreferenceStates.waiting_for_menu_choice)

@router.message(StateFilter(PreferenceStates.waiting_for_menu_choice))
async def handle_preference_choice(message: types.Message, state: FSMContext):
    choice = message.text
    
    if choice == "Назад":
        await message.answer(
            "Возвращаемся в главное меню",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
        return

    if choice == "Аллергия":
        await message.answer(
            "Пожалуйста, напишите все продукты, на которые у вас аллергия, в одном сообщении через запятую",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="Отмена")]],
                resize_keyboard=True
            )
        )
        await state.set_state(PreferenceStates.waiting_for_allergies)
        
    elif choice == "Ограничение цены":
        await message.answer(
            "Введите максимальную сумму (в целых числах), которую вы готовы потратить на продукты для одного рецепта",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="Отмена")]],
                resize_keyboard=True
            )
        )
        await state.set_state(PreferenceStates.waiting_for_price_limit)
        
    elif choice == "Нелюбимые продукты":
        await message.answer(
            "Пожалуйста, напишите все нелюбимые продукты в одном сообщении через запятую",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="Отмена")]],
                resize_keyboard=True
            )
        )
        await state.set_state(PreferenceStates.waiting_for_disliked_products)

    if choice == "Посмотреть мои предпочтения":
        user_id = message.from_user.id
        preferences_text = await handler.get_formatted_preferences(user_id)
        await message.answer(
            preferences_text,
            reply_markup=get_preferences_keyboard()
        )
        return

@router.message(StateFilter(PreferenceStates.waiting_for_allergies))
async def handle_allergies(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await message.answer(
            "Настройка аллергий отменена",
            reply_markup=get_preferences_keyboard()
        )
        await state.set_state(PreferenceStates.waiting_for_menu_choice)
        return

    user_id = message.from_user.id
    allergies = [item.strip() for item in message.text.split(',')]
    
    await handler.update_user_allergies(user_id, allergies)
    
    await message.answer(
        "Список аллергий обновлен",
        reply_markup=get_preferences_keyboard()
    )
    await state.set_state(PreferenceStates.waiting_for_menu_choice)

@router.message(StateFilter(PreferenceStates.waiting_for_price_limit))
async def handle_price_limit(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await message.answer(
            "Настройка ограничения цены отменена",
            reply_markup=get_preferences_keyboard()
        )
        await state.set_state(PreferenceStates.waiting_for_menu_choice)
        return

    try:
        price_limit = int(message.text)
        user_id = message.from_user.id
        
        await handler.update_price_limit(user_id, price_limit)
        
        await message.answer(
            f"Ограничение цены установлено на {price_limit}",
            reply_markup=get_preferences_keyboard()
        )
        await state.set_state(PreferenceStates.waiting_for_menu_choice)
    except ValueError:
        await message.answer(
            "Пожалуйста, введите целое число",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="Отмена")]],
                resize_keyboard=True
            )
        )

@router.message(StateFilter(PreferenceStates.waiting_for_disliked_products))
async def handle_disliked_products(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await message.answer(
            "Настройка нелюбимых продуктов отменена",
            reply_markup=get_preferences_keyboard()
        )
        await state.set_state(PreferenceStates.waiting_for_menu_choice)
        return

    user_id = message.from_user.id
    disliked_products = [item.strip() for item in message.text.split(',')]
    
    await handler.update_disliked_products(user_id, disliked_products)
    
    await message.answer(
        "Список нелюбимых продуктов обновлен",
        reply_markup=get_preferences_keyboard()
    )
    await state.set_state(PreferenceStates.waiting_for_menu_choice)


@router.message(StateFilter(PreferenceStates.waiting_for_menu_choice),lambda msg: msg.text == "Посмотреть мои предпочтения")
async def view_preferences(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    print("get my preferences")
    preferences_text = await handler.get_formatted_preferences(user_id)
    print(preferences_text)
    
    await message.answer(
        preferences_text,
        reply_markup=get_preferences_keyboard()
    )

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.username or message.from_user.first_name
    language = message.from_user.language_code or "en"
    
    await handler.add_new_user(user_id, user_name, language)
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