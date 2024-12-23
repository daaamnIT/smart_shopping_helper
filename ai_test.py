import pytest
from unittest.mock import patch, MagicMock
from backend.services.ai_service.ai import parse_ingredients, format_recipe, get_recipe

def test_parse_ingredients_with_ingredients_section():
    recipe = """
    Ингредиенты:
    Мука - 200 г
    Сахар - 100 г
    Соль - по вкусу
    Масло - 50 г
    Приготовление:
    1. Смешать все ингредиенты
    """
    result = parse_ingredients(recipe)
    assert result == {
        'мука': '200 г',
        'сахар': '100 г',
        'масло': '50 г'
    }

def test_parse_ingredients_without_ingredients_section():
    recipe = """
    Мука - 200 г
    Сахар - 100 г
    Масло - 50 г
    """
    result = parse_ingredients(recipe)
    assert result == {
        'мука': '200 г',
        'сахар': '100 г',
        'масло': '50 г'
    }

def test_parse_ingredients_empty():
    recipe = ""
    result = parse_ingredients(recipe)
    assert result == {}

# Test format_recipe
def test_format_recipe():
    raw_recipe = """
    Мука - 200 г
    Сахар - 100 г
    Масло - 50 г

    1. Смешать все ингредиенты
    """
    formatted, ingredients = format_recipe(raw_recipe)
    assert "🥘 Ингредиенты:" in formatted
    assert ingredients == {
        'мука': '200 г',
        'сахар': '100 г',
        'масло': '50 г'
    }

# Test get_recipe
@pytest.mark.asyncio
async def test_get_recipe_success():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'result': {
            'alternatives': [{
                'message': {
                    'text': """
                    Паста Карбонара:

                    Ингредиенты:
                    Спагетти - 200 г
                    Сливки - 200 мл
                    
                    Приготовление:
                    1. Сварить макароны
                    
                    Порций - 2
                    """
                }
            }]
        }
    }
    mock_response.raise_for_status = MagicMock()

    with patch('requests.post', return_value=mock_response):
        query = "карбонара на 2 порции"
        user_dict = {
            "allergies": ["бекон"],
            "unliked_products": ["яйца", "сыр"]
        }
        
        recipe, ingredients = await get_recipe(query, user_dict)
        assert "Ингредиенты:" in recipe
        assert ingredients == {
            'спагетти': '200 г',
            'сливки': '200 мл'
        }

@pytest.mark.asyncio
async def test_get_recipe_error():
    with patch('requests.post', side_effect=Exception("API Error")):
        query = "карбонара"
        user_dict = {}
        
        recipe, ingredients = await get_recipe(query, user_dict)
        assert "Произошла ошибка" in recipe
        assert ingredients == {}