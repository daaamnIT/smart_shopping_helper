from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

def get_input_text(ingredients: dict) -> list[str]:
    products = []
    for key in ingredients.keys():
        products.append(key)
    return products

async def data_parser(ingredients: dict) -> list[dict]:
    options = Options()
    options.add_argument('--headless')
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    )
    ingredients = get_input_text(ingredients)
    purchases = []
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    for el in ingredients:
        base_url = f"https://av.ru/search/?text={el}"
        print(base_url)

        driver.get(base_url)

        wait = WebDriverWait(driver, 10)
        
        try:
            moscow_button = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//div[@class='button_content' and contains(text(), 'Москва')]")
            ))
            moscow_button.click()
        except Exception as e:
            print(f"Couldn't click Moscow button: {e}")

        wait.until(EC.presence_of_element_located((By.XPATH, "//div[@data-digi-type='productsSearch']")))

        products = driver.find_elements(By.XPATH, "//div[@data-digi-type='productsSearch']")
        product_data = []

        for product in products:
            try:
                product_name = product.get_attribute("data-digi-prod-name")
                product_price = product.get_attribute("data-digi-prod-price")
                product_id = product.get_attribute("data-digi-prod-id")
                
                product_link = f"https://av.ru/i/{product_id}"

                if product_name and product_price:
                    product_data.append({
                        "name": product_name,
                        "price": product_price,
                        "link": product_link
                    })
            except Exception as e:
                print(f"Error extracting product data: {e}")

        if product_data:
            product_data.sort(key=lambda x: float(x['price']))
            mid_index = len(product_data) // 2
            mid_product = product_data[mid_index]
            purchases.append(mid_product)
    
    driver.quit()
    return purchases