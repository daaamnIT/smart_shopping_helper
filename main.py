from aiogram import Bot, Dispatcher, types, Router, F   #type: ignore
from aiogram.filters import Command, StateFilter    #type: ignore
from aiogram.fsm.context import FSMContext  #type: ignore
from aiogram.fsm.state import State, StatesGroup    #type: ignore
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton   #type: ignore
from aiogram.client.default import DefaultBotProperties   #type: ignore
from aiogram.enums import ParseMode  #type: ignore
from aiogram.filters.callback_data import CallbackData  #type: ignore
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery #type: ignore


from bot.keyboards.main_keyboard import get_main_keyboard
from bot import texts
from bot.settings import BOT_TOKEN
from backend.services.ai_service.ai import get_recipe
from backend.handler import Handler
from backend.parser.parser import data_parser, knapsack, standardize_ingredients
from bot.keyboards.preferences_keyboard import get_preferences_keyboard
from bot.paste import RecipeCallback
import asyncio
from bot.loading_messages import get_random_loading_message



class RecipeStates(StatesGroup):
    waiting_for_recipe_request = State()

class PreferenceStates(StatesGroup):
    waiting_for_menu_choice = State()
    waiting_for_allergies = State()
    waiting_for_price_limit = State()
    waiting_for_disliked_products = State()

router = Router()
handler = Handler()

class PaginationCallback(CallbackData, prefix="page"):
    offset: int
    page_type: str = "history"

class LoadingMessageManager:
    def __init__(self, message: types.Message):
        self.message = message
        self.is_running = True
        self.task = None
        self.current_operation = "🔍 Начинаю поиск рецепта..."

    async def update_loading_message(self):
        while self.is_running:
            try:
                loading_text = get_random_loading_message()
                if not loading_text.endswith('...'): 
                    loading_text += '...'
                await self.message.edit_text(loading_text)
            except Exception as e:
                print(f"Error updating loading message: {e}")
            finally:
                if self.is_running:
                    await asyncio.sleep(2.5)

    async def start(self):
        self.task = asyncio.create_task(self.update_loading_message())
        return self.task

    async def stop(self):
        self.is_running = False
        if self.task and not self.task.done():
            try:
                self.task.cancel()
                await self.task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"Error stopping loading message task: {e}")

@router.message(lambda msg: msg.text == texts.buttons["new_recipe"])
async def new_recipe_request(message: types.Message, state: FSMContext):
    await message.answer(
        "Пожалуйста, напишите название блюда и количество порций.\n"
        "Например: 'борщ на 2 порции' или 'паста карбонара на 4 порции'",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Отмена")]],
            resize_keyboard=True
        )
    )
    await state.set_state(RecipeStates.waiting_for_recipe_request)

async def generate_products_message(data):
    if isinstance(data, str):
        return data
    
    products_message = ""
    
    for category, products in data.items():
        if products:
            if len(products) == 1 and "message" in products[0]:
                products_message += f"{category.replace('+', ' ')}:\n{products[0]['message']}\n\n"
                continue
            
            for product in products:
                if "message" in product:
                    products_message += f"{product['message']}\n\n"
                else:
                    products_message += (
                        f"{product.get('name', 'Название не указано')}\n"
                        f"Цена: {product.get('price', 'Цена не указана')}\n"
                        f"Ссылка: {product.get('link', 'Ссылка отсутствует')}\n\n"
                    )
    
    return products_message.strip() if products_message else "Продукты не найдены"

@router.message(StateFilter(RecipeStates.waiting_for_recipe_request))
async def process_recipe_request(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await message.answer(
            "Поиск рецепта отменен",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
        return
    
    loading_message = await message.answer("🔍 Начинаю поиск рецепта...")
    loading_manager = LoadingMessageManager(loading_message)
    
    try:
        loading_task = await loading_manager.start()
        user_id = message.from_user.id

        preferences = await handler.get_user_preferences(user_id)        

        recipe_text, ingredients = await get_recipe(message.text, preferences)
        
        recipe_text = '🍳 ' + message.text + "\n\n" + recipe_text
        

        ingredients = {key.replace(' ', "+"): value for key, value in ingredients.items()}
        standardized_ingredients = await standardize_ingredients(ingredients)

        raw_links = {}
        try:
            raw_links = await data_parser(ingredients)
        except Exception as e:
            print(f"Error getting product links: {e}")
        
        max_price = int(preferences['max_price']) if preferences['max_price'] else 20000000
        links = await knapsack(raw_links, standardized_ingredients, max_price)


        recipe_text = recipe_text.replace('**', '')
        recipe_text = recipe_text.replace('*', '•')
        key_word = "Приготовление"
        key_word_pos = recipe_text.find(key_word)
        if key_word_pos != -1:
            recipe_text = recipe_text[:key_word_pos] + "\n" + recipe_text[key_word_pos:]
        
        recipe_data = {
            'text': recipe_text,
            'ingredients': ingredients,
            'request': message.text,
            'links': links
        }

        
        # await loading_manager.set_stage("💾 Сохраняю рецепт...")
        recipe_id = await handler.new_recipe_handler(user_id, recipe_data)
        
        products_message = await generate_products_message(links)
        result_message = f"{recipe_text}\n\nСсылки на продукты:\n\n{products_message}"
        
        keyboard = handler.create_recipe_keyboard(recipe_id, user_id, show_full=False)
        
        await loading_manager.stop()
        
        await loading_message.edit_text(result_message, reply_markup=keyboard)
        
        await message.answer("Приготовим что-то еще?", reply_markup=get_main_keyboard())
        await state.clear()
        
    except Exception as e:
        print(f"Error processing recipe request: {e}")
        await loading_manager.stop()
        
        error_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="Попробовать снова", callback_data="try_again")
            ]]
        )
        
        await loading_message.edit_text(
            "Извините, произошла ошибка при получении рецепта. Попробуйте еще раз или выберите другое блюдо.",
            reply_markup=error_keyboard
        )
        
        await message.answer("Приготовим что-то еще?", reply_markup=get_main_keyboard())
        await state.clear()

