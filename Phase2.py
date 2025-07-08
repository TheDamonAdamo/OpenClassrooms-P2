import requests
from bs4 import BeautifulSoup
import csv
import re  # Used for regular expressions
import os  # Used to check if the CSV file exists
from urllib.parse import urljoin # Help build absolute URLs from relative URLs

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

        # Product Information Table (contains UPC, Price Excl. Tax, etc.)
        # Finding the table with class 'table table-striped'
        product_info_table = soup.find('table', class_='table table-striped')
        if product_info_table:  # Find all table rows (<tr>) within this table
            table_rows = product_info_table.find_all('tr')
            for row in table_rows:  # Get the header (<th>) and value (<td>) for each row
                header = row.find('th').get_text(strip=True)
                value = row.find('td').get_text(strip=True)

                if header == 'UPC':
                    book_data['universal_product_code'] = value
                elif header == 'Price (incl. tax)':
                    book_data['price_including_tax'] = value
                elif header == 'Price (excl. tax)':
                    book_data['price_excluding_tax'] = value
                # elif header == 'Availability':
                #    book_data['price_excluding_tax'] = value

                # Quantity Available (from the 'instock availability' paragraph)
        availability_tag = soup.find('p', class_='instock availability')
        if availability_tag:
            stock_text = availability_tag.get_text(strip=True)
            # Use a re to find the number of books in "In stock"
            match = re.search(r'\((\d+) available\)', stock_text)
            if match:
                book_data['quantity_available'] = int(match.group(1))  # Convert to integer
            else:
                book_data['quantity_available'] = stock_text  # Fallback if number not found

        # Product Description in <p> tag that is a sibling to a <div> with id 'product_description'
        description_div = soup.find('div', id='product_description')
        if description_div:
            # Find the very next <p> tag after the description_div
            description_p = description_div.find_next_sibling('p')
            if description_p:
                book_data['product_description'] = description_p.get_text(strip=True)
            else:
                book_data['product_description'] = "No description found."
        else:
            book_data['product_description'] = "No description found."

        # Category from the breadcrumb navigation
        # The breadcrumb is an <ul> with class 'breadcrumb'
        breadcrumb_ul = soup.find('ul', class_='breadcrumb')
        if breadcrumb_ul:
            # (Home > Category > Book Title) <li> element (index 2)
            breadcrumb_items = breadcrumb_ul.find_all('li')
            if len(breadcrumb_items) >= 3:
                category_tag = breadcrumb_items[2].find('a')  # The <a> tag inside the <li>
                if category_tag:
                    book_data['category'] = category_tag.get_text(strip=True)

        # Review Rating from the <p> tag with a class like 'star-rating Three'
        star_rating_tag = soup.find('p', class_=lambda x: x and 'star-rating' in x)
        if star_rating_tag:
            # The rating is part of the class name (e.g., 'One', 'Two', 'Three')
            class_list = star_rating_tag['class']
            # Find the rating word in the class list
            for cls in ['One', 'Two', 'Three', 'Four', 'Five']:
                if cls in class_list:
                    book_data['review_rating'] = cls
                    break
            else:
                book_data['review_rating'] = 'Unknown'  # If no rating class found

        # Image URL in <div> with class 'item active'
        image_container = soup.find('div', class_='item active')
        if image_container:
            image_tag = image_container.find('img')
            if image_tag and 'src' in image_tag.attrs:
                # The 'src' attribute is relative this will convert to absolute path
                relative_path = image_tag['src']
                # Base URL for the site https://books.toscrape.com/
                base_site_url = url.split('/catalogue/')[0] + '/'
                # Remove the relative path components
                clean_relative_path = relative_path.replace('../../', '')
                book_data['image_url'] = base_site_url + clean_relative_path

        return book_data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during scraping: {e}")
        return None

