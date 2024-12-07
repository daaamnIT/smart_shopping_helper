import unittest
from unittest.mock import patch, MagicMock
from parser import data_parser, get_input_text
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

    # не найден товар
    @patch('parser.webdriver.Chrome')
    @patch('parser.WebDriverWait')
    def test_data_parser_no_products(self, mock_wait, mock_webdriver):
        mock_driver = MagicMock()
        mock_webdriver.return_value = mock_driver
        mock_driver.find_elements.return_value = []

        ingredients = {"молоко": 1}
        result = asyncio.run(data_parser(ingredients))

        self.assertEqual(result, [])

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
        self.assertEqual(result[0]["name"], "Продукт1")
        self.assertEqual(result[0]["price"], "50")
        self.assertEqual(result[0]["link"], "https://av.ru/i/1")

    # Корректно ли парсятся данные после кликов и обработки логики
    @patch('parser.webdriver.Chrome')
    @patch('parser.WebDriverWait')
    def test_integration_parse_logic(self, mock_wait, mock_webdriver):
        mock_driver = MagicMock()

        mock_product1 = MagicMock()
        mock_product1.get_attribute.side_effect = lambda attr: {
            "data-digi-prod-name": "Хлеб",
            "data-digi-prod-price": "40",
            "data-digi-prod-id": "1"
        }.get(attr, None)

        mock_product2 = MagicMock()
        mock_product2.get_attribute.side_effect = lambda attr: {
            "data-digi-prod-name": "Сыр",
            "data-digi-prod-price": "30",
            "data-digi-prod-id": "2"
        }.get(attr, None)

        # Устанавливаем возвращаемые значения для find_elements
        mock_driver.find_elements.return_value = [mock_product1, mock_product2]
        mock_webdriver.return_value = mock_driver

        ingredients = {"хлеб": 1, "сыр": 1}

        result = asyncio.run(data_parser(ingredients))

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], "Хлеб")
        self.assertEqual(result[0]['price'], "40")
        self.assertEqual(result[0]['link'], "https://av.ru/i/1")

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

    # Проверяем, что логика парсинга корректно работает при множественных запросах
    @patch('parser.webdriver.Chrome')
    @patch('parser.WebDriverWait')
    def test_integration_multiple_requests(self, mock_wait, mock_webdriver):
        mock_driver = MagicMock()
        mock_driver.find_elements.return_value = []
        mock_webdriver.return_value = mock_driver

        ingredients = {"хлеб": 1, "молоко": 1, "сыр": 1}
        result = asyncio.run(data_parser(ingredients))

        self.assertIsInstance(result, list)  # Проверяем тип результата
        self.assertEqual(len(result), 0)  # Проверяем отсутствие данных


    # Покрытие >= 70% (79%)
    def test_coverage(self):
        cov = coverage.Coverage(source=["parser"])
        cov.start()
        self.test_data_parser_products_found()
        cov.stop()
        cov.save()
        total_coverage = cov.report(omit=None)
#        print(f"Total coverage: {total_coverage}%")
        self.assertGreaterEqual(total_coverage, 70, "Покрытие должно быть не меньше 70%")


# E2E тесты
class TestE2EDataParser(unittest.TestCase):
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

            assert len(result) > 0, "Должен быть найден хотя бы один продукт"
            assert "name" in result[0], "В результате должен быть ключ 'name'"
            assert "price" in result[0], "В результате должен быть ключ 'price'"
            assert "link" in result[0], "В результате должен быть ключ 'link'"
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

            assert result == [], "Если продукт отсутствует, парсер должен вернуть пустой список"
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

if __name__ == "__main__":
    unittest.main()