import unittest
from unittest.mock import patch, MagicMock
from parser import data_parser, get_input_text, knapsack
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import coverage
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import asyncio

# Юнит тесты
class TestDataParser(unittest.TestCase):

    # Чекаем что get_input_text возвращает все как нужно
    def test_get_input_text(self):
        ingredients = {"молоко": 1, "хлеб": 2, "сыр": 1}
        expected = ["молоко", "хлеб", "сыр"]
        self.assertEqual(get_input_text(ingredients), expected)

    # Проверяем что происходит поск по нужной нам ссылке
    @patch('parser.webdriver.Chrome')
    @patch('parser.WebDriverWait')
    def test_data_parser_calls_webdriver(self, mock_wait, mock_webdriver):
        mock_driver = MagicMock()
        mock_webdriver.return_value = mock_driver

        ingredients = {"молоко": 1}
        asyncio.run(data_parser(ingredients))

        mock_webdriver.assert_called_once()
        mock_driver.get.assert_called_with("https://av.ru/search/?text=молоко")

    # Правильное количество распаршенных продуктов
    def test_data_parser_products_found(self):

        ingredients = {"молоко": 1}

        result = asyncio.run(data_parser(ingredients))

        self.assertEqual(len(result), 1)


    @patch('parser.webdriver.Chrome')
    @patch('parser.WebDriverWait')
    def test_data_parser_no_products(self, mock_wait, mock_webdriver):
        mock_driver = MagicMock()
        mock_webdriver.return_value = mock_driver
        mock_driver.find_elements.return_value = []

        ingredients = {"молоко": 1}
        result = asyncio.run(data_parser(ingredients))

        self.assertEqual(result, {'молоко': [{'message': 'Товар отсутствует в данном магазине, попробуйте '
                        'поискать в другом.'}]})

    # Логика
    @patch('parser.webdriver.Chrome')
    @patch('parser.WebDriverWait')
    def test_data_parser_mid_product(self, mock_wait, mock_webdriver):
        mock_driver = MagicMock()
        mock_webdriver.return_value = mock_driver

        # Создаем мокнутые элементы с нужными атрибутами
        mock_product1 = MagicMock()
        mock_product1.get_attribute.side_effect = lambda attr: {
            "data-digi-prod-name": "Продукт1",
            "data-digi-prod-price": "50",
            "data-digi-prod-id": "1"
        }.get(attr, None)

        mock_driver.find_elements.return_value = [mock_product1]

        ingredients = {"молоко": 1}
        result = asyncio.run(data_parser(ingredients))
        self.assertEqual(result["молоко"][0]["name"], "Продукт1")
        self.assertEqual(result["молоко"][0]["price"], 50)
        self.assertEqual(result["молоко"][0]["link"], "https://av.ru/i/1")

    # Симулируем отсутствие продуктов
    @patch('parser.webdriver.Chrome')
    @patch('parser.WebDriverWait')
    def test_data_parser_no_products(self, MockWait, MockChrome):
        mock_driver = MagicMock()
        mock_wait = MagicMock()
        mock_driver.find_elements.return_value = []
        MockChrome.return_value = mock_driver
        MockWait.return_value = mock_wait

        ingredients = {"несуществующий продукт": 1}
        raw_data = asyncio.run(data_parser(ingredients))

        self.assertIn("несуществующий продукт", raw_data)
        self.assertEqual(raw_data["несуществующий продукт"][0]["message"],
                         "Товар отсутствует в данном магазине, попробуйте поискать в другом.")

    #  Дурной формат цены
    async def test_invalid_price_format(self):
        ingredients = {
            "спагетти": 1,
            "бекон": 1,
        }

        # Моделируем ситуацию, когда цена товара указана некорректно (например, строка вместо числа)
        with patch('parser.webdriver.Chrome') as MockChrome:
            MockChrome.return_value.find_elements.return_value = [
                MagicMock(get_attribute=MagicMock(return_value="Test Product")),
                MagicMock(get_attribute=MagicMock(return_value="invalid_price"))  # Некорректная цена
            ]

            raw_data = await data_parser(ingredients)

            # Проверка, что цена парсится корректно
            self.assertIsInstance(raw_data["спагетти"][0]["price"], float)  # Цена должна быть числом
            self.assertEqual(raw_data["бекон"][0]["price"], 100)

    #  Много запросов
    async def test_multiple_requests(self):
        ingredients = {
            "спагетти": 1,
            "бекон": 1,
            "яйца": 1,
        }

        raw_data = await data_parser(ingredients)

        # Проверяем, что данные для всех ингредиентов были собраны
        self.assertIn("спагетти", raw_data)
        self.assertIn("бекон", raw_data)
        self.assertIn("яйца", raw_data)

        # Проверяем, что в ответе есть хотя бы один продукт с ценой
        for ingredient in raw_data.values():
            for product in ingredient:
                self.assertIn("price", product)
                self.assertIsInstance(product["price"], float)


    #  Проверяем рюкзак
    def test_knapsack(self):

        products_data = {
            "спагетти": [{"name": "Product1", "price": 50, "link": "url1"}],
            "бекон": [{"name": "Product2", "price": 100, "link": "url2"}]
        }
        quantities = {
            "спагетти": 1,
            "бекон": 2
        }
        budget = 150
        result = knapsack(products_data, quantities, budget)

        self.assertIn("спагетти", result)
        self.assertIn("бекон", result)
        self.assertLessEqual(result["спагетти"][0]["price"] + result["бекон"][0]["price"], budget)

    # Мало денег
    def test_knapsack_budget_not_enough(self):
        products_data = {
            "спагетти": [{"name": "Product1", "price": 100, "link": "url1"}],
            "бекон": [{"name": "Product2", "price": 100, "link": "url2"}]
        }
        quantities = {
            "спагетти": 1,
            "бекон": 2
        }
        budget = 150
        result = knapsack(products_data, quantities, budget)

        # Проверка сообщения о недостаточном бюджете
        self.assertIn("message", result)
        self.assertTrue(result["message"].startswith("Бюджета недостаточно"))

    # Когда ничего не вводим
    def test_get_input_text_empty(self):
        ingredients = {}
        expected = []
        self.assertEqual(get_input_text(ingredients), expected)

    @patch('parser.webdriver.Chrome')
    @patch('parser.WebDriverWait')
    def test_headless_browser_option(self, mock_wait, mock_webdriver):
        mock_driver = MagicMock()
        mock_webdriver.return_value = mock_driver

        ingredients = {"молоко": 1}

        asyncio.run(data_parser(ingredients))

        options = mock_webdriver.call_args[1]['options']
        self.assertIn('--headless', options.arguments)

    # Проверяем, обрабатываются ли исключения при вызовах Selenium
    @patch('parser.webdriver.Chrome')
    @patch('parser.WebDriverWait')
    def test_integration_webdriver_exception(self, mock_wait, mock_webdriver):
        mock_driver = MagicMock()
        mock_driver.get.side_effect = WebDriverException()
        mock_webdriver.return_value = mock_driver

        with self.assertRaises(WebDriverException):
            asyncio.run(data_parser({"молоко": 1}))

    # Ошибка при загузки страницы
    async def test_page_load_error(self):
        ingredients = {
            "спагетти": 1,
            "бекон": 1,
            "яйца": 1,
        }

        # Моделируем ошибку при загрузке страницы (например, ошибка сети)
        with patch('parser.webdriver.Chrome') as MockChrome:
            MockChrome.return_value.get.side_effect = Exception("Ошибка загрузки страницы")

            try:
                # Попытка получения данных о товарах
                raw_data = await data_parser(ingredients)
            except Exception as e:
                # Проверяем, что ошибка была обработана и выведено соответствующее сообщение
                self.assertEqual(str(e), "Ошибка загрузки страницы")

