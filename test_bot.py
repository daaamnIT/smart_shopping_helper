import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import Bot, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, Message, User, Chat

from bot.paste import RecipeCallback
from bot.keyboards.main_keyboard import get_main_keyboard
from bot.keyboards.preferences_keyboard import get_preferences_keyboard
from main import (
    RecipeStates,
    PreferenceStates,
    process_recipe_request,
    handle_preference_choice,
    handle_allergies,
    new_recipe_request,
    favorite_recipes,
    recipe_history,
    cmd_start,
    Handler
)

@pytest.fixture
def message():
    message = AsyncMock(spec=Message)
    message.from_user = AsyncMock(spec=User)
    message.from_user.id = 12345
    message.from_user.username = "test_user"
    message.from_user.first_name = "Test"
    message.from_user.language_code = "en"
    message.chat = AsyncMock(spec=Chat)
    message.chat.id = 12345
    return message

@pytest.fixture
def state():
    storage = MemoryStorage()
    state = FSMContext(storage=storage, key=('test_bot', 12345, 12345))
    return state

@pytest.fixture
def handler():
    return Handler()

@pytest.mark.asyncio
async def test_cmd_start(message, state):
    message.answer = AsyncMock()
    
    await cmd_start(message)
    
    message.answer.assert_called_once()
    assert isinstance(message.answer.call_args[1]['reply_markup'], type(get_main_keyboard()))

@pytest.mark.asyncio
async def test_new_recipe_request(message, state):
    message.answer = AsyncMock()
    
    await new_recipe_request(message, state)
    
    message.answer.assert_called_once()
    current_state = await state.get_state()
    assert current_state == RecipeStates.waiting_for_recipe_request.state

@pytest.mark.asyncio
async def test_process_recipe_request_cancel(message, state):
    message.text = "Отмена"
    message.answer = AsyncMock()
    
    await process_recipe_request(message, state)
    
    message.answer.assert_called_once_with(
        "Поиск рецепта отменен",
        reply_markup=get_main_keyboard()
    )
    current_state = await state.get_state()
    assert current_state is None

@pytest.mark.asyncio
async def test_handle_preference_choice_back(message, state):
    message.text = "Назад"
    message.answer = AsyncMock()
    
    await handle_preference_choice(message, state)
    
    message.answer.assert_called_once_with(
        "Возвращаемся в главное меню",
        reply_markup=get_main_keyboard()
    )
    current_state = await state.get_state()
    assert current_state is None

@pytest.mark.asyncio
async def test_handle_allergies_cancel(message, state):
    message.text = "Отмена"
    message.answer = AsyncMock()
    
    await handle_allergies(message, state)
    
    message.answer.assert_called_once_with(
        "Настройка аллергий отменена",
        reply_markup=get_preferences_keyboard()
    )
    current_state = await state.get_state()
    assert current_state == PreferenceStates.waiting_for_menu_choice.state