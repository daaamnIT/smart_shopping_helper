from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import asyncio

def get_input_text(ingredients: dict) -> list[str]:
    products = []
    for key in ingredients.keys():
        products.append(key)
    return products

async def data_parser(ingredients: dict) -> dict[str, list[dict]]:
    options = Options()
    options.add_argument('--headless')
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    )
    ingredients = get_input_text(ingredients)
    results = {}

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    flag = True
    for el in ingredients:
        base_url = f"https://av.ru/search/?text={el}"
        print(f"Searching for: {el} at {base_url}")

        driver.get(base_url)

        wait = WebDriverWait(driver, 10)

        if flag:  # Добавил флаг а то Москва то появляется то нет
            try:
                moscow_button = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//div[@class='button_content' and contains(text(), 'Москва')]")
                ))
                moscow_button.click()
                flag = False
            except Exception as e:
                print(f"Couldn't click Moscow button: {e}")

        wait.until(EC.presence_of_element_located((By.XPATH, "//div[@data-digi-type='productsSearch']")))

        products = driver.find_elements(By.XPATH, "//div[@data-digi-type='productsSearch']")
        product_data = []

        for product in products[:5]:
            try:
                product_name = product.get_attribute("data-digi-prod-name")
                product_price = product.get_attribute("data-digi-prod-price")
                product_id = product.get_attribute("data-digi-prod-id")

                product_link = f"https://av.ru/i/{product_id}"

                if product_name and product_price:
                    product_data.append({
                        "name": product_name,
                        "price": float(product_price),
                        "link": product_link
                    })
            except Exception as e:
                print(f"Error extracting product data: {e}")

        if product_data:
            results[el] = product_data

    driver.quit()
    return results

# Наш рюкзак
def knapsack(products_data: dict[str, list[dict]], quantities: dict, budget: float) -> dict:
    selected_products = {}
    total_cost = 0
    insufficient_budget = False

    for ingredient, required_quantity in quantities.items():
        if ingredient in products_data:
            affordable_products = sorted(products_data[ingredient], key=lambda x: x['price'])
            selected_products[ingredient] = []

            for product in affordable_products:
                if len(selected_products[ingredient]) < required_quantity and total_cost + product['price'] <= budget:
                    selected_products[ingredient].append(product)
                    total_cost += product['price']

            if len(selected_products[ingredient]) < required_quantity:
                insufficient_budget = True
        else:
            selected_products[ingredient] = []
            insufficient_budget = True

    # Если бюджет закончился
    if insufficient_budget:
        selected_products["message"] = "Бюджета недостаточно для покупки всех ингредиентов. Попробуйте увеличить бюджет."

    return selected_products

# Тестил на яблочном штруделе
if __name__ == "__main__":
    ingredients_example = {
        "яблоки": 1,
        "тесто фило": 1,
        "сахар": 1,
        "корица": 1,
        "сухари панировочные": 1,
        "масло сливочное": 1,
        "яйцо": 1,
        "лимонный сок": 1
    }
    budget = 1000  # бюджет (маленький, не хватит)

    raw_data = asyncio.run(data_parser(ingredients_example))
    chosen_products = knapsack(raw_data, ingredients_example, budget)

    print("Продукты:")
    for ingredient, products in chosen_products.items():
        if ingredient == "message":
            print(products)  # Если не хватило денег просто выводим название продукта
        else:
            print(f"{ingredient.capitalize()}:")
            for product in products:
                print(f"  - {product['name']} | {product['price']} RUB | {product['link']}")
