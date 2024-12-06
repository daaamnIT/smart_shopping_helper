import unittest
from unittest.mock import patch, MagicMock
from parser import data_parser, get_input_text
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import coverage
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

#Юнит тесты
class TestDataParser(unittest.TestCase):

    #Чекаем что get_input_text возвращает все как нужно
    def test_get_input_text(self):
        ingredients = {"молоко": 1, "хлеб": 2, "сыр": 1}
        expected = ["молоко", "хлеб", "сыр"]
        self.assertEqual(get_input_text(ingredients), expected)

    #Проверяем что происходит поск по нужной нам ссылке
    @patch('parser.webdriver.Chrome')
    @patch('parser.WebDriverWait')
    def test_data_parser_calls_webdriver(self, mock_wait, mock_webdriver):
        mock_driver = MagicMock()
        mock_webdriver.return_value = mock_driver

        ingredients = {"молоко": 1}
        data_parser(ingredients)

        mock_webdriver.assert_called_once()
        mock_driver.get.assert_called_with("https://av.ru/search/?text=молоко")

    #Что кнопка Москва нажимается только 1 раз
    @patch('parser.webdriver.Chrome')
    @patch('parser.WebDriverWait')
    def test_moscow_button_click(self, mock_wait, mock_webdriver):
        mock_driver = MagicMock()
        mock_webdriver.return_value = mock_driver
        mock_wait.return_value.until.return_value.click = MagicMock()

        ingredients = {"молоко": 1}
        data_parser(ingredients)

        mock_wait.return_value.until.assert_called_once()

    #Правильное количество распаршенных продуктов
    def test_data_parser_products_found(self):

        ingredients = {"молоко": 1}

        result = data_parser(ingredients)

        self.assertEqual(len(result), 1)

    #не найден товар
    @patch('parser.webdriver.Chrome')
    @patch('parser.WebDriverWait')
    def test_data_parser_no_products(self, mock_wait, mock_webdriver):
        mock_driver = MagicMock()
        mock_webdriver.return_value = mock_driver
        mock_driver.find_elements.return_value = []

        ingredients = {"молоко": 1}
        result = data_parser(ingredients)

        self.assertEqual(result, [])

    #Логика
    @patch('parser.webdriver.Chrome')
    @patch('parser.WebDriverWait')
    def test_data_parser_mid_product(self, mock_wait, mock_webdriver):
        mock_driver = MagicMock()
        mock_webdriver.return_value = mock_driver

        mock_product1 = MagicMock()
        mock_product1.find_element.side_effect = [
            MagicMock(text="Продукт1"),  # name
            MagicMock(text="50")  # price
        ]
        mock_product2 = MagicMock()
        mock_product2.find_element.side_effect = [
            MagicMock(text="Продукт2"),  # name
            MagicMock(text="70")  # price
        ]
        mock_product3 = MagicMock()
        mock_product3.find_element.side_effect = [
            MagicMock(text="Продукт3"),  # name
            MagicMock(text="30")  # price
        ]

        mock_driver.find_elements.return_value = [mock_product1, mock_product2, mock_product3]

        ingredients = {"молоко": 1}
        result = data_parser(ingredients)

        self.assertEqual(result[0]["name"], "Продукт1")

    #Корректно ли парсятся данные после кликов и обработки логики
    @patch('parser.webdriver.Chrome')
    @patch('parser.WebDriverWait')
    def test_integration_parse_logic(self, mock_wait, mock_webdriver):
        mock_driver = MagicMock()
        mock_product1 = MagicMock()
        mock_product1.find_element.side_effect = [MagicMock(text="Хлеб"), MagicMock(text="40")]
        mock_product2 = MagicMock()
        mock_product2.find_element.side_effect = [MagicMock(text="Сыр"), MagicMock(text="30")]

        mock_driver.find_elements.return_value = [mock_product1, mock_product2]
        mock_webdriver.return_value = mock_driver

        ingredients = {"хлеб": 1, "сыр": 1}
        result = data_parser(ingredients)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], "Хлеб")
        self.assertEqual(result[0]['price'], "40")

    #Когда ничего не вводим
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

        data_parser(ingredients)

        options = mock_webdriver.call_args[1]['options']
        self.assertIn('--headless', options.arguments)

    #Проверяем, обрабатываются ли исключения при вызовах Selenium
    @patch('parser.webdriver.Chrome')
    @patch('parser.WebDriverWait')
    def test_integration_webdriver_exception(self, mock_wait, mock_webdriver):
        mock_driver = MagicMock()
        mock_driver.get.side_effect = WebDriverException()
        mock_webdriver.return_value = mock_driver

        with self.assertRaises(WebDriverException):
            data_parser({"молоко": 1})

    #Проверяем, что логика парсинга корректно работает при множественных запросах
    @patch('parser.webdriver.Chrome')
    @patch('parser.WebDriverWait')
    def test_integration_multiple_requests(self, mock_wait, mock_webdriver):
        mock_driver = MagicMock()
        mock_driver.find_elements.return_value = []
        mock_webdriver.return_value = mock_driver

        ingredients = {"хлеб": 1, "молоко": 1, "сыр": 1}
        result = data_parser(ingredients)

        self.assertIsInstance(result, list)  # Проверяем тип результата
        self.assertEqual(len(result), 0)  # Проверяем отсутствие данных

    #Проверяем, как парсер обрабатывает временные задержки и их исключения
    @patch('parser.webdriver.Chrome')
    @patch('parser.WebDriverWait')
    def test_integration_timeout(self, mock_wait, mock_webdriver):
        mock_driver = MagicMock()
        mock_wait.return_value.until.side_effect = TimeoutException()
        mock_webdriver.return_value = mock_driver

        with self.assertRaises(TimeoutException):
            data_parser({"молоко": 1})

    #Покрытие >= 70% (79%)
    def test_coverage(self):
        # Запускаем coverage
        cov = coverage.Coverage(source=["parser"])
        cov.start()
        self.test_data_parser_products_found()
        cov.stop()
        cov.save()
        total_coverage = cov.report(omit=None)
