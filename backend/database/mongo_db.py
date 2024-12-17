from pymongo import MongoClient
import certifi
import random
from typing import Optional, Dict, Any
import datetime

class MongoDBManager:
    def __init__(self, mongo_url: str, db_name: str = "recipe_bot", collection_name: str = "recipes"):
        self.client = MongoClient(mongo_url, tlsCAFile=certifi.where())
        self.db = self.client[db_name]
        self.recipes = self.db[collection_name]
        
        try:
            self.client.admin.command('ismaster')
            print("MongoDB connection successful")
        except Exception as e:
            print(f"MongoDB connection failed: {e}")
            raise

    def save_recipe(self, recipe_name: str, recipe_text: str, products: Dict[str, str], user_id: int) -> str:
        """
        Save recipe to MongoDB with user ID and timestamp
        """
        while True:
            recipe_id = str(random.randint(100000, 999999))
            existing = self.recipes.find_one({"_id": recipe_id})
            if not existing:
                break

        recipe_doc = {
            "_id": recipe_id,
            "name": recipe_name,
            "recipe": recipe_text,
            "products": products,
            "user_id": user_id,
            "timestamp": datetime.datetime.now()
        }

        self.recipes.insert_one(recipe_doc)
        return recipe_id

    def get_recipe(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        return self.recipes.find_one({"_id": recipe_id})

    def get_user_recipes(self, user_id: int, skip: int = 0, limit: int = 10) -> tuple[list[Dict[str, Any]], bool]:
        """
        Get recipes for specific user with pagination
        Returns tuple of (recipes list, has_more flag)
        """
        total = self.recipes.count_documents({"user_id": user_id})
        
        cursor = self.recipes.find({"user_id": user_id})\
                           .sort("timestamp", -1)\
                           .skip(skip)\
                           .limit(limit)
        
        recipes = list(cursor)
        has_more = total > skip + limit
        
        return recipes, has_more

    def close(self):
        self.client.close()