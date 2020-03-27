import logging
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

LOGGER = logging.getLogger('crawler')


def _parse_row(html):
    elem_tree = BeautifulSoup(html, 'html.parser')
    tds = elem_tree.select('td')
    return {
        'ip': str(tds[0].string),
        'port': str(tds[1].string),
        'type': list(map(lambda x: x.strip().lower(), str(tds[4].string).split(","))),
        'anonymity': str(tds[5].string),
    }


def _get_remote_driver():
    while True:
        try:
            return webdriver.Remote(
                command_executor='http://selenium_hub:4444/wd/hub',
                desired_capabilities={'browserName': 'firefox', 'headless': True})
        except:
            LOGGER.debug("Waiting for selenium hub...")
            time.sleep(2)


def scrap(start_url):
    driver = _get_remote_driver()
    try:
        driver.get(start_url)
        WebDriverWait(driver, 500).until(
            expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, 'table.proxy__t')))

        while True:
            elements = driver.find_elements_by_css_selector("table.proxy__t tr")
            for i in range(1, len(elements)):
                try:
                    if i >= len(elements):
                        break
                    content = elements[i].get_attribute('innerHTML')
                except StaleElementReferenceException:
                    elements = driver.find_elements_by_css_selector("table.proxy__t tr")
                    if i >= len(elements):
                        break
                    content = elements[i].get_attribute('innerHTML')
                yield _parse_row(content)
            for _ in range(0, 20):
                try:
                    driver.execute_script(
                        "b = document.querySelector('.proxy__pagination .arrow__right a'); "
                        + "b && window.scroll(b.getBoundingClientRect().x+window.scrollX, b.getBoundingClientRect().y+window.scrollY);")
                    try:
                        next_button = driver.find_element_by_css_selector('.proxy__pagination .arrow__right a')
                    except NoSuchElementException:
                        print('no such!')
                        return
                    ActionChains(driver).move_to_element_with_offset(next_button, 1, 1).click().perform()
                    WebDriverWait(driver, 10).until(
                        expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, 'table.proxy__t')))
                    break
                except:
                    pass
    finally:
        driver.quit()
