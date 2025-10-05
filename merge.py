from config import KEYWORDS_FILE, URLS_FILE, SHOPPING_DORK
from utils.helper import save_list_to_file
def merge_dorks():
    keywords = KEYWORDS_FILE
    dork_keys = URLS_FILE


    merged = []
    for dork in dork_keys:
        for keyword in keywords:
            merged.append(f'{dork} "{keyword}"')
    save_list_to_file(SHOPPING_DORK, merged)
    print(f"[+] Merged {len(merged)} dorks into {SHOPPING_DORK}")

merge_dorks()