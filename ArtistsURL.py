# Import Necessary Libraries
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

import pandas as pd
import time
import os
import requests
import re

from scrapper_utils import *


# Get Artist Name and URL
def get_artist_list(driver, letter, out_filename): 
    curr_pg = 1
    driver.get('https://www.artsy.net/artists/artists-starting-with-{0}?page={1}'.format(letter,curr_pg))
    time.sleep(5) 

    # Number of Pages
    no_pages = driver.find_elements(By.TAG_NAME, 'nav')[-1] # Last 'nav' tag contains the page numbers
    soup = BeautifulSoup(no_pages.get_attribute('innerHTML'), 'html.parser') 
    tot_no_pages = max([int(i.text) for i in soup.find_all('a') if re.match('[0-9]+', i.text)]) # Max Number of Pages

    # first page
    artist_list = driver.find_elements(By.CSS_SELECTOR, '[class*="ArtistsByLetter__Name"]') # Get all artist names
    artists_url=[a.get_attribute('href') for a in artist_list] # Get all artist URLs
    append_list_of_dicts_to_pickle(artists_url, out_filename) # write results to file
    print(f'Page 1 finished (out of {tot_no_pages}). Number of artists: {len(artists_url)}')

    while curr_pg < tot_no_pages: # Loop through all pages
        # Click Next Button
        nxt_button = WebDriverWait(driver.find_elements(By.TAG_NAME, 'nav')[-1], 10).until( 
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="next"]')) 
            )
        driver.execute_script("arguments[0].click();", nxt_button) 
        curr_pg += 1 # Goes through loop until curr_pg < tot_no_pages
        time.sleep(5)

        artist_list = driver.find_elements(By.CSS_SELECTOR, '[class*="ArtistsByLetter__Name"]') # Get all artist names
        artists_url=[a.get_attribute('href') for a in artist_list] # Get all artist URLs
        append_list_of_dicts_to_pickle(artists_url, out_filename) # write results to file
        print(f'Page {curr_pg} finished (out of {tot_no_pages}). Number of artists: {len(artists_url)}')


def close_popup_if_present(driver):
    try:
        popup_close_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Close"]'))
        )
        driver.execute_script("arguments[0].click();", popup_close_button)
        print("Popup closed successfully.")
    except:
        print("No popup found or popup already closed.")

if __name__ == "__main__":

    # INPUT: start from letter:
    letter = 'a'

    if not os.path.exists('results'):
        try:
            os.makedirs('results')  # Use makedirs for nested directories
            print(f"Directory 'results' created.")
        except OSError as e:
            print(f"Error creating directory 'results': {e}")
    else:
        print(f"Directory 'results' already exists.")

    try:
        # Setup Chrome options
        chrome_options = webdriver.ChromeOptions()
        chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        # chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        # chrome_options.add_argument("start-maximized")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Initialize Chrome driver
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36'})

        # Start extracting
        get_artist_list(driver, letter, f'results/artists_url_{letter}.pickle')

    finally:
        try:
            driver.quit()
            print("Selenium driver closed.")
        except:
            print("Selenium driver already closed, or failed to close.")

import pickle
letter = 'a'
filename = f'results/artists_url_{letter}.pickle'

# Open and read the pickle file
with open(filename, 'rb') as f:
    data = pickle.load(f)

# Print the data
print("Contents of the pickle file:")
for item in data:
    print(item)

    