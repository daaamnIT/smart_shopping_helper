def welcome_message(message):
    return (
        f"{message.from_user.full_name}, добро пожаловать! Выберите действие:"
    )


buttons = {
    "new_recipe": "🆕 Новый рецепт",
    "favorite_recipes": "⭐️ Избранные рецепты",
    "recipe_history": "📜 История рецептов",
    "preferences": "⚙️ Личные предпочтения",
}

new_recipe_response = "Введите название блюда и количество порций"
favourite_recipes_response = "Избранные рецепты:"
recipe_history_response = "История ваших рецептов:"
preferences_response = "Настройки личных предпочтений:"

preferences = {
    "allergies": "Аллергия",
    "price_limit": "Ограничение цены",
    "disliked_products": "Нелюбимые продукты",
    "view_preferences": "Посмотреть мои предпочтения",
    "back": "Назад",
}