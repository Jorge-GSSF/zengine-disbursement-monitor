from __future__ import annotations

from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait


ZENGINE_DEVELOPER_URL = "https://platform.zenginehq.com/account/developer"
TOKEN_LOCATOR = (By.CSS_SELECTOR, "span.access-token")

EMAIL_LOCATORS = [
    (By.CSS_SELECTOR, "input[type='email']"),
    (By.CSS_SELECTOR, "input[name='email']"),
    (By.CSS_SELECTOR, "input[name='username']"),
    (By.CSS_SELECTOR, "input[id='email']"),
    (By.CSS_SELECTOR, "input[id='username']"),
    (
        By.XPATH,
        "//input[contains(translate(@placeholder, "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'email')]",
    ),
]

PASSWORD_LOCATORS = [
    (By.CSS_SELECTOR, "input[type='password']"),
    (By.CSS_SELECTOR, "input[name='password']"),
    (By.CSS_SELECTOR, "input[id='password']"),
]

SUBMIT_LOCATORS = [
    (By.CSS_SELECTOR, "button[type='submit']"),
    (By.CSS_SELECTOR, "input[type='submit']"),
    (
        By.XPATH,
        "//button[contains(translate(normalize-space(.), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'log in')]",
    ),
    (
        By.XPATH,
        "//button[contains(translate(normalize-space(.), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sign in')]",
    ),
]


def get_zengine_api_token(email: str, password: str, timeout_seconds: int = 60) -> str:
    if not email.strip() or not password:
        raise RuntimeError("Zengine login email and password are required.")

    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1440,1200")

    driver = Chrome(options=options)
    try:
        driver.get(ZENGINE_DEVELOPER_URL)
        try:
            return _wait_for_token(driver, timeout=8)
        except TimeoutException:
            return _login_and_read_token(driver, email.strip(), password, timeout_seconds)
    finally:
        driver.quit()


def _login_and_read_token(
    driver: WebDriver,
    email: str,
    password: str,
    timeout_seconds: int,
) -> str:
    email_field = _first_visible(driver, EMAIL_LOCATORS, timeout=20)
    if email_field is not None:
        _replace_input_value(email_field, email)

    password_field = _first_visible(driver, PASSWORD_LOCATORS, timeout=5)
    if password_field is None and email_field is not None:
        email_field.send_keys(Keys.ENTER)
        password_field = _first_visible(driver, PASSWORD_LOCATORS, timeout=20)

    if password_field is None:
        raise RuntimeError("Zengine login page opened, but the password field was not found.")

    _replace_input_value(password_field, password)

    submit_button = _first_visible(driver, SUBMIT_LOCATORS, timeout=5)
    if submit_button is not None:
        submit_button.click()
    else:
        password_field.send_keys(Keys.ENTER)

    try:
        return _wait_for_token(driver, timeout=timeout_seconds)
    except TimeoutException:
        driver.get(ZENGINE_DEVELOPER_URL)
        return _wait_for_token(driver, timeout=30)


def _wait_for_token(driver: WebDriver, timeout: int) -> str:
    return WebDriverWait(driver, timeout).until(lambda current: _read_token(current) or False)


def _read_token(driver: WebDriver) -> str | None:
    for element in driver.find_elements(*TOKEN_LOCATOR):
        token = (element.text or element.get_attribute("textContent") or "").strip()
        if token:
            return token
    return None


def _first_visible(
    driver: WebDriver,
    locators: list[tuple[str, str]],
    timeout: int,
) -> object | None:
    def locate(current: WebDriver) -> object | bool:
        for by, selector in locators:
            for element in current.find_elements(by, selector):
                if element.is_displayed() and element.is_enabled():
                    return element
        return False

    try:
        return WebDriverWait(driver, timeout).until(locate)
    except TimeoutException:
        return None


def _replace_input_value(element: object, value: str) -> None:
    element.click()
    element.send_keys(Keys.CONTROL, "a")
    element.send_keys(value)
