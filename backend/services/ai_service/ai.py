import aiohttp
import asyncio
import json
import re
import ssl
import requests

from backend.services.ai_service.settings import GPT_API_KEY
 
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
   
async def get_recipe(query: str, user_dict: dict) -> tuple:
        """
        Получает запрос вида "борщ на 2 порции" и возвращает рецепт от YandexGPT,
        словарь ингредиентов и количество порций
        """
        # Извлекаем количество порций из запроса
        API_KEY = GPT_API_KEY
        URL = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'

        headers = {
            'Authorization': f'Api-Key {API_KEY}',
            'Content-Type': 'application/json'
        }

        # Формируем дополнительные ограничения для рецепта
        restrictions = []
        if user_dict.get('allergies'):
            restrictions.append(f"НЕЛЬЗЯ использовать продукты, на которые есть аллергия: {', '.join(user_dict['allergies'])}")
        if user_dict.get('unliked_products'):
            restrictions.append(f"НЕ используй следующие продукты: {', '.join(user_dict['unliked_products'])}")

        restrictions_text = "\n".join(restrictions)

        caution = "Обрати внимение на стандартное количество продуктов в одной упаковке. Например, в одной упаковке яиц обычно 10 штук, а в пачке масла 200 грамм. Учти это при оценки множителя продуктов продуктов, которые нужно купить."

        system_prompt = f"""Ты - опытный повар. Напиши подробный рецепт блюда.
        {restrictions_text}
        {caution}

        Формат ответа должен быть строго такой:

        [Название блюда]:

        Ингредиенты:
        • продукт - количество

        Приготовление:
        1. Шаг первый
        2. Шаг второй
        
        
        Напиши множитель продуктов в формате "Порций - [целое число]". Например, "порций - 2".
        """
        
        # print(system_prompt)
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
                    "text": f"Напиши рецепт: {query + ' ' + restrictions_text + ' ' + caution + 'Напиши количество порций в формате "порций - [целое число]". Например, "порций - 2".'}"
                }
            ]
        }

        try:
            response = requests.post(URL, headers=headers, json=data)
            response.raise_for_status()

            result = response.json()
            recipe = result['result']['alternatives'][0]['message']['text']

            # Форматируем и получаем словарь ингредиентов
            formatted_recipe, ingredients_dict = format_recipe(recipe)
            return formatted_recipe, ingredients_dict

        except Exception as e:
            return f"Произошла ошибка при получении рецепта: {str(e)}", {}

def main():
    query = "карбонара на 1 человека"
    user_dict = {
        "allergies": ["бекон"],
        "unliked_products": ["яйца", "сыр"]
    }

    loop = asyncio.get_event_loop()
    formatted_recipe, ingredients_dict = loop.run_until_complete(get_recipe(query, user_dict))
    print("рецепт", formatted_recipe, '\n\n')
    print("ингредиенты: ", ingredients_dict, '\n\n')


if __name__ == "__main__":
    main()