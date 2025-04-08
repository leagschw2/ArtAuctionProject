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

import pickle

from scrapper_utils import *

# Scrape Artist Description
def close_popup_if_present(driver):
    try:
        popup_close_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Close"]'))
        )
        driver.execute_script("arguments[0].click();", popup_close_button)
        print("Popup closed successfully.")
    except:
        # print("No popup found or popup already closed.")
        pass


def get_artist_description(driver):
    try:
        artist_info = driver.find_element(By.CSS_SELECTOR, '[data-test="artistHeader"]')

        # Close popup if present
        close_popup_if_present(driver)

        # Try clicking "Read more" if available
        try:
            artist_info_readmore = WebDriverWait(artist_info, 5).until(
                EC.element_to_be_clickable((By.XPATH, './/button[contains(., "Read more")]'))
            )
            driver.execute_script("arguments[0].click();", artist_info_readmore)

            WebDriverWait(artist_info, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[aria-expanded="true"]'))
            )
        except:
            pass  # No "Read more" button means no expansion needed

        # Re-grab updated HTML after potential expansion
        artist_info_updated = driver.find_element(By.CSS_SELECTOR, '[data-test="artistHeader"]')
        artist_info_html = artist_info_updated.get_attribute('innerHTML')
        soup = BeautifulSoup(artist_info_html, 'html.parser')

        # Extract data
        artist_name = soup.find('h1').text.strip()
        artist_country_year = soup.find('h2').text.strip()

        # Description (check if it exists)
        desc_block = soup.find('div', {'aria-expanded': 'true'})
        artist_description_paragraph = desc_block.text.strip() if desc_block else 'N/A'

        return artist_name, artist_country_year, artist_description_paragraph

    except Exception as e:
        print(f"Error extracting artist description: {e}")
        return 'N/A', 'N/A', 'N/A'


def filter_artist_by_auction_count(artist_url):
    
    try:
        driver.get(artist_url + "/auction-results?categories%5B0%5D=Painting&categories%5B1%5D=Work%20on%20Paper&hide_upcoming=true&allow_empty_created_dates=true&currency=&include_estimate_range=false&include_unknown_prices=true&allow_unspecified_sale_dates=true")
        time.sleep(5)  # Allow time for the page to load

        # Check for "No auction results" message
        if driver.find_elements(By.XPATH, 
                "//*[contains(text(), 'There are currently no auction results for this artist.')]"):
            return 0 # 0 means do not continue
        
        if driver.find_elements(By.XPATH, "//*[contains(text(), 'There aren‘t any works available that meet the following criteria at this time')]"):
            return 0

        # Extract auction results count
        auction_results = driver.find_element(By.CSS_SELECTOR, '[data-test="auctionResults"]')
        auction_results_html = auction_results.get_attribute('innerHTML')
        soup = BeautifulSoup(auction_results_html, 'html.parser')

        # Extract the number of auction results
        no_work_text = soup.find(string=re.compile(r"(\d+) results"))
        if no_work_text:
            no_work = int(re.search(r"(\d+)", no_work_text).group(1))
        else:
            no_work = 0  # Assume 0 if number is not found

        # Only keep artists with at least 10 auction results
        return int(no_work >= 10)

    except Exception as e:
        print(f"Error processing {artist_url}: {e}")
        return 0


# Scrape all Auction Entries for an Artist
def scrape_all_pages(url):
    try:
        driver.get(url + "/auction-results?categories%5B0%5D=Painting&categories%5B1%5D=Work%20on%20Paper&hide_upcoming=true&allow_empty_created_dates=true&currency=&include_estimate_range=false&include_unknown_prices=true&allow_unspecified_sale_dates=true")
        time.sleep(5)

    except Exception as e:
        print(f"Auction results page not found for {url}")
        return None, None, None

    # Scrape Artist Description
    artist_name, artist_country_year, artist_description_paragraph = get_artist_description(driver)
    # print(f"Artist Name: {artist_name}")
    # print(f"Artist Country and Year: {artist_country_year}")
    # print(f"Artist Description: {artist_description_paragraph}\n")

    page_count = 1

    # first page
    soup = BeautifulSoup(driver.page_source, "html.parser")
    auction_entries = soup.find_all("a", class_="RouterLink__RouterAwareLink-sc-c712443b-0 laGLjt")
    all_work.extend(auction_entries)

    while True:
        try:
            next_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a[data-testid='next'][style*='opacity: 1']"))
            )
            driver.execute_script("arguments[0].click();", next_button)
            time.sleep(5)
            page_count += 1

            soup = BeautifulSoup(driver.page_source, "html.parser")
            auction_entries = soup.find_all("a", class_="RouterLink__RouterAwareLink-sc-c712443b-0 laGLjt")
            all_work.extend(auction_entries)

        except Exception as e:
            # print(f"No 'Next' button found or error on Page {page_count}: {e} of artist {artist_name}")
            # print(f"No 'Next' button found or error on Page {page_count} of artist {artist_name}")
            break

    return artist_name, artist_country_year, artist_description_paragraph

def modify_url(url_ori, height=400, quality=80, resize_to='fit&amp', width=400):
    config_param = {'height':str(int(height)), 
                    'quality':str(int(quality)), 
                    'resize_to':resize_to, 
                    'width':str(int(width))}

    http_, url_details = url_ori.split('://')
    url_domain, url_details = url_details.split('?')
    url_details = url_details.split('&')
    for idx, d in enumerate(url_details):
        if d.split('=')[0] == 'src':
            url_details[idx] = d.replace('thumbnail.jpg','larger.jpg')
        else:
            url_details[idx] = '{0}={1}'.format(d.split('=')[0], config_param[d.split('=')[0]])
    
    modified_url = '{0}://{1}?{2}'.format(http_,url_domain,'&'.join(url_details))
    return modified_url

