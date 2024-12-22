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

        if flag:
            try:
                moscow_button = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//div[@class='button_content' and contains(text(), 'Москва')]")
                ))
                moscow_button.click()
                flag = False
            except Exception as e:
                print(f"Couldn't click Moscow button: {e}")

        try:
            wait.until(EC.presence_of_element_located((By.XPATH, "//div[@data-digi-type='productsSearch']")))
            products = driver.find_elements(By.XPATH, "//div[@data-digi-type='productsSearch']")
        except Exception as e:
            print(f"Error waiting for products: {e}")
            products = []

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
        else:
            results[el] = [{"message": "Товар отсутствует в данном магазине, попробуйте поискать в другом."}]

    driver.quit()
    return results


# Наш рюкзак
def knapsack(products_data: dict[str, list[dict]], quantities: dict, budget: float) -> dict:
    selected_products = {}
    total_cost = 0
    final_cost = 0  # Итоговая стоимость
    insufficient_budget = False

    for ingredient in quantities.keys():  # Перебираем только названия ингредиентов
        if ingredient in products_data:
            valid_products = [
                product for product in products_data[ingredient] if 'price' in product
            ]

            if valid_products:
                best_product = min(valid_products, key=lambda x: x['price'])
                selected_products[ingredient] = [best_product]
                final_cost += best_product['price']

                if total_cost + best_product['price'] <= budget:
                    total_cost += best_product['price']
                else:
                    insufficient_budget = True
            else:
                selected_products[ingredient] = [
                    {"message": "Товар отсутствует в данном магазине, попробуйте поискать в другом."}
                ]
        else:
            selected_products[ingredient] = [
                {"message": "Товар отсутствует в данном магазине, попробуйте поискать в другом."}
            ]

    # Если мало денег
    if insufficient_budget:
        selected_products["message"] = (
            f"Бюджета недостаточно для покупки всех ингредиентов. "
            f"Итоговая стоимость всех продуктов: {final_cost:.2f} RUB. "
            f"Попробуйте увеличить бюджет."
        )

    return selected_products


# Тестил на яблочном штруделе
if __name__ == "__main__":
    ingredients_example = {
        "спагетти": 12313,
        "бекон": 342421,
        "яйца": 12342,
        "сливки": 1,
        "тёртый сыр": 1,
        "чеснок": 2,
        "fafafaf": 1,
        "соль": 1,
        "перец": 1
    }
    budget = 10  # бюджет (маленький, не хватит)

    raw_data = asyncio.run(data_parser(ingredients_example))
    chosen_products = knapsack(raw_data, ingredients_example, budget)

    print("Продукты:")
    for ingredient, products in chosen_products.items():
        if ingredient == "message":
            print(products)
        else:
            print(f"{ingredient.capitalize()}:")
            for product in products:
                if "name" in product and "price" in product and "link" in product:
                    print(f"  - {product['name']} | {product['price']} RUB | {product['link']}")
                elif "message" in product:
                    print(f"  - {product['message']}")