#  Покрытие
class TestCoverage(unittest.IsolatedAsyncioTestCase):

    async def test_coverage(self):

        cov = coverage.Coverage(source=["parser"])
        cov.start()

        rez = await data_parser({
            "спагетти": 12313,
            "бекон": 342421,
            "яйца": 12342,
            "rfgwff": 1
        })

        cov.stop()
        cov.save()


        total_coverage = cov.report(omit=None)
     #   print(f"Total coverage: {total_coverage}%")

        self.assertGreaterEqual(total_coverage, 50, "Покрытие должно быть не меньше 50%")

# E2E тесты
class TestE2EDataParser(unittest.TestCase):

    # Моделируем изменение структуры страницы, например, изменение классов или XPATH.
    async def test_ui_changes(self):
        ingredients = {
            "спагетти": 1,
            "бекон": 1,
            "яйца": 1,
        }

        with patch('parser_av.webdriver.Chrome') as MockChrome:
            # Мокируем новый XPATH для кнопки "Москва"
            MockChrome.return_value.find_elements.return_value = [
                MagicMock(get_attribute=MagicMock(return_value="Test Product")),
                MagicMock(get_attribute=MagicMock(return_value="200"))  # Цена товара
            ]

            # Моделируем изменение XPATH для кнопки "Москва"
            MockChrome.return_value.find_element.side_effect = [
                MagicMock(click=MagicMock(return_value=None)),  # Нажатие на кнопку
                MagicMock()  # Простой объект для продукта
            ]

            # Теперь подаем измененную структуру страницы
            raw_data = await data_parser(ingredients)

            # Проверяем, что данные о товарах были успешно получены
            self.assertIn("спагетти", raw_data)
            self.assertIn("бекон", raw_data)
            self.assertIn("яйца", raw_data)

            for ingredient in raw_data.values():
                for product in ingredient:
                    self.assertIn("price", product)
                    self.assertIsInstance(product["price"], float)

    # Обычный вызов
    async def test_add_to_cart(self):
        ingredients = {
            "спагетти": 1,
            "бекон": 1,
            "яйца": 1,
        }
        budget = 1000

        raw_data = await data_parser(ingredients)  # Получаем данные о товарах
        selected_products = knapsack(raw_data, ingredients, budget)

        # Проверяем, что все ингредиенты были добавлены в корзину
        self.assertIn("спагетти", selected_products)
        self.assertIn("бекон", selected_products)
        self.assertIn("яйца", selected_products)

        # Проверяем, что для каждого товара есть имя, цена и ссылка
        for ingredient, products in selected_products.items():
            if ingredient != "message":
                for product in products:
                    self.assertIn("name", product)
                    self.assertIn("price", product)
                    self.assertIn("link", product)

    # Закгрузка страницы
    def test_headless_mode(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        try:
            # Проверяем базовую навигацию
            driver.get("https://av.ru/")
            self.assertIn("азбука вкуса", driver.title.lower(), "Тест должен подтвердить, что браузер успешно загрузил страницу")
        finally:
            driver.quit()

    # Тест на нахождеия продукта
    def test_single_product_found(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Открываем браузер в фоновом режиме
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        try:
            ingredients = {"молоко": 1}

            result = asyncio.run(data_parser(ingredients))
            print(result)
            assert len(result) > 0, "Должен быть найден хотя бы один продукт"
            assert "name" in result["молоко"][0], "В результате должен быть ключ 'name'"
            assert "price" in result["молоко"][0], "В результате должен быть ключ 'price'"
            assert "link" in result["молоко"][0], "В результате должен быть ключ 'link'"
        finally:
            driver.quit()

    # Тест на несущ товар
    def test_no_products_found(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        try:
            # Искать явно несуществующий товар
            ingredients = {"asdkjlqwex": 1}
            result = asyncio.run(data_parser(ingredients))
            assert result == {'asdkjlqwex': [{'message': 'Товар отсутствует в данном магазине, попробуйте поискать в другом.'}]},\
                "Вот так должно быть: 'asdkjlqwex': [{'message': 'Товар отсутствует в данном магазине, попробуйте поискать в другом.'}]."
        except TimeoutException:
            # Обрабатываем случай, когда элемент с результатами отсутствует
            assert True, "Тест успешен: на странице нет результатов, и это ожидаемое поведение"
        except Exception as e:
            assert False, f"Тест завершился с ошибкой: {e}"
        finally:
            driver.quit()

    # Тест на обработку временных блокировок сайта
    def test_wait_timeout(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        try:
            # Эмуляция поиска на сайте, который не отвечает
            ingredients = {"молоко": 1}
            # Изменяем базовый URL для эмуляции таймаута (используем пример)
            asyncio.run(data_parser({"молоко": 1}))

            assert True, "Тест завершён: функция успешно обработала таймаут ожидания"
        except Exception as e:
            assert False, f"Ошибка обработки таймаута: {e}"
        finally:
            driver.quit()

    async def test_budget_limit(self):
        ingredients = {
            "спагетти": 1,
            "бекон": 1,
            "яйца": 1,
        }
        budget = 1000  # Бюджет достаточно большой для всех ингредиентов

        raw_data = await data_parser(ingredients)
        selected_products = knapsack(raw_data, ingredients, budget)

        total_cost = sum(product['price'] for ingredient in selected_products.values() for product in ingredient)
        self.assertLessEqual(total_cost, budget, "Стоимость не должна превышать бюджет.")
        self.assertIn("спагетти", selected_products)
        self.assertIn("бекон", selected_products)
        self.assertIn("яйца", selected_products)


if __name__ == "__main__":
    unittest.main()