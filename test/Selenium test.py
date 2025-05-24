from selenium import webdriver
from time import sleep

driver = webdriver.Edge()
driver.get("https://example.com")  # Initial URL
driver.maximize_window()

sleep(5)

# Change the URL in the same tab
driver.get("https://openai.com")  # New URL

sleep(5)

driver.quit()
