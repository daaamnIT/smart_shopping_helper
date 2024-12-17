from .database.sql_db import DatabaseManager
from .database.mongo_db import MongoDBManager
from .database.setting import connection

class Handler:
    def __init__(self):
        self.user_db = DatabaseManager()
        mongo_url = connection
        self.recipe_db = MongoDBManager(
            mongo_url=mongo_url,
            db_name="recipe_bot",
            collection_name="recipes"
        )

    async def get_recipe_history(self, user_id, offset: int = 0, limit: int = 10):
        """Get paginated recipe history for user directly from MongoDB"""
        recipes, has_more = self.recipe_db.get_user_recipes(user_id, skip=offset, limit=limit)
        return recipes, has_more

    async def new_recipe_handler(self, user_id, recipe_data):
        recipe_id = self.recipe_db.save_recipe(
            recipe_name=recipe_data['request'],
            recipe_text=recipe_data['text'],
            products=recipe_data['ingredients'],
            user_id=user_id
        )
        return recipe_id

    async def get_recipe_by_id(self, recipe_id: str):
        """Get single recipe by ID"""
        return self.recipe_db.get_recipe(recipe_id)

    async def add_new_user(self, user_id, user_name: str = "", language: str = "en"):
        await self.user_db.add_user(user_id, user_name, language)

    async def get_user_preferences(self, user_id):
        return await self.user_db.get_user(user_id)

    async def update_user_allergies(self, user_id: int, allergies: list):
        await self.user_db.update_user_preferences(user_id, allergies=allergies)

    async def update_price_limit(self, user_id: int, price_limit: int):
        await self.user_db.update_user_preferences(user_id, max_price=price_limit)

    async def update_disliked_products(self, user_id: int, disliked_products: list):
        await self.user_db.update_user_preferences(user_id, unliked_products=disliked_products)

    async def get_formatted_preferences(self, user_id: int) -> str:
        user_data = await self.user_db.get_user(user_id)
        if not user_data:
            return "Предпочтения не найдены"
        
        allergies = user_data['allergies']
        allergies_text = "Аллергия:\n" + "\n".join(allergies) if allergies else "Аллергия:\nНе указано"
        
        unliked = user_data['unliked_products']
        unliked_text = "\n\nНелюбимые продукты:\n" + "\n".join(unliked) if unliked else "\n\nНелюбимые продукты:\nНе указано"
        
        price_text = f"\n\nОграничение цены:\n{user_data['max_price']} руб." if user_data['max_price'] else "\n\nОграничение цены:\nНе указано"
        
        return allergies_text + unliked_text + price_text

    def __del__(self):
        self.recipe_db.close()