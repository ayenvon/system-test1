from faker import Faker
import random

def get_us_address(random_information):
    randomize = random.choice(random_information)
    return {
        "street_address": randomize['street'],
        "city": randomize['city'],
        "state": randomize['state'],
        "region_code": randomize['state_code'],
        "postal_code": randomize['postcode'],
        "country": "US"
    }

def get_gb_address(random_information):
    fake = Faker(f"en_GB")
    item = random.choice(random_information)
    postal_code, city = item[0], item[1]  
    return {
        "street_address": fake.street_address(),
        "city": city,
        "postal_code": postal_code.split("\t")[0],
        "faker_postal_code": fake.postcode(),
        "country": "GB"
    }

def get_au_address(random_information):
    randomize = random.choice(random_information)['address']
    return {
        "street_address": randomize['street_address'],
        "city": randomize['city'],
        "state": randomize['state'],
        "region_code": randomize['region_code'],
        "postal_code": randomize['postal_code'],
        "country": "AU"
    }

def get_ca_address(random_information):
    fake = Faker(f"en_CA")
    item = random.choice(random_information)
    postal_code, city, region_code = item[0], item[1], item[2] 
    return {
        "street_address": fake.street_address(),
        "city": city,
        "state": region_code,
        "postal_code": postal_code.split("\t")[0],
        "country": "CA"
    }