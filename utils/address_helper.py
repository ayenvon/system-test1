import data.address.handlers as address_handler
import json
import random


# Preload JSON files once at module load
with open("data/user.json", "r", encoding="utf-8") as f:
    USERS = json.load(f)

with open("data/ua.json", "r", encoding="utf-8") as f:
    USER_AGENTS = json.load(f)

ADDRESS_DATA = {}
for country in ["us", "gb", "au", "ca"]:
    with open(f"data/address/{country}.json", "r", encoding="utf-8") as f:
        ADDRESS_DATA[country] = json.load(f)

COUNTRY_HANDLERS = {
    "us": address_handler.get_us_address,
    "gb": address_handler.get_gb_address,
    "au": address_handler.get_au_address,
    "ca": address_handler.get_ca_address
}


def get_address(country="us"):
    country_lower = country.lower()

    random_user = random.choice(USERS)

    user_info = {
        "first_name": random_user['user']['first_name'],
        "last_name": random_user['user']['last_name'],
        "email": random_user['user']['email'],
        "phone": random_user['user']['phone'],
        "user_agent": random.choice(USER_AGENTS)["ua"]
    }

    address_handler = COUNTRY_HANDLERS.get(country_lower)
    address_json = {"address": address_handler(ADDRESS_DATA[country_lower])}

    return {"user": user_info, **address_json}