def export_to_csv_simple(data, filename="book_details.csv"):
    """
    Exports a list of dictionaries (book data) to a CSV file.

    Args:
        data (list of dict): A list containing dictionaries, where each dictionary
                             represents one book's data.
        filename (str): The name of the CSV file to create or append to.
    """
    # Define the headers in the order requested for the CSV file
    csv_headers = [
        'product_page_url',
        'universal_product_code',
        'book_title',
        'price_including_tax',
        'price_excluding_tax',
        'quantity_available',
        'product_description',
        'category',
        'review_rating',
        'image_url'
    ]

    # Check if the file already exists. If not, or if it's empty, we need to write the header row.
    file_exists = os.path.exists(filename)
    # os.stat(filename).st_size == 0 checks if the file is empty
    write_header = not file_exists or os.stat(filename).st_size == 0

    try:
        # Open the CSV file in append mode ('a').
        # 'newline=''' prevents extra blank rows in the CSV.
        # 'encoding='utf-8''
        with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
            # Create a DictWriter object, which maps dictionaries to CSV rows
            writer = csv.DictWriter(csvfile, fieldnames=csv_headers)

            # Write the header row if it's a new file or an empty existing file
            if write_header:
                writer.writeheader()

            # Write each book's data row
            for row_data in data:
                writer.writerow(row_data)
        print(f"Data successfully exported to {filename}")
    except IOError as e:
        print(f"Error writing to CSV file {filename}: {e}")

def get_book_links_from_category_page(category_url):
    """
    Scrapes all individual book detail page links from a given category page.

    Args:
        category_url (str): The URL of the category page.

    Returns:
        list: A list of absolute URLs for each book on the page.
              Returns an empty list if no links are found or an error occurs.
    """
    book_links = []
    try:
        response = requests.get(category_url)
        response.raise_for_status()
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the main content section where books are listed
        # Books are typically within <article class="product_pod"> inside a <section>
        products_section = soup.find('section')
        if products_section:
            # Find all book containers (articles)
            book_containers = products_section.find_all('article', class_='product_pod')
            for container in book_containers:
                # Find the <a> tag that links to the book's detail page in the <h3> tag
                link_tag = container.find('h3').find('a')
                if link_tag and 'href' in link_tag.attrs:
                    relative_link = link_tag['href']
                    # Construct the absolute URL using urljoin
                    absolute_link = urljoin(category_url, relative_link)
                    book_links.append(absolute_link)
        return book_links

    except requests.exceptions.RequestException as e:
        print(f"Error fetching category page {category_url}: {e}")
        return []
    except Exception as e:
        print(f"An error occurred while getting book links: {e}")
        return []

# Single Book Code
# if __name__ == "__main__":
    # The URL of the book page we want to scrape
    #book_page_url = "https://books.toscrape.com/catalogue/soumission_998/index.html"

    #print(f"Attempting to scrape: {book_page_url}")
    # Call the scraping function
    #scraped_book_info = scrape_book_details_simple(book_page_url)

    #if scraped_book_info:
    #    print("\nSuccessfully scraped book details:")
    #    for key, value in scraped_book_info.items():
    #        print(f"  {key.replace('_', ' ').title()}: {value}")

        # Export the scraped data to a CSV file
        # The export_to_csv_simple function expects a list of dictionaries,
        # so we put our single book_data dictionary into a list.
        #export_to_csv_simple([scraped_book_info], "book_details.csv")
    #else:
    #    print("Failed to scrape book details. No data will be exported.")




# --- Main part of the script to run the scraping and export ---
if __name__ == "__main__":
    category_page_url = "https://books.toscrape.com/catalogue/category/books/travel_2/index.html"
    output_csv_filename = "travel_books_details.csv"

    print(f"Starting to scrape book links from category page: {category_page_url}")
    book_urls = get_book_links_from_category_page(category_page_url)

    if not book_urls:
        print("No book links found on the category page or an error occurred. Exiting.")
    else:
        print(f"Found {len(book_urls)} book links. Now scraping details for each...")
        all_scraped_books_data = []
        for i, book_url in enumerate(book_urls):
            print(f"Scraping book {i+1}/{len(book_urls)}: {book_url}")
            book_details = scrape_book_details_simple(book_url)
            if book_details:
                all_scraped_books_data.append(book_details)
            else:
                print(f"  Failed to scrape details for: {book_url}")

        if all_scraped_books_data:
            print(f"\nSuccessfully scraped details for {len(all_scraped_books_data)} books.")
            # Export all collected book data to a single CSV file
            export_to_csv_simple(all_scraped_books_data, output_csv_filename)
        else:
            print("No book details were successfully scraped. No CSV will be created.")


