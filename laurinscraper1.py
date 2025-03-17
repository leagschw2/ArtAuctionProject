from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time


def scrape_all_pages(artist_name):
    # Setup Chrome options
    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

    # Initialize Chrome driver
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()

    formatted_name = artist_name.lower().replace(" ", "-")
    url = f"https://www.artsy.net/artist/{formatted_name}/auction-results"
    driver.get(url)

    time.sleep(15)  # Initial load

    all_work = []
    page_count = 1

    while True:
        # Parse current page content
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Collect auction entries
        auction_entries = soup.find_all("a", class_="RouterLink__RouterAwareLink-sc-c712443b-0 laGLjt")
        all_work.extend(auction_entries)
        print(f"Page {page_count}: Collected {len(auction_entries)} entries.")

        # Locate and click the 'Next' button
        try:
            next_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a[data-testid='next'][style*='opacity: 1']"))
            )
            driver.execute_script("arguments[0].click();", next_button)

            time.sleep(10)  # Wait for the next page to load
            page_count += 1

        except Exception as e:
            print(f"No 'Next' button found or error on Page {page_count}: {e}")
            break

    driver.quit()
    return all_work


if __name__ == "__main__":
    artist_name = "Titian"
    all_entries = scrape_all_pages(artist_name)
    print(f"\nTotal auction results collected: {len(all_entries)}\n")

    # Print URLs of collected entries
    for idx, entry in enumerate(all_entries, 1):
        print(f"{idx}: {entry.get('href')}")
