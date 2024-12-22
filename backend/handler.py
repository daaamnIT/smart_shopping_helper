from .database.sql_db import DatabaseManager
from .database.mongo_db import MongoDBManager
from .database.setting import connection
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton # type: ignore
from bot.paste import RecipeCallback



class Handler:
    def __init__(self):
        self.user_db = DatabaseManager()
        mongo_url = connection
        self.recipe_db = MongoDBManager(
            mongo_url=mongo_url,
            db_name="recipe_bot",
            collection_name="recipes"
        )

    async def get_recipe_history(self, user_id, offset: int = 0, limit: int = 3):
        """Get paginated recipe history for user directly from MongoDB"""
        recipes, has_more = self.recipe_db.get_user_recipes(user_id, skip=offset, limit=limit)
        return recipes, has_more

    async def new_recipe_handler(self, user_id, recipe_data):
        product_links = {}
        if 'links' in recipe_data:
            for category, products in recipe_data['links'].items():
                if not isinstance(products, list):
                    continue
                    
                for product in products:
                    if not isinstance(product, dict):
                        continue
                        
                    if 'message' in product:
                        product_links[category] = product['message']
                        
                    if product.get('name') and product.get('link'):
                        product_links[product['name']] = {
                            'link': product['link'],
                            'price': product.get('price', 'Цена не указана')
                        }

        recipe_id = self.recipe_db.save_recipe(
            recipe_name=recipe_data['request'],
            recipe_text=recipe_data['text'],
            products=recipe_data['ingredients'],
            user_id=user_id,
            product_links=product_links
        )
        return recipe_id
    
    async def format_recipe_with_links(self, recipe: dict) -> str:
        base_text = f"🍳 {recipe['name']}\n\n{recipe['recipe']}"
        
        if recipe.get('product_links'):
            base_text += "\n\nСсылки на продукты:\n"
            for product_name, info in recipe['product_links'].items():
                base_text += f"\n{product_name.replace('+', ' ')}\n"
                if isinstance(info, str):
                    base_text += f"{info}\n"
                else:
                    base_text += f"Цена: {info.get('price', 'Цена не указана')}\n"
                    base_text += f"Ссылка: {info.get('link', 'Ссылка отсутствует')}\n"
        
        return base_text
    
    async def toggle_favorite_recipe(self, user_id: int, recipe_id: str) -> bool:
        return self.recipe_db.toggle_favorite(recipe_id, user_id)

    async def is_recipe_favorite(self, user_id: int, recipe_id: str) -> bool:
        return self.recipe_db.is_favorite(recipe_id, user_id)

    async def get_favorite_recipes(self, user_id: int) -> list:
        favorites = self.recipe_db.get_user_favorites(user_id)
        if not favorites:
            return []
        return favorites

    async def get_recipe_by_id(self, recipe_id: str):
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
    
    def create_recipe_keyboard(self, recipe_id: str, user_id: int, show_full=True) -> InlineKeyboardMarkup:
        is_favorite = self.recipe_db.is_favorite(recipe_id, user_id)
        favorite_text = "❌ Убрать из избранного" if is_favorite else "⭐️ Добавить в избранное"
        
        buttons = []
        if show_full:
            buttons.append([
                InlineKeyboardButton(
                    text="Получить полный рецепт",
                    callback_data=RecipeCallback(action="get_full", id=recipe_id).pack()
                )
            ])
        
        buttons.append([
            InlineKeyboardButton(
                text=favorite_text,
                callback_data=RecipeCallback(action="toggle_favorite", id=recipe_id).pack()
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    

    def __del__(self):
        self.recipe_db.close()