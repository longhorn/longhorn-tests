import os
import sys

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

wait_timeout = 10
click_retry_timeout = 20


def navigate_and_wait_for(target, expect):
    success = False
    retry = 0
    max_retry = 10
    while success is not True and retry < max_retry:
        try:
            driver.get(target)
            wait_for(expect)
            success = True
        except ElementClickInterceptedException as e:
            raise e
        except Exception as e:
            print(f'[retry {retry}] try to navigate to {target} and wait for {expect} failed ... {repr(e)} {e}')
        retry += 1


def wait_for(target):
    try:
        WebDriverWait(driver, wait_timeout).until(
            expected_conditions.presence_of_element_located((By.XPATH, elements[target]))
        )
        return True
    except Exception as e:
        print(f'wait for {target} error: {e}')
        return False


def click(target):
    driver.find_element_by_xpath(elements[target]).click()


def click_and_wait(target, expect):
    success = False
    retry = 0
    max_retry = 10
    while success is not True and retry < max_retry:
        try:
            _target = driver.find_element_by_xpath(elements[target])
            _target.click()
            WebDriverWait(driver, click_retry_timeout).until(
                expected_conditions.presence_of_element_located((By.XPATH, elements[expect]))
            )
            success = True
        except ElementClickInterceptedException as e:
            raise e
        except Exception as e:
            print(f'[retry {retry}] try to click {target} and wait for {expect} failed ... {repr(e)} {e}')
        retry += 1


def send_keys(target, keys):
    _target = driver.find_element_by_xpath(elements[target])
    _target.send_keys(keys)


def get_element(element):
    content = driver.find_element_by_xpath(elements[element]).text
    return content


elements = {
    'username_input': '//*[@id="username"]',
    'password_input': '//*[@type="password"]',
    'login': '//button[@id="submit"]',
    'agree': '(//*[contains(@class, "checkbox-custom")])[2]',
    'continue': '//*[@type="submit" and not(@disabled)]',
    'local_cluster': '//*[contains(@href, "/local")]',
    'create_api_key': '//button[contains(text(), "Create API Key")]',
    'create_confirm': '//button//*[contains(text() ,"Create")]',
    'access_key': '//*[contains(@class, "with-copy")][1]/span',
    'secret_key': '//*[contains(@class, "with-copy")][2]/span',
    'create_done': '//button//*[contains(text() ,"Done")]'
}

if __name__ == '__main__':

    url = 'https://' + sys.argv[1]
    login_url = url + '/dashboard/auth/login'
    account_url = url + '/dashboard/account'

    options = webdriver.ChromeOptions()
    prefs = {
        'profile.default_content_setting_values.notifications': 2
    }
    options.add_experimental_option('prefs', prefs)
    options.add_argument('--headless')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--no-sandbox')
    options.add_argument('window-size=1920,1200')

    driver = webdriver.Chrome(executable_path='/usr/bin/chromedriver', options=options)

    success = False
    _retry = 0
    _max_retry = 3

    while not success and _retry < _max_retry:
        try:
            print(login_url)
            driver.get(login_url)
            try:
                wait_for('username_input')
                send_keys('username_input', 'admin')
            except Exception as e:
                print(f'no username field {e}')
            send_keys('password_input', sys.argv[2])
            click_and_wait('login', 'agree')
            click_and_wait('agree', 'continue')
            click_and_wait('continue', 'local_cluster')
            navigate_and_wait_for(account_url, 'create_api_key')
            click_and_wait('create_api_key', 'create_confirm')
            click_and_wait('create_confirm', 'access_key')
            access_key = get_element('access_key')
            secret_key = get_element('secret_key')
            click('create_done')
            with open('access_key', 'w') as f:
                f.write(str(access_key))
            with open('secret_key', 'w') as f:
                f.write(str(secret_key))
            success = True
        except Exception as e:
            print(f'parsing error: {e}')
            _retry += 1

    driver.quit()
