import mariadb
import asyncio


class User:
    telegram_id : int
    preferences : str


    def __init__(self, telegram_id, preferences):
        self.telegram_id = telegram_id
        self.preferences = preferences


def connect():
    conn = mariadb.connect(
        user="smart_shopping",
        password="Ltybc753!!",
        host="192.168.0.105",
        database="smart_shopping",
        port=3307
    )
    return conn


def add_user(user : User):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO users (telegram_id,preferences) VALUES (?, ?)",
                          (user.telegram_id, user.preferences))
        conn.commit()


def get_all_users():
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id,telegram_id,preferences FROM users")
        for id, telegram_id, preferences in cur:
            print(id, telegram_id, preferences)

