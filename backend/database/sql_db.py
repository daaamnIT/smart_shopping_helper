import sqlite3
import json
from typing import List, Optional
import aiosqlite

class DatabaseManager:
    def __init__(self, db_name: str = "bot.db"):
        self.db_name = db_name
        self._create_tables()

    def _create_tables(self):
        """Create necessary tables if they don't exist."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    user_name TEXT,
                    language TEXT,
                    recipe_history TEXT,
                    favourite_recipes TEXT,
                    allergies TEXT,
                    max_price INTEGER DEFAULT 0,
                    unliked_products TEXT
                )
            ''')
            
            conn.commit()

    async def add_user(self, user_id: int, user_name: str, language: str) -> bool:
        """Add new user to database if not exists."""
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                'SELECT user_id FROM users WHERE user_id = ?', 
                (user_id,)
            )
            exists = await cursor.fetchone()
            
            if not exists:
                await db.execute('''
                    INSERT INTO users (
                        user_id, user_name, language, 
                        recipe_history, favourite_recipes, 
                        allergies, unliked_products
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, user_name, language,
                    json.dumps([]),
                    json.dumps([]),
                    json.dumps([]),
                    json.dumps([])
                ))
                await db.commit()
                return True
            return False

    async def get_user(self, user_id: int) -> Optional[dict]:
        """Get user data by user_id."""
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                'SELECT * FROM users WHERE user_id = ?', 
                (user_id,)
            )
            user = await cursor.fetchone()
            
            if user:
                column_names = [description[0] for description in cursor.description]
                user_dict = dict(zip(column_names, user))
                user_dict['recipe_history'] = json.loads(user_dict['recipe_history'])
                user_dict['favourite_recipes'] = json.loads(user_dict['favourite_recipes'])
                user_dict['allergies'] = json.loads(user_dict['allergies'])
                user_dict['unliked_products'] = json.loads(user_dict['unliked_products'])
                return user_dict
            return None

    async def update_user_preferences(self, user_id: int, allergies: List[str] = None, 
                                    max_price: int = None, unliked_products: List[str] = None):
        """Update user preferences."""
        async with aiosqlite.connect(self.db_name) as db:
            if allergies is not None:
                await db.execute(
                    'UPDATE users SET allergies = ? WHERE user_id = ?',
                    (json.dumps(allergies), user_id)
                )
            
            if max_price is not None:
                await db.execute(
                    'UPDATE users SET max_price = ? WHERE user_id = ?',
                    (max_price, user_id)
                )
            
            if unliked_products is not None:
                await db.execute(
                    'UPDATE users SET unliked_products = ? WHERE user_id = ?',
                    (json.dumps(unliked_products), user_id)
                )
            
            await db.commit()

    async def update_recipe_history(self, user_id: int, recipe_id: str):
        """Add recipe to user's history."""
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                'SELECT recipe_history FROM users WHERE user_id = ?',
                (user_id,)
            )
            history_json = await cursor.fetchone()
            
            if history_json:
                history = json.loads(history_json[0])
                if recipe_id not in history:
                    history.append(recipe_id)
                    await db.execute(
                        'UPDATE users SET recipe_history = ? WHERE user_id = ?',
                        (json.dumps(history), user_id)
                    )
                    await db.commit()

    async def update_favourite_recipes(self, user_id: int, recipe_id: str):
        """Add recipe to user's favourites."""
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                'SELECT favourite_recipes FROM users WHERE user_id = ?',
                (user_id,)
            )
            favourites_json = await cursor.fetchone()
            
            if favourites_json:
                favourites = json.loads(favourites_json[0])
                if recipe_id not in favourites:
                    favourites.append(recipe_id)
                    await db.execute(
                        'UPDATE users SET favourite_recipes = ? WHERE user_id = ?',
                        (json.dumps(favourites), user_id)
                    )
                    await db.commit()

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