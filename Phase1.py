import requests
from bs4 import BeautifulSoup
import csv
import re  # Used for regular expressions
import os  # Used to check if the CSV file exists


def scrape_book_details_simple(url):
    """
    Scrapes specific book details from books.toscrape.com.

    Args:
        url (str): The URL of the book's detail page.

    Returns:
        dict: A dictionary containing the scraped book details, or None if an error occurs.
    """
    try:

        response = requests.get(url)  # 1. Send a request to get the webpage content
        response.raise_for_status()  # Raise an error for bad responses (e.g., 404 Not Found)
        response.encoding = 'utf-8'  # Explicitly set encoding to UTF-8 to correctly handle special characters like '£'

        soup = BeautifulSoup(response.text, 'html.parser')  # 2. Parse the HTML content using BeautifulSoup

        # 3. Create a dictionary to store all the scraped data and initialize all strings as empty
        book_data = {
            'product_page_url': url,
            'universal_product_code': '',
            'book_title': '',
            'price_including_tax': '',
            'price_excluding_tax': '',
            'quantity_available': '',
            'product_description': '',
            'category': '',
            'review_rating': '',
            'image_url': ''
        }

        # --- Extracting Data Points ---

        # Book Title from <h1> tag
        title_tag = soup.find('h1')
        if title_tag:
            book_data['book_title'] = title_tag.get_text(strip=True)

        # Price Including Tax <p> tag with class 'price_color'
        price_incl_tax_tag = soup.find('p', class_='price_color')
        if price_incl_tax_tag:
            book_data['price_including_tax'] = price_incl_tax_tag.get_text(strip=True)

        return book_data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during scraping: {e}")
        return None

# --- Main part of the script to run the scraping and export ---
if __name__ == "__main__":
    # The URL of the book page we want to scrape
    book_page_url = "https://books.toscrape.com/catalogue/soumission_998/index.html"

    print(f"Attempting to scrape: {book_page_url}")
    # Call the scraping function
    scraped_book_info = scrape_book_details_simple(book_page_url)

    if scraped_book_info:
        print("\nSuccessfully scraped book details:")
        for key, value in scraped_book_info.items():
            print(f"  {key.replace('_', ' ').title()}: {value}")


    else:
        print("Failed to scrape book details.")
