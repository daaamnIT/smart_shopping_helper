from aiogram.filters.callback_data import CallbackData

class RecipeCallback(CallbackData, prefix="recipe"):
    action: str
    id: str