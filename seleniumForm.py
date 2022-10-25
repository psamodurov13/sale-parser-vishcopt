from selenium import webdriver
import time
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import auth_data
import json
import requests as rq
from bs4 import BeautifulSoup as bs
from rich.progress import track
import add_sales

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15',
}

def get_cookies():
    cookies = {}
    selenium_cookies = driver.get_cookies()
    for cookie in selenium_cookies:
        cookies[cookie['name']] = cookie['value']
    return cookies


def get_posts(url):
    cookies = get_cookies()
    response = rq.get(url, cookies=cookies)
    return response.text


# Подключаем вэб-драйвер Chrome
options = Options()
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                     '(KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36')


# Запускаем парсинг
def start_parse():
    driver.get('https://vishcopt.ru/')
    time.sleep(1)
    cookies = driver.get_cookies()[1]
    s = rq.Session()
    s.cookies.set(domain=cookies['domain'], name=cookies['name'], path=cookies['path'], value=cookies['value'])

    try:
        # Входим в личный кабинет
        driver.get('https://vishcopt.ru/personal/')
        time.sleep(1)
        username_input = driver.find_element(By.CSS_SELECTOR, 'div.api-auth form input[type="text"]')
        username_input.send_keys(auth_data.login)
        time.sleep(1)
        password_input = driver.find_element(By.CSS_SELECTOR, 'div.api-auth form input[type="password"]')
        password_input.send_keys(auth_data.password)
        time.sleep(1)
        button = driver.find_element(By.CSS_SELECTOR, 'div.api-auth form button[type="submit"]')
        button.click()
        time.sleep(5)

        yml_url = 'https://vishcopt.ru/export/yml/'
        yml = s.get(yml_url, cookies=get_cookies())
        with open('/Users/psamodurov13/Downloads/catalog.yml', 'wb') as file:
            file.write(yml.content)

        # Собираем список товаров, пробегаемся по двум разделам распродажи
        products = set()
        for i in ['https://vishcopt.ru/catalog/s_a_l_e/', 'https://vishcopt.ru/catalog/super_sale/']:
            driver.get(i)
            while True:
                html = driver.page_source
                soup = bs(html, features="html.parser")
                products.update(list(set(item.get('href') for item in soup.select('#collection .product-item a'))))
                print('Всего товаров ', len(products))
                if not driver.find_element(By.CSS_SELECTOR, '.pagination-bar ul li:last-child a').text.isdigit():
                    next_page = driver.find_element(By.CSS_SELECTOR, '.pagination-bar ul li:last-child a')
                    next_page.click()
                    time.sleep(1)
                else:
                    print('Больше страниц с товарами нет')
                    break
        # Собираем данные о каждом товаре (старая цена, новая цена)
        products_dict = {}
        for product in track(products):
            prod_html = get_posts('https://vishcopt.ru' + product)
            prod_soup = bs(prod_html, features="html.parser")
            try:
                products_dict[prod_soup.find('span', id='sku').text] = [
                    prod_soup.find('span', class_='price').text.replace(' руб', '').replace(' ', ''),
                    prod_soup.find('del', class_='old-price').text.replace(' руб', '').replace(' ', ''),
                    'https://vishcopt.ru' + product
                ]
            except Exception as ex:
                print(ex)
            print(len(products_dict), ' / ', len(products))

        # Сохраняем данные в json
        with open('products.json', 'w') as prod_file:
            json.dump(products_dict, prod_file, ensure_ascii=False, indent=4)

        # Обновляем цены в файле-выгрузке и создаем xml файл
        add_sales.convert()

    except Exception as ex:
        print(ex)
    finally:
        driver.close()
        driver.quit()
