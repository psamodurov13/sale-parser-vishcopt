from selenium import webdriver
# from seleniumwire import webdriver
import time

from selenium.webdriver import ActionChains, Keys
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
from loguru import logger
from selenium.common.exceptions import NoSuchElementException
import urllib.request
import base64

logger.add('debug.log', format="{time} {level} {message}", level="INFO")

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


# Connect webdriver Chrome
options = Options()
options.add_argument('headless')
options.add_argument('--no-sandbox')
# options.add_argument(f'--proxy-server=194.67.202.81:9138')
# driver = webdriver.Chrome(options=options)
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                     '(KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36')


# Start parsing
def start_parse():
    driver.get('https://vishcopt.ru/')
    time.sleep(1)
    cookies = driver.get_cookies()[1]
    s = rq.Session()
    s.cookies.set(domain=cookies['domain'], name=cookies['name'], path=cookies['path'], value=cookies['value'])

    try:
        status = True
        while status:
            # Sign in
            driver.get('https://vishcopt.ru/private/login/')
            time.sleep(1)
            username_input = driver.find_element(By.CSS_SELECTOR, '.authform input[name="login"]')
            username_input.send_keys(auth_data.login)
            time.sleep(1)
            password_input = driver.find_element(By.CSS_SELECTOR, '.authform input[name="password"]')
            password_input.send_keys(auth_data.password)
            time.sleep(5)
            iframe = driver.find_element(By.CSS_SELECTOR, 'iframe[title="SmartCaptcha checkbox widget"]')
            driver.switch_to.frame(iframe)
            time.sleep(2)
            drag_element = driver.find_element(By.CSS_SELECTOR, '.Track .Thumb')
            actions = ActionChains(driver)
            actions.click_and_hold(drag_element)
            actions.move_by_offset(230, 0)
            actions.release()
            actions.perform()
            driver.switch_to.default_content()
            time.sleep(5)
            try:
                iframe_img = driver.find_element(By.CSS_SELECTOR, 'iframe[title="SmartCaptcha advanced widget"]')
                driver.switch_to.frame(iframe_img)
                captcha_img = driver.find_element(By.CSS_SELECTOR, '.Captcha-ModalContent img').get_attribute('src')
                base64_img = base64.b64encode(rq.get(captcha_img).content).decode('utf-8')
                params = {
                    'key': auth_data.api_key,
                    'method': 'base64',
                    'body': base64_img,
                    'json': 1
                }
                try_to_get_task = 1
                while True:
                    task_response = rq.post(f'http://rucaptcha.com/in.php', data=params)
                    if task_response.json()['status']:
                        task_id = task_response.json()['request']
                        logger.info(f'TASK ID - {task_id}')
                        time.sleep(15)
                        try_to_get_answer = 1
                        while True:
                            result_response = rq.get(
                                f'http://rucaptcha.com/res.php?key={auth_data.api_key}&action=get&id={task_id}&json=1')
                            if result_response.json()['status']:
                                captcha_answer = result_response.json()['request']
                                logger.info(f'CAPTCHA ANSWER - {captcha_answer}')
                                answer_field = driver.find_element(By.CSS_SELECTOR, '.Textinput-Control')
                                answer_field.send_keys(captcha_answer)
                                time.sleep(2)
                                answer_field.send_keys(Keys.RETURN)
                                # confirm_button = driver.find_element(By.CSS_SELECTOR, '.CaptchaButton-SubmitContent')
                                # confirm_button.click()
                                time.sleep(5)
                                break
                            else:
                                logger.info(f'CAPTCHA NOT SOLVED YET')
                                try_to_get_answer += 1
                                time.sleep(10)
                                if try_to_get_answer == 10:
                                    logger.info('LAST TRY COMPLETED')
                                    break
                                else:
                                    logger.info(f'CONTINUE')
                                    continue
                    else:
                        logger.info(f'TASK ID WAS NOT RECEIVED')
                        try_to_get_task += 1
                        time.sleep(5)
                        continue
                    driver.switch_to.default_content()
                    iframe = driver.find_element(By.CSS_SELECTOR, 'iframe[title="SmartCaptcha checkbox widget"]')
                    driver.switch_to.frame(iframe)
                    captcha_status = driver.find_element(By.CSS_SELECTOR, '.Text_typography_control-s').text
                    driver.switch_to.default_content()
                    if captcha_status == 'Готово':
                        logger.info('CAPTCHA WAS SOLVED')
                        status = True
                        break
                    else:
                        status = False
            except Exception:
                logger.debug('TEXT CAPTCHA FORM DID NOT FOUND')
                logger.exception(Exception)
            if status:
                break
            else:
                continue
        button = driver.find_element(By.CSS_SELECTOR, '.authform button[type="submit"]')
        button.click()
        time.sleep(5)
        driver.save_screenshot('screen.png')

        yml_url = 'https://vishcopt.ru/export/yml/'
        yml = s.get(yml_url, cookies=get_cookies())
        # urllib.request.urlretrieve(yml_url, 'catalog.yml',)
        logger.info(f'RESPONSE {yml}')
        # with open('/home/user/web/sweethomedress.ru/public_html/catalog.yml', 'wb') as file:
        with open('catalog.yml', 'wb') as file:
            file.write(yml.content)
            logger.info(f'CREATED FILE')

        # get products list, iterate by 2 sales categories
        products = set()
        for i in ['https://vishcopt.ru/catalog/s_a_l_e/', 'https://vishcopt.ru/catalog/super_sale/']:
            driver.get(i)
            while True:
                html = driver.page_source
                soup = bs(html, features="html.parser")
                products.update(list(set(item.get('href') for item in soup.select('.product-cards .product-card a'))))
                logger.info(f'Total products {len(products)}')
                try:
                    try:
                        next_page = driver.find_element(By.CSS_SELECTOR, '.pagination-next')
                        next_page.click()
                        time.sleep(1)
                    except NoSuchElementException:
                        logger.info('No more product pages')
                        break
                    # if not driver.find_element(By.CSS_SELECTOR, '.pagination-bar ul li:last-child a').text.isdigit():
                    #     next_page = driver.find_element(By.CSS_SELECTOR, '.pagination-bar ul li:last-child a')
                    #     next_page.click()
                    #     time.sleep(1)
                    # else:
                    #     logger.info('No more product pages')
                    #     break
                except Exception:
                    print('Only one page')
                    break
        # Get data about all products (old price, new price)
        products_dict = {}
        for product in track(products):
            if product:
                logger.info(f'Scrap {product}')
                prod_html = get_posts('https://vishcopt.ru' + product)
                prod_soup = bs(prod_html, features="html.parser")
                try:
                    sku = prod_soup.select_one('.product-details > .pb-3 > .p-1').text.replace('Артикул: ', '')
                    products_dict[sku] = [
                        prod_soup.select('.product-price span')[0].text.replace(' руб', '').replace(' ', ''),
                        prod_soup.select_one('.product-price span.is-striketrough').text.replace(' руб', '').replace(
                            ' ', ''),
                        'https://vishcopt.ru' + product
                    ]
                    logger.info(f'{sku} - {products_dict[sku]}')
                except Exception as ex:
                    logger.exception(ex)
            else:
                logger.info('None skipped')
                continue
            print(len(products_dict), ' / ', len(products))

        # Save data in json
        with open('products.json', 'w') as prod_file:
            json.dump(products_dict, prod_file, ensure_ascii=False, indent=4)

        # Update prices in the upload file and create an xml file
        add_sales.convert()

    except Exception as ex:
        print(ex)
    finally:
        driver.close()
        driver.quit()