@router.callback_query(lambda c: c.data == "try_again")
async def try_again(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer(
        "Пожалуйста, напишите название блюда и количество порций.\n"
        "Например: 'борщ на 2 порции' или 'паста карбонара на 4 порции'"
    )
    await state.set_state(RecipeStates.waiting_for_recipe_request)
    await callback.answer()

@router.message(lambda msg: msg.text == texts.buttons["favorite_recipes"])
async def favorite_recipes(message: types.Message):
    user_id = message.from_user.id
    favorites = await handler.get_favorite_recipes(user_id)
    
    if not favorites:
        await message.answer("У вас пока нет избранных рецептов")
        return
    
    recipes_text = ""
    keyboard_buttons = []
    
    current_recipes = favorites[:3]
    for i, recipe in enumerate(current_recipes, start=1):
        recipes_text += f"🍳 {recipe['name']}\n\n"
        keyboard_buttons.append([InlineKeyboardButton(
            text=f"Рецепт {i}",
            callback_data=RecipeCallback(action="get_full", id=recipe["_id"]).pack()
        )])
    
    nav_buttons = []
    if len(favorites) > 3:
        nav_buttons.append(
            InlineKeyboardButton(
                text="Следующие →",
                callback_data=PaginationCallback(offset=3, page_type="favorites").pack()
            )
        )
    
    if nav_buttons:
        keyboard_buttons.append(nav_buttons)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await message.answer(recipes_text.strip(), reply_markup=keyboard)


@router.message(lambda msg: msg.text == texts.buttons["recipe_history"])
async def recipe_history(message: types.Message):
    user_id = message.from_user.id
    recipes, has_more = await handler.get_recipe_history(user_id, offset=0, limit=3)
    
    if not recipes:
        await message.answer(texts.recipe_history_response)
        return
    
    recipes_text = ""
    keyboard_buttons = []
    
    for i, recipe in enumerate(recipes, start=1):
        recipes_text += f"🍳 {recipe['name']}\n\n"
        keyboard_buttons.append([InlineKeyboardButton(
            text=f"Рецепт {i}",
            callback_data=RecipeCallback(action="get_full", id=recipe["_id"]).pack()
        )])
    
    nav_buttons = []
    if has_more:
        nav_buttons.append(
            InlineKeyboardButton(
                text="Следующие →",
                callback_data=PaginationCallback(offset=3, page_type="history").pack()
            )
        )
    
    if nav_buttons:
        keyboard_buttons.append(nav_buttons)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await message.answer(recipes_text.strip(), reply_markup=keyboard)


@router.callback_query(PaginationCallback.filter())
async def handle_pagination(callback: CallbackQuery, callback_data: PaginationCallback):
    if callback_data.page_type == "history":
        await show_more_history(callback, callback_data)
    else:
        await show_more_favorites(callback, callback_data)


@router.callback_query(RecipeCallback.filter(F.action == "get_full"))
async def get_full_recipe(callback: CallbackQuery, callback_data: RecipeCallback):
    recipe_id = callback_data.id
    user_id = callback.from_user.id
    recipe = handler.recipe_db.get_recipe(recipe_id)
    
    if recipe:
        formatted_recipe = await handler.format_recipe_with_links(recipe)
        keyboard = handler.create_recipe_keyboard(recipe_id, user_id, show_full=False)
        await callback.message.answer(
            formatted_recipe,
            reply_markup=keyboard
        )
    else:
        await callback.message.answer("Рецепт не найден")
    
    await callback.answer()


@router.callback_query(PaginationCallback.filter())
async def show_more_recipes(callback: CallbackQuery, callback_data: PaginationCallback):
    offset = callback_data.offset
    user_id = callback.from_user.id
    
    recipes, has_more = await handler.get_recipe_history(user_id, offset=offset, limit=3)
    
    if recipes:
        await callback.message.delete()
        
        recipes_text = ""
        keyboard_buttons = []
        
        for i, recipe in enumerate(recipes, start=offset+1):
            recipes_text += f"🍳 {recipe['name']}\n\n"
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"Рецепт {i}",
                callback_data=RecipeCallback(action="get_full", id=recipe["_id"]).pack()
            )])
        
        nav_buttons = []
        
        if offset >= 3:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="← Предыдущие",
                    callback_data=PaginationCallback(offset=offset - 3).pack()
                )
            )
        
        if has_more:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="Следующие →",
                    callback_data=PaginationCallback(offset=offset + 3).pack()
                )
            )
        
        if nav_buttons:
            keyboard_buttons.append(nav_buttons)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await callback.message.answer(recipes_text.strip(), reply_markup=keyboard)
    
    await callback.answer()

