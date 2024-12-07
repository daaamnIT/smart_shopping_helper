import aiohttp
import asyncio
import json
import re
import ssl
from settings import GPT_API_KEY
 
def parse_ingredients(recipe: str) -> dict:
    """
    Парсит ингредиенты из рецепта в словарь
    """
    ingredients_dict = {}
 
    # Находим секцию с ингредиентами
    ingredients_section = ""
    if "Ингредиенты:" in recipe:
        sections = recipe.split("Приготовление:")
        if len(sections) > 0:
            ingredients_section = sections[0].split("Ингредиенты:")[1].strip()
    else:
        sections = recipe.split("\n\n")
        if len(sections) > 0:
            ingredients_section = sections[0]
 
    if not ingredients_section:
        return ingredients_dict
 
    # Разбиваем на отдельные строки
    lines = ingredients_section.split('\n')
 
    for line in lines:
        line = line.strip()
        if not line or line == "**":  # Пропускаем пустые строки и **
            continue
 
        # Убираем звездочки, точки с запятой и точки в конце
        line = line.strip('*., ;')
 
        # Паттерн для извлечения названия и количества
        pattern = r'^(.*?)(?:[-—–]\s*)([\d.,]+\s*(?:г|кг|мл|л|шт|ст\.|ч\.|ст\.л\.|ч\.л\.|штук|грамм|грамма|граммов|литр|литра|литров|зубчик|зубчика|штуки|пучок|пучка|банка|упаковка|стакан|стакана)|\s*по\s*вкусу)'
 
        match = re.match(pattern, line, re.IGNORECASE)
        if match:
            name, amount = match.groups()
            name = name.strip('* ')  # Убираем звездочки и пробелы
 
            # Если количество "по вкусу", пропускаем этот ингредиент
            if 'по вкусу' in amount.lower():
                continue
 
            ingredients_dict[name.lower()] = amount.strip()
 
    return ingredients_dict
 
 
def format_recipe(raw_recipe: str) -> tuple:
    """
    Форматирует рецепт и возвращает как отформатированный текст и словарь ингредиентов
    """
    # Базовое форматирование
    formatted = raw_recipe.replace('\n\n', '\n')
    if "Ингредиенты" not in formatted:
        formatted = "🥘 Ингредиенты:\n" + formatted
 
    # Парсим ингредиенты
    ingredients = parse_ingredients(raw_recipe)
 
    # Добавляем отформатированный список ингредиентов
    # ingredients_text = "\n\nСписок ингредиентов в структурированном виде:\n"
    # for name, amount in ingredients.items():
    #     ingredients_text += f"• {name}: {amount}\n"
 
    return formatted, ingredients
 
 
# ... parse_ingredients and format_recipe functions remain the same as they don't need to be async ...
 
async def get_recipe(query: str) -> tuple:
    """
    Асинхронно получает запрос вида "борщ на 2 порции" и возвращает рецепт от YandexGPT
    и словарь ингредиентов
    """
    API_KEY = GPT_API_KEY
    URL = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'
 
    headers = {
        'Authorization': f'Api-Key {API_KEY}',
        'Content-Type': 'application/json'
    }
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
 
    system_prompt = """Ты - опытный повар. Напиши подробный рецепт блюда.
    Формат ответа должен быть строго такой:
 
    Ингредиенты:
    • продукт - количество
 
    Приготовление:
    1. Шаг первый
    2. Шаг второй"""
 
    data = {
        "modelUri": "gpt://b1gjsebilk1g8hvtc07c/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": 2000
        },
        "messages": [
            {
                "role": "system",
                "text": system_prompt
            },
            {
                "role": "user",
                "text": f"Напиши рецепт: {query}"
            }
        ]
    }
 
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(URL, headers=headers, json=data, ssl=ssl_context) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API вернул статус {response.status}: {error_text}")
 
                result = await response.json()
                recipe = result['result']['alternatives'][0]['message']['text']
 
                # Форматируем и получаем словарь ингредиентов
                formatted_recipe, ingredients_dict = format_recipe(recipe)
                return formatted_recipe, ingredients_dict
 
    except Exception as e:
        return f"Произошла ошибка при получении рецепта: {str(e)}", {}