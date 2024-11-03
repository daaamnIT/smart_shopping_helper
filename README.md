# AI Shopping Assistant (Умный помощник для покупок)

Telegram-бот с искусственным интеллектом, который помогает составлять списки покупок на основе рецептов и находить лучшие цены в магазинах.

## 🚀 Возможности

- 📝 Обработка естественных запросов для составления списка продуктов
- 🧮 Автоматический расчет количества ингредиентов под нужное число порций
- 🏪 Поиск товаров в разных магазинах и составление оптимальной корзины
- 💾 Сохранение любимых рецептов и истории заказов
- ⚡ Быстрое повторение предыдущих заказов

## 📋 Требования

- Python 3.9+
- PostgreSQL 13+
- PyMongo 4.10
- Redis 6+

## 🛠 Стек технологий

- **Backend**: 
  - FastAPI
  - MongoDB
  - redis-py
  - aiogram

- **AI & ML**:
  - YandexGPT API
  
- **Базы данных**:
  - PostgreSQL (пользовательские данные)
  - MongoDB (рецепты)
  - Redis (кэш)

## 🏗 Структура проекта

```
ai-shopping-assistant/
├── backend/
│   ├── services/
│   │   ├── ai_service/
│   │   ├── recipe_service/
│   │   ├── product_service/
│   │   └── user_service/
│   ├── models/
│   ├── database/
│   └── utils/
├── bot/
│   ├── handlers/
│   ├── keyboards/
│   └── states/
├── parsers/
│   └── stores/
└── tests/
```

## 📊 Базы данных

### PostgreSQL (User DB)
```sql
-- users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE,
    preferences JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- order_history
CREATE TABLE order_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    recipe_id TEXT,
    products_list JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### MongoDB (Recipe DB)
```javascript
// recipes
{
  _id: ObjectId,
  name: String,
  ingredients: [{
    name: String,
    quantity: Number,
    unit: String
  }],
  instructions: [String],
  portions: Number,
  time: Number
}
```

## 🗾 Схема сервиса и пользовательские сценарии
- https://miro.com/app/board/uXjVLLQNMpo=/?share_link_id=256193246257

## 🤖 Примеры использования бота

1. Запрос на создание списка продуктов:
```
Пользователь: Хочу приготовить борщ на 6 человек
Бот: Отлично! Я составил список необходимых ингредиентов для борща на 6 порций:
[список ингредиентов]
```

2. Сохранение рецепта:
```
Пользователь: Сохрани этот рецепт
Бот: Рецепт борща сохранен! Вы можете найти его в разделе "Избранное"
```

## 🤝 Участие в разработке

1. Форкните репозиторий
2. Создайте ветку для новой функциональности
3. Создайте Pull Request

## 👥 Команда

- Frontend (Telegram Bot) Developer - @daaamn1T
- Backend (AI/Recipes) Developer - @xl1ty
- Backend (Products/Parsing) Developer - @endgame_666
- Backend (Products/Parsing) Developer - @Denvelin

## 📞 Контакты

По всем вопросам: @daaamn1T