async def show_more_history(callback: CallbackQuery, callback_data: PaginationCallback):
    offset = callback_data.offset
    user_id = callback.from_user.id
    
    recipes, has_more = await handler.get_recipe_history(user_id, offset=offset, limit=3)
    
    if recipes:
        await callback.message.delete()
        
        recipes_text = ""
        keyboard_buttons = []
        
        for i, recipe in enumerate(recipes, start=offset+1):
            recipes_text += f"🍳 {recipe['name']}\n\n"
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"Рецепт {i}",
                callback_data=RecipeCallback(action="get_full", id=recipe["_id"]).pack()
            )])
        
        nav_buttons = []
        
        if offset >= 3:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="← Предыдущие",
                    callback_data=PaginationCallback(offset=offset - 3, page_type="history").pack()
                )
            )
        
        if has_more:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="Следующие →",
                    callback_data=PaginationCallback(offset=offset + 3, page_type="history").pack()
                )
            )
        
        if nav_buttons:
            keyboard_buttons.append(nav_buttons)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await callback.message.answer(recipes_text.strip(), reply_markup=keyboard)
    
    await callback.answer()


async def show_more_favorites(callback: CallbackQuery, callback_data: PaginationCallback):
    offset = callback_data.offset
    user_id = callback.from_user.id
    
    favorites = await handler.get_favorite_recipes(user_id)
    
    if favorites and offset < len(favorites):
        await callback.message.delete()
        
        current_recipes = favorites[offset:offset+3]
        recipes_text = ""
        keyboard_buttons = []
        
        for i, recipe in enumerate(current_recipes, start=offset+1):
            recipes_text += f"🍳 {recipe['name']}\n\n"
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"Рецепт {i}",
                callback_data=RecipeCallback(action="get_full", id=recipe["_id"]).pack()
            )])
        
        nav_buttons = []
        
        if offset >= 3:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="← Предыдущие",
                    callback_data=PaginationCallback(offset=offset - 3, page_type="favorites").pack()
                )
            )
        
        if offset + 3 < len(favorites):
            nav_buttons.append(
                InlineKeyboardButton(
                    text="Следующие →",
                    callback_data=PaginationCallback(offset=offset + 3, page_type="favorites").pack()
                )
            )
        
        if nav_buttons:
            keyboard_buttons.append(nav_buttons)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await callback.message.answer(recipes_text.strip(), reply_markup=keyboard)
    
    await callback.answer()


@router.callback_query(RecipeCallback.filter(F.action == "toggle_favorite"))
async def toggle_favorite(callback: CallbackQuery, callback_data: RecipeCallback):
    user_id = callback.from_user.id
    recipe_id = callback_data.id
    
    is_favorite = await handler.toggle_favorite_recipe(user_id, recipe_id)
    

    new_keyboard = handler.create_recipe_keyboard(
        recipe_id, 
        user_id, 
        show_full="Получить полный рецепт" in callback.message.reply_markup.inline_keyboard[0][0].text
    )
    
    await callback.message.edit_reply_markup(reply_markup=new_keyboard)
    
    status_text = "добавлен в избранное" if is_favorite else "удален из избранного"
    await callback.answer(f"Рецепт {status_text}")


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
            "Пожалуйста, напишите все продукты, на которые у вас аллергия, в одном сообщении через запятую.\n"
            "Или нажмите 'Очистить' чтобы удалить все аллергии.",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="Очистить")],
                    [KeyboardButton(text="Отмена")]
                ],
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
            "Пожалуйста, напишите все нелюбимые продукты в одном сообщении через запятую.\n"
            "Или нажмите 'Очистить' чтобы удалить все нелюбимые продукты.",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="Очистить")],
                    [KeyboardButton(text="Отмена")]
                ],
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
        
    if message.text == "Очистить":
        user_id = message.from_user.id
        await handler.update_user_allergies(user_id, [])
        await message.answer(
            "Список аллергий очищен",
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

    if message.text == "Очистить":
        user_id = message.from_user.id
        await handler.update_disliked_products(user_id, [])
        await message.answer(
            "Список нелюбимых продуктов очищен",
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
    asyncio.run(main())