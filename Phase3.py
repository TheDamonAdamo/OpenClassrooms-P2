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

def export_books_to_csv(data, category_name, base_filename="books_details.csv"):
    """
    Exports a list of dictionaries (book data) to a CSV file.

    Args:
        data (list of dict): A list containing dictionaries, where each dictionary
                             represents one book's data.
        category_name (str): The name of the category, used for the filename.
        base_filename (str): The base name for the CSV file (e.g., "books_details.csv").
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

    # Sanitize category name to create a valid filename
    # Replace spaces with underscores, remove characters that are not alphanumeric, underscore, or hyphen
    clean_category_name = re.sub(r'[^\w-]', '', category_name.replace(' ', '_'))
    filename = f"{clean_category_name}_{base_filename}"

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

def get_all_categories_with_links(main_url="https://books.toscrape.com/index.html"):
    """
    Scrapes all category names and their corresponding absolute links from the main page.

    Args:
        main_url (str): The URL of the main page (default is https://books.toscrape.com/index.html).

    Returns:
        list: A list of dictionaries, where each dictionary contains 'name'
              and 'url' for each scraped category.
              Returns an empty list if no categories are found or an error occurs.
    """
    categories = []
    try:
        response = requests.get(main_url)
        response.raise_for_status()
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        side_categories_div = soup.find('div', class_='side_categories')
        if side_categories_div:
            nav_list_ul = side_categories_div.find('ul', class_='nav nav-list')
            if nav_list_ul:
                nested_ul = nav_list_ul.find('ul') # This targets the ul with actual categories
                if nested_ul:
                    category_links = nested_ul.find_all('a')
                    for link_tag in category_links:
                        category_name = link_tag.get_text(strip=True)
                        relative_url = link_tag['href']
                        # Construct the absolute URL using urljoin
                        absolute_url = urljoin(main_url, relative_url)
                        categories.append({'name': category_name, 'url': absolute_url})
        return categories
    except requests.exceptions.RequestException as e:
        print(f"Error fetching categories from {main_url}: {e}")
        return []
    except Exception as e:
        print(f"An error occurred during category link scraping: {e}")
        return []

def get_all_book_links_in_category(category_base_url):
    """
    Scrapes all individual book detail page links from a given category,
    handling pagination.

    Args:
        category_base_url (str): The base URL of the category page (e.g., .../travel_2/index.html).

    Returns:
        list: A list of absolute URLs for each book found in the category.
    """
    all_book_links = []
    current_page_url = category_base_url
    page_num = 1

    while True:
        print(f"  Scraping book links from category page {page_num}: {current_page_url}")
        try:
            response = requests.get(current_page_url)
            response.raise_for_status()
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find the main content section where books are listed
            products_section = soup.find('section')
            if products_section:
                book_containers = products_section.find_all('article', class_='product_pod')
                for container in book_containers:
                    link_tag = container.find('h3').find('a')
                    if link_tag and 'href' in link_tag.attrs:
                        relative_link = link_tag['href']
                        # Book links are relative to the 'catalogue' directory, not the current page directly.
                        # urljoin handles this correctly by resolving against the base of the category URL.
                        absolute_link = urljoin(current_page_url, relative_link)
                        all_book_links.append(absolute_link)

            # Check for a "next" pagination link
            next_button = soup.find('li', class_='next')
            if next_button:
                next_page_relative_link = next_button.find('a')['href']
                # Construct the next page URL relative to the current category page URL
                current_page_url = urljoin(current_page_url, next_page_relative_link)
                page_num += 1
            else:
                # No "next" button found, so we're on the last page
                break

        except requests.exceptions.RequestException as e:
            print(f"  Error fetching category page {current_page_url}: {e}")
            break # Stop if we encounter an error
        except Exception as e:
            print(f"  An error occurred while getting book links from {current_page_url}: {e}")
            break # Stop if an unexpected error occurs

    return all_book_links

if __name__ == "__main__":
    main_site_url = "https://books.toscrape.com/index.html"
    total_books_scraped = 0

    print(f"--- Starting full site scrape from: {main_site_url} ---")

    # Step 1: Get all categories and their links
    print("\nStep 1: Scraping all categories and their links...")
    categories_with_links = get_all_categories_with_links(main_site_url)

    if not categories_with_links:
        print("No categories found. Exiting.")
    else:
        print(f"Found {len(categories_with_links)} categories.")
        # Step 2 & 3: Iterate through each category, get book links, and scrape details
        for i, category_info in enumerate(categories_with_links):
            category_name = category_info['name']
            category_url = category_info['url']
            print(f"\nProcessing category {i+1}/{len(categories_with_links)}: '{category_name}' ({category_url})")

            # List to hold books for the current category
            books_in_current_category = []

            book_urls_in_category = get_all_book_links_in_category(category_url)

            if not book_urls_in_category:
                print(f"  No books found in category '{category_name}'.")
            else:
                print(f"  Found {len(book_urls_in_category)} books in '{category_name}'. Scraping details...")
                for j, book_url in enumerate(book_urls_in_category):
                    # print(f"    Scraping book {j+1}/{len(book_urls_in_category)}: {book_url}")
                    book_details = scrape_book_details_simple(book_url)
                    if book_details:
                        books_in_current_category.append(book_details)
                        total_books_scraped += 1
                    else:
                        print(f"    Failed to scrape details for book: {book_url}")

            # Step 4: Export all collected data for the current category to its own CSV
            if books_in_current_category:
                print(f"  Successfully scraped details for {len(books_in_current_category)} books in '{category_name}'.")
                export_books_to_csv(books_in_current_category, category_name)
            else:
                print(f"  No book details were successfully scraped for category '{category_name}'. No CSV will be created for this category.")

        print(f"\n--- Full site scraping complete. Total books scraped across all categories: {total_books_scraped} ---")