def parse_auction_entries(all_entries, artist_id, artist_name):
    auction_data = []

    for entry in all_entries:
        soup = BeautifulSoup(str(entry), "html.parser")

        # Extracting Title, Medium, Dimesnions
        title = soup.select_one('.bxWaGD').text.strip() if soup.select_one('.bxWaGD') else 'N/A'
        medium = soup.select('.irDwAE')[0].text.strip() if len(soup.select('.irDwAE')) > 0 else 'N/A'
        dimensions = soup.select('.irDwAE')[1].text.strip() if len(soup.select('.irDwAE')) > 1 else 'N/A'

        # Extracting Sale Date, Auction House
        sale_date_house = soup.select('.irDwAE')[2].text.strip() if len(soup.select('.irDwAE')) > 2 else 'N/A'
        if '•' in sale_date_house:
            sale_date, auction_house = [x.strip() for x in sale_date_house.split('•', 1)]
        else:
            sale_date, auction_house = sale_date_house, 'N/A'
        
        # Extracting Sale Name, Lot Number
        sale_name = soup.select('.irDwAE')[6].text.strip() if len(soup.select('.irDwAE')) > 6 else 'N/A'
        lot_number = soup.select('.irDwAE')[7].text.strip() if len(soup.select('.irDwAE')) > 7 else 'N/A'
        
        # Extracting Sale Location
        sale_location_full = soup.select('.irDwAE.bbAxnM')[2].text.strip() if len(soup.select('.irDwAE.bbAxnM')) > 2 else 'N/A'
        if '•' in sale_location_full:
            sale_location = sale_location_full.split('•')[1].strip()
        else:
            sale_location = 'N/A'
        
         # Image URL
        if entry.find('img'):
            image_url = entry.find('img').get('src')
            # replace image_url with the higher quality image url
            modified_url = modify_url(image_url)
            
        else:
            image_url = 'N/A'
            modified_url = 'N/A'

        # Extracting Price Sold, Price Estimated
        if soup.select_one('.cMfkJA'):
            price_sold = soup.select_one('.cMfkJA').text.strip()
        elif soup.select_one('.lgFNAw'):
            price_sold = soup.select_one('.lgFNAw').text.strip()
        else:
            price_sold = 'N/A'
        # price_sold = soup.select_one('.cMfkJA').text.strip() if soup.select_one('.cMfkJA') else 'N/A'
        price_estimated = soup.select_one('.jEONpp').text.strip().replace("(est)", "") if soup.select_one('.jEONpp') else 'N/A'

        # Merge Data
        auction_data.append({
            'Title': title,
            'Artist ID': artist_id,
            'Artist Name': artist_name,
            'Medium': medium,
            'Dimensions': dimensions,
            'Sale Date': sale_date,
            'Auction House': auction_house,
            'Sale Location': sale_location,
            'Sale Name': sale_name,
            'Lot Number': lot_number,
            'Price Sold': price_sold,
            'Price Estimated': price_estimated,
            'Image url ori': image_url,
            'Image url better quality': modified_url
        })

    return auction_data


def append_to_pickle(data, filename):
    """Appends data to a pickle file."""
    try:
        with open(filename, "ab") as f:  # Use "ab" (append binary) mode
            pickle.dump(data, f)
    except FileNotFoundError:
        with open(filename, "wb") as f: # if file doesn't exist, create it
            pickle.dump(data,f)


# Example
if __name__ == "__main__":

    # INPUT: artists start with letter:
    letter = 'c'
    email = "artauctionproject.57@gmail.com"
    password = "Artauctionproject2025!"

    try:
        # Setup Chrome options
        chrome_options = webdriver.ChromeOptions()
        # chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument("start-maximized")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Initialize Chrome driver
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36'})

        #Read artist URLs from the saved text file
        # Load the data:
        artist_urls = read_list_of_dicts_from_appended_pickle(f"results/artists_url_{letter}.pickle")        

        driver.get('https://www.artsy.net/')
        time.sleep(5)
        artsy_login(driver, email, password)

        time.sleep(10)

        print(f'Scrapping started at {time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.time()))}')

        for artist_id, url in enumerate(artist_urls[8001:10000]):
            artist_id = f'{letter}{str(artist_id+8001)}'
            
            all_work = []
            if filter_artist_by_auction_count(url) == 0:
                continue
            artist_name, artist_country_year, artist_description_paragraph = scrape_all_pages(url)
            if (artist_name is None) and (artist_country_year is None) and (artist_description_paragraph is None):
                continue
            
            auction_data = parse_auction_entries(all_work, artist_id, artist_name)
            
            print(f'Artist {artist_id}: {artist_name}. Number of auction results: {len(all_work)}')

            # write artist data
            append_list_of_dicts_to_pickle(
                [{'artist_id':artist_id,'url':url,'artist_country_year':artist_country_year,'artist_biography':artist_description_paragraph}], 
                f'results/artists_details_{letter}.pickle'
                )
            # write auction results
            append_list_of_dicts_to_pickle(auction_data, f'results/auction_results_{letter}.pickle')

        print(f'Scrapping finished at {time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.time()))}')

    finally:
        try:
            driver.quit()
            print("Selenium driver closed.")
        except:
            print("Selenium driver already closed, or failed to close.")