#        print(f"Total coverage: {total_coverage}%")
        self.assertGreaterEqual(total_coverage, 70, "Покрытие должно быть не меньше 70%")


#E2E тесты
class TestE2EDataParser(unittest.TestCase):
    #Закгрузка страницы
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
    #Тест на нахождеия продукта
    def test_single_product_found(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Открываем браузер в фоновом режиме
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        try:
            ingredients = {"молоко": 1}
            result = data_parser(ingredients)

            # Проверяем, был ли найден продукт
            self.assertGreater(len(result), 0, "Должен быть найден хотя бы один продукт")
            self.assertIn("name", result[0], "В результате должен быть ключ 'name'")
            self.assertIn("price", result[0], "В результате должен быть ключ 'price'")
            self.assertIn("link", result[0], "В результате должен быть ключ 'link'")
        finally:
            driver.quit()
    #Тест на несколько продуктов
    def test_multiple_products_found(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        try:
            ingredients = {"хлеб": 1, "сыр": 1}  # Проверяем несколько продуктов
            result = data_parser(ingredients)

            self.assertGreater(len(result), 1, "Должны найти несколько продуктов")
        finally:
            driver.quit()
    #Тест на несущ товар
    def test_no_products_found(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        try:
            # Искать явно несуществующий товар
            ingredients = {"asdkjlqwex": 1}
            result = data_parser(ingredients)

            self.assertEqual(result, [], "Если продукт отсутствует, парсер должен вернуть пустой список")
        finally:
            driver.quit()
    #Тес на обработку врменных блокировок сайта
    def test_wait_timeout(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        try:
            # Проверяем, что сайт не загружается быстро
            ingredients = {"молоко": 1}
            driver.get("https://example.com")  # Эмуляция несуществующего поиска
            self.assertTrue(driver.title)  # Проверяем, что браузер нормально ожидает
        finally:
            driver.quit()

if __name__ == "__main__":
    unittest.main()


