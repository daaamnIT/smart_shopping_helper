#Тут надо написать класс хэндлера, к которому может обращаться бот и который будет обрабатывать запросы

class Handler:
    def __init__(self):
        # self.recipe_db = 
        # self.user_db =
        # self.cache_db =
        pass

    def get_recipe_history(self, user_id):
        # return recipe history of user
        pass

    def get_favorite_recipes(self, user_id):
        # return favorite recipes of user
        pass

    def new_recipe_handler(self, user_id, recipe):
        # handles new recipe
        pass

    def edit_user_preferences(self, user_id, preferences):
        # edit user preferences
        pass

    def add_new_user(self, user_id):
        # add new user
        pass

    def get_user_preferences(self, user_id):
        # return user preferences
        pass

    #Ну тут очевидно что-то еще будет я пока не придумал что
        