import time
import pyperclip
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from config import FIREFOX_USER_DATA

# Use firefox for selenium
def init_browser(headless: bool = False) -> webdriver.Firefox:
    """
    Launches Firefox using an existing profile so you stay logged in to Milanote.
    - headless: if True, runs Firefox in headless mode
    """
    options = Options()
    # Use the specified Firefox profile:
    options.add_argument('-profile')
    options.add_argument(FIREFOX_USER_DATA)
    if headless:
        options.headless = True
    driver = webdriver.Firefox(options=options)
    driver.implicitly_wait(10)
    return driver

def dispatch_note(driver: webdriver.Firefox, content: str, link: str) -> bool:
    """
    Open the Milanote URL in a new tab, paste the text as an unsorted note, then close that tab.
    Returns True on success, False on any exception.
    """
    if not link:
        return True  # Empty link is treated as "dispatching to nowhere"
    flag = False
    try:
        # Open a new tab and navigate to the link
        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[-1])
        driver.get(link)
        time.sleep(2)

        # Copy content into clipboard and paste into Milanote
        pyperclip.copy(content)
        body = driver.find_element(By.TAG_NAME, "body")
        body.send_keys(Keys.CONTROL, "v")
        time.sleep(0.2)
        body.send_keys(Keys.ESCAPE)
        time.sleep(0.2)
        flag = True
    except Exception as e:
        print(f"[dispatcher] failed to send to {link}: {e}")
    finally:
        try:
            # Close tab and return to main window
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        except:
            pass
    return flag
