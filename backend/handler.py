from .database.sql_db import DatabaseManager

class Handler:
    def __init__(self):
        self.db = DatabaseManager()

    async def get_recipe_history(self, user_id):
        user_data = await self.db.get_user(user_id)
        if user_data and user_data['recipe_history']:
            return "\n".join(user_data['recipe_history'])
        return None

    async def get_favorite_recipes(self, user_id):
        user_data = await self.db.get_user(user_id)
        if user_data and user_data['favourite_recipes']:
            return "\n".join(user_data['favourite_recipes'])
        return None

    async def new_recipe_handler(self, user_id, recipe):
        recipe_id = recipe['request']
        await self.db.update_recipe_history(user_id, recipe_id)

    async def edit_user_preferences(self, user_id, preferences):
        await self.db.update_user_preferences(
            user_id,
            allergies=preferences.get('allergies'),
            max_price=preferences.get('max_price'),
            unliked_products=preferences.get('unliked_products')
        )

    async def add_new_user(self, user_id, username, language):
        await self.db.add_user(user_id, username, language)

    async def get_user_preferences(self, user_id):
        return await self.db.get_user(user_id)

    async def update_user_allergies(self, user_id: int, allergies: list):
        await self.db.update_user_preferences(user_id, allergies=allergies)

    async def update_price_limit(self, user_id: int, price_limit: int):
        await self.db.update_user_preferences(user_id, max_price=price_limit)

    async def update_disliked_products(self, user_id: int, disliked_products: list):
        await self.db.update_user_preferences(user_id, unliked_products=disliked_products)

    async def get_formatted_preferences(self, user_id: int) -> str:
        """Get user preferences formatted as a readable message."""
        user_data = await self.db.get_user(user_id)
        if not user_data:
            return "Предпочтения не найдены"
        
        allergies = user_data['allergies']
        allergies_text = "Аллергия:\n" + "\n".join(allergies) if allergies else "Аллергия:\nНе указано"
        
        unliked = user_data['unliked_products']
        unliked_text = "\n\nНелюбимые продукты:\n" + "\n".join(unliked) if unliked else "\n\nНелюбимые продукты:\nНе указано"
        
        price_text = f"\n\nОграничение цены:\n{user_data['max_price']} руб." if user_data['max_price'] else "\n\nОграничение цены:\nНе указано"
        
        return allergies_text + unliked_text + price_text