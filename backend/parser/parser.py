from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# from backend.services.ai_service.ai import get_recipe
#
# recipe_text, ingredients = get_recipe()

def get_input_text(ingredients: dict) -> list[str]:
    products = []
    for key in ingredients.keys():
        products.append(key)
    return products


def data_parser(ingredients: dict) -> list[dict]:
    """
    Получает запрос вида "молоко" и возвращает словарь со ссылкой на этот продукт с сайта https://av.ru/
    :param input_text: искомый продукт
    :return: список словарей, [{name: str, price: int | float, link: str}]
    """
    options = Options()
    options.add_argument('--headless')
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    )
    ingredients = get_input_text(ingredients)
    purchases = []
    for el in ingredients:
        base_url = f"https://av.ru/search/?text={el}"

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(base_url)

        wait = WebDriverWait(driver, 1)
        moscow_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@class='button_content' and contains(text(), 'Москва')]")))
        moscow_button.click()

        products = driver.find_elements(By.XPATH, "//div[@data-digi-type='productsSearch']")
        product_data = []

        for product in products:
            try:
                name_element = product.find_element(By.XPATH, ".//div[@class='product-info_name']//a")
                product_name = name_element.text
                price_element = product.find_element(By.XPATH, ".//div[@class='product-price_current-price']//div[@class='price']")
                product_price = price_element.text.strip()
                product_link = name_element.get_attribute("href")

                product_data.append({
                    "name": product_name,
                    "price": product_price,
                    "link": product_link
                })
            except Exception as e:
                print(f"Ошибка при извлечении данных о товаре: {e}")

        if product_data:
            product_data.sort(key=lambda x: x['price'])
            mid_index = len(product_data) // 2
            mid_product = product_data[mid_index]
            purchases.append(mid_product)
    return purchases
