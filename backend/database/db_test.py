import pytest
from unittest.mock import Mock, patch, AsyncMock
import datetime
import json
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo import MongoClient
from mongo_db import MongoDBManager
from sql_db import DatabaseManager
import os
import sqlite3

@pytest.fixture
def mock_mongo_client():
    with patch('mongo_db.MongoClient') as mock_client:
        mock_client.return_value.admin.command = Mock()
        mock_client.return_value.__getitem__.return_value.__getitem__.return_value = Mock(spec=Collection)
        yield mock_client

@pytest.fixture
def mongo_manager(mock_mongo_client):
    manager = MongoDBManager("mongodb://fake-url", "test_db", "test_collection")
    yield manager
    manager.close()

def test_mongodb_connection_success(mock_mongo_client):
    manager = MongoDBManager("mongodb://fake-url")
    mock_mongo_client.assert_called_once()
    assert hasattr(manager, 'recipes')

def test_mongodb_connection_failure(mock_mongo_client):
    mock_mongo_client.return_value.admin.command.side_effect = Exception("Connection failed")
    with pytest.raises(Exception) as exc_info:
        MongoDBManager("mongodb://fake-url")
    assert "Connection failed" in str(exc_info.value)

def test_save_recipe(mongo_manager):
    mongo_manager.recipes.find_one = Mock(return_value=None)
    mongo_manager.recipes.insert_one = Mock()

    recipe_id = mongo_manager.save_recipe(
        "Test Recipe",
        "Test instructions",
        {"ingredient1": "amount1"},
        123,
        {"link1": "url1"}
    )

    assert isinstance(recipe_id, str)
    assert len(recipe_id) == 6
    mongo_manager.recipes.insert_one.assert_called_once()

def test_get_recipe(mongo_manager):
    expected_recipe = {
        "_id": "123456",
        "name": "Test Recipe",
        "recipe": "Test instructions",
        "products": {"ingredient1": "amount1"}
    }
    mongo_manager.recipes.find_one = Mock(return_value=expected_recipe)

    recipe = mongo_manager.get_recipe("123456")
    assert recipe == expected_recipe
    mongo_manager.recipes.find_one.assert_called_once_with({"_id": "123456"})

def test_get_user_recipes(mongo_manager):
    mock_recipes = [{"_id": "1"}, {"_id": "2"}]
    mock_cursor = Mock()
    mock_cursor.sort.return_value.skip.return_value.limit.return_value = mock_recipes
    mongo_manager.recipes.find = Mock(return_value=mock_cursor)
    mongo_manager.recipes.count_documents = Mock(return_value=3)

    recipes, has_more = mongo_manager.get_user_recipes(123, skip=0, limit=2)
    assert recipes == mock_recipes
    assert has_more is True
    mongo_manager.recipes.count_documents.assert_called_once_with({"user_id": 123})

def test_toggle_favorite(mongo_manager):
    mock_recipe = {"_id": "123456", "favorite_by": []}
    mongo_manager.recipes.find_one = Mock(return_value=mock_recipe)
    mongo_manager.recipes.update_one = Mock()

    result = mongo_manager.toggle_favorite("123456", 123)
    assert result is True
    mongo_manager.recipes.update_one.assert_called_once()

    mock_recipe["favorite_by"] = [123]
    result = mongo_manager.toggle_favorite("123456", 123)
    assert result is False

def test_is_favorite(mongo_manager):
    mock_recipe = {"_id": "123456", "favorite_by": [123]}
    mongo_manager.recipes.find_one = Mock(return_value=mock_recipe)

    assert mongo_manager.is_favorite("123456", 123) is True
    assert mongo_manager.is_favorite("123456", 456) is False

class DatabaseManager:
    def __init__(self, db_name: str = "bot.db"):
        self.db_name = db_name
        self._create_tables()

    def _create_tables(self):
        with sqlite3.connect(self.db_name) as conn:
            conn.execute('''
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

    def add_user(self, user_id: int, user_name: str, language: str) -> bool:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
            exists = cursor.fetchone()
            
            if not exists:
                cursor.execute('''
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
                conn.commit()
                return True
            return False

    def get_user(self, user_id: int) -> dict:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            
            if user:
                column_names = [description[0] for description in cursor.description]
                user_dict = dict(zip(column_names, user))
                user_dict['recipe_history'] = json.loads(user_dict['recipe_history'])
                user_dict['favourite_recipes'] = json.loads(user_dict['favourite_recipes'])
                user_dict['allergies'] = json.loads(user_dict['allergies'])
                user_dict['unliked_products'] = json.loads(user_dict['unliked_products'])
                return user_dict
            return None

    def update_user_preferences(self, user_id: int, allergies: list = None, 
                              max_price: int = None, unliked_products: list = None):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            if allergies is not None:
                cursor.execute(
                    'UPDATE users SET allergies = ? WHERE user_id = ?',
                    (json.dumps(allergies), user_id)
                )
            
            if max_price is not None:
                cursor.execute(
                    'UPDATE users SET max_price = ? WHERE user_id = ?',
                    (max_price, user_id)
                )
            
            if unliked_products is not None:
                cursor.execute(
                    'UPDATE users SET unliked_products = ? WHERE user_id = ?',
                    (json.dumps(unliked_products), user_id)
                )
            
            conn.commit()

    def update_recipe_history(self, user_id: int, recipe_id: str):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT recipe_history FROM users WHERE user_id = ?',
                (user_id,)
            )
            history_json = cursor.fetchone()
            
            if history_json:
                history = json.loads(history_json[0])
                if recipe_id not in history:
                    history.append(recipe_id)
                    cursor.execute(
                        'UPDATE users SET recipe_history = ? WHERE user_id = ?',
                        (json.dumps(history), user_id)
                    )
                    conn.commit()

    def update_favourite_recipes(self, user_id: int, recipe_id: str):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT favourite_recipes FROM users WHERE user_id = ?',
                (user_id,)
            )
            favourites_json = cursor.fetchone()
            
            if favourites_json:
                favourites = json.loads(favourites_json[0])
                if recipe_id not in favourites:
                    favourites.append(recipe_id)
                    cursor.execute(
                        'UPDATE users SET favourite_recipes = ? WHERE user_id = ?',
                        (json.dumps(favourites), user_id)
                    )
                    conn.commit()

    def get_formatted_preferences(self, user_id: int) -> str:
        user_data = self.get_user(user_id)
        if not user_data:
            return "Предпочтения не найдены"
        
        allergies = user_data['allergies']
        allergies_text = "Аллергия:\n" + "\n".join(allergies) if allergies else "Аллергия:\nНе указано"
        
        unliked = user_data['unliked_products']
        unliked_text = "\n\nНелюбимые продукты:\n" + "\n".join(unliked) if unliked else "\n\nНелюбимые продукты:\nНе указано"
        
        price_text = f"\n\nОграничение цены:\n{user_data['max_price']} руб." if user_data['max_price'] else "\n\nОграничение цены:\nНе указано"
        
        return allergies_text + unliked_text + price_text


@pytest.fixture
def db_manager():
    test_db = "test_bot.db"
    manager = DatabaseManager(test_db)
    yield manager
    try:
        os.remove(test_db)
    except FileNotFoundError:
        pass

def test_add_user(db_manager):
    result = db_manager.add_user(1, "test_user", "en")
    assert result is True
    
    result = db_manager.add_user(1, "test_user", "en")
    assert result is False
    
    user = db_manager.get_user(1)
    assert user is not None
    assert user["user_id"] == 1
    assert user["user_name"] == "test_user"
    assert user["language"] == "en"
    assert user["recipe_history"] == []
    assert user["favourite_recipes"] == []
    assert user["allergies"] == []
    assert user["unliked_products"] == []

def test_get_user(db_manager):
    db_manager.add_user(1, "test_user", "en")
    
    user = db_manager.get_user(1)
    assert user is not None
    assert user["user_id"] == 1
    
    user = db_manager.get_user(999)
    assert user is None

def test_update_user_preferences(db_manager):
    db_manager.add_user(1, "test_user", "en")
    
    allergies = ["nuts", "milk"]
    db_manager.update_user_preferences(1, allergies=allergies)
    user = db_manager.get_user(1)
    assert user["allergies"] == allergies
    
    db_manager.update_user_preferences(1, max_price=1000)
    user = db_manager.get_user(1)
    assert user["max_price"] == 1000
    
    unliked = ["onion", "garlic"]
    db_manager.update_user_preferences(1, unliked_products=unliked)
    user = db_manager.get_user(1)
    assert user["unliked_products"] == unliked
    
    db_manager.update_user_preferences(
        1, 
        allergies=["eggs"],
        max_price=500,
        unliked_products=["mushrooms"]
    )
    user = db_manager.get_user(1)
    assert user["allergies"] == ["eggs"]
    assert user["max_price"] == 500
    assert user["unliked_products"] == ["mushrooms"]

def test_update_recipe_history(db_manager):
    db_manager.add_user(1, "test_user", "en")
    
    db_manager.update_recipe_history(1, "recipe1")
    user = db_manager.get_user(1)
    assert "recipe1" in user["recipe_history"]
    
    db_manager.update_recipe_history(1, "recipe1")
    user = db_manager.get_user(1)
    assert user["recipe_history"].count("recipe1") == 1
    
    db_manager.update_recipe_history(1, "recipe2")
    user = db_manager.get_user(1)
    assert len(user["recipe_history"]) == 2
    assert "recipe1" in user["recipe_history"]
    assert "recipe2" in user["recipe_history"]

def test_update_favourite_recipes(db_manager):
    db_manager.add_user(1, "test_user", "en")
    
    db_manager.update_favourite_recipes(1, "recipe1")
    user = db_manager.get_user(1)
    assert "recipe1" in user["favourite_recipes"]
    
    db_manager.update_favourite_recipes(1, "recipe1")
    user = db_manager.get_user(1)
    assert user["favourite_recipes"].count("recipe1") == 1
    
    db_manager.update_favourite_recipes(1, "recipe2")
    user = db_manager.get_user(1)
    assert len(user["favourite_recipes"]) == 2
    assert "recipe1" in user["favourite_recipes"]
    assert "recipe2" in user["favourite_recipes"]

def test_get_formatted_preferences(db_manager):
    db_manager.add_user(1, "test_user", "en")
    db_manager.update_user_preferences(
        1,
        allergies=["nuts", "milk"],
        max_price=1000,
        unliked_products=["onion", "garlic"]
    )
    
    formatted = db_manager.get_formatted_preferences(1)
    assert "Аллергия:\nnuts\nmilk" in formatted
    assert "Нелюбимые продукты:\nonion\ngarlic" in formatted
    assert "Ограничение цены:\n1000 руб." in formatted
    
    db_manager.add_user(2, "test_user2", "en")
    formatted = db_manager.get_formatted_preferences(2)
    assert "Аллергия:\nНе указано" in formatted
    assert "Нелюбимые продукты:\nНе указано" in formatted
    assert "Ограничение цены:\nНе указано" in formatted

def test_database_connection_error():
    with patch('sqlite3.connect', side_effect=sqlite3.Error):
        with pytest.raises(sqlite3.Error):
            db_manager = DatabaseManager("test_bot.db")
            db_manager.add_user(1, "test_user", "en")

if __name__ == "__main__":
    pytest.main(["-v"])