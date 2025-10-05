import urllib.parse
import html
import random
import re
from curl_cffi.requests import Response
from typing import Any
from faker import Faker
EXCLUDED_URLS = ["/search", "google", "facebook", "gcash", "stackoverflow", "magento", "quora", "wordpress", "forum", "usersinsights", "gstatic", "schema", ".w3.", "support", "reason8", "showponycreative", "doubleclick", "wp-content", ".wp.", "helpdesk", "wpmet", "blog", "themeim", "thatware", "8theme", "businessbloomer", "seedprod", "generatepress", "flyingpixel", "woocommerce", "blocks.", "productcategory.net", "help.", "wooextend", "bigcommerce",
                 "/documentation/", "/docs.", "/doc/", "/community/", "woolentor", "binarycarpenter", "/simpledonation.com", "/secure.simpledonation.com", "www.simpledonation.com", "/articles/", "linkedin", ".pdf", "reddit", "squarespace", "mastercard", "totallymoney", "amazon", "merriam-webster", "dictionary", "youtube", "instagram", "vocabulary", "thesaurus", "ytimg", "lookaside", "reversedrecords", "apple.", "wikipedia", "www.paypal.com", "dribbble.com", "chegg.com", "tiktok.com", "x.com"]


def get_base_url(url):
    parsed_url = urllib.parse.urlparse(url)
    return f"{parsed_url.scheme}://{parsed_url.netloc}"


def filter_urls(urls):
    unique_urls = []
    clean_urls = []

    base_urls = set()
    for url in urls:
        decoded_url = urllib.parse.unquote(html.unescape(url))
        if not any(excluded_url in decoded_url for excluded_url in EXCLUDED_URLS):
            base_url = get_base_url(decoded_url)
            if base_url not in base_urls:
                base_urls.add(base_url)
                unique_urls.append(decoded_url)

    for sites in unique_urls:
        from urllib.parse import urlparse, urlunparse
        parsed_url = urlparse(sites)
        if parsed_url.query:
            cleaned_url = urlunparse(parsed_url._replace(query=''))
        else:
            path = parsed_url.path.split('&')[0]
            cleaned_url = urlunparse(parsed_url._replace(path=path))
        clean_urls.append(cleaned_url)

    return clean_urls


def faker(country):
    fake = Faker(f'en_{country}')
    # print(fake)
    if 'US' in country:
        state = fake.country()
    elif 'AU' in country:
        state = fake.state()
    else:
        state = fake.county()
    # Generate fake personal data
    fname = fake.first_name()
    lname = fake.last_name()
    street = fake.street_address()
    city = fake.city()
    postcode = fake.postcode()
    phone = fake.phone_number()
    email = f'artpogisobrasobra{random.randint(00000, 99999)}@gmail.com'
    ua = fake.user_agent()
    webkit = ''.join(random.choice('0123456789') for _ in range(28))

    # Return the generated personal data as a dictionary
    return {
        "First Name": fname,
        "Last Name": lname,
        "Street": street,
        "City": city,
        "State": state,
        "Post Code": postcode,
        "Phone Number": phone,
        "Email Address": email,
        "User Agent": ua,
        "Webkit": webkit
    }


def read_file_generator(filename):
    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                yield stripped


def save_list_to_file(filename, items):
    with open(filename, "w", encoding="utf-8") as f:
        for item in items:
            f.write(item.strip() + "\n")


def split_card_details(card_details):

    # Use regex to split by multiple delimiters
    parts = re.split(r'[|:;/\\]', card_details)

    # Ensure there are exactly 4 parts
    if len(parts) != 4:
        raise ValueError(
            "Input must have exactly 4 parts separated by |, :, ;, /, or \\")

    cc, mm, yy_or_yyyy, cvv = parts

    # Determine the full year (yyyy) and last two digits (yy)
    if len(yy_or_yyyy) == 2:
        yyyy = f"20{yy_or_yyyy}"  # Assume year is in the 2000s
        yy = yy_or_yyyy
    elif len(yy_or_yyyy) == 4:
        yyyy = yy_or_yyyy
        yy = yy_or_yyyy[-2:]
    else:
        raise ValueError("Year must be either 2 or 4 digits long.")

    # Handle month (mm and m)
    mm = mm.zfill(2)  # Ensure month is two digits
    m = int(mm)  # Remove leading zero if any

    card_details = f"{cc}|{mm}|{yyyy}|{cvv}"
    # Return the values in the desired format, including original input
    return card_details, cc, mm, str(m), yyyy, yy, cvv


def safe_json(resp: Response) -> Any | None:
    try:
        return resp.json()
    except Exception:
        return None
