import asyncio
import re
from curl_cffi.requests import exceptions as ccx
from utils.helper import filter_urls, faker
import urllib.parse
from curl_cffi.requests import AsyncSession

# global lock for safe file writing
file_lock = asyncio.Lock()


def return_msg(query: str, results: list, message: str):
    return {
        "query": query,
        "results": results,
        "message": message
    }


async def append_to_file(filename: str, urls: list[str]):
    """Safely append URLs to a file without race conditions."""
    async with file_lock:
        with open(filename, "a", encoding="utf-8") as f:
            for url in urls:
                f.write(url + "\n")


async def dorker(query: str, proxy: str, pages: int = 5, max_retries: int = 5):
    proxy_body = {
        "http": proxy,
        "https": proxy
    }
    encoded_dork_key = urllib.parse.quote(query)
    all_results = []

    async with AsyncSession() as session:
        session.proxies = proxy_body
        session.impersonate = "chrome"

        for page in range(pages):
            start = page * 100
            retries = 0

            while True:
                try:
                    data = faker("US")
                    ua = data["User Agent"]

                    headers = {
                        "User-Agent": ua, 
                        "Accept": "*/*",
                        "Accept-Language": "en-US,en;q=0.5",
                        "Referer": "https://www.google.com/",
                        "Alt-Used": "www.google.com",
                        "DNT": "1",
                        "Connection": "keep-alive",
                    }

                    url = (
                        f"https://www.google.com/search?q={encoded_dork_key}"
                        f"&num=100&start={start}&sourceid=chrome&ie=UTF-8"
                    )

                    response = await session.get(url, headers=headers, timeout=20)

                    if "did not match any documents." in response.text:
                        # print(
                        # f"No relevant results for query: {query} (page {page+1})")
                        break
                    elif "Our systems have detected unusual traffic" in response.text:
                        if retries >= max_retries:
                            # print("Recaptcha triggered - Exiting...")
                            return return_msg(query, all_results, f"Total {len(all_results)} URLs found across {pages} pages")
                        retries += 1
                        continue

                    urls = re.findall(
                        r'https?://[^\s"<>,\'\\\)\(]+', response.text)
                    unique_urls = filter_urls(urls)
                    

                    if not unique_urls:
                        if retries >= max_retries:
                            # print(f"No results on query {query} page {page+1}")
                            break
                        retries += 1
                        continue

                    all_results.extend(unique_urls)
                    print(
                        f"Query: {query} | Page {page+1} | {len(unique_urls)} URLs")
                    break  # ✅ done with this page, go next

                except (ccx.ProxyError, ccx.ConnectionError, ccx.ConnectTimeout, ccx.Timeout, asyncio.TimeoutError) as e:
                    if retries >= max_retries:
                        # print(
                        #     f"Request failed after {max_retries} attempts: {str(e)}")
                        return return_msg(query, all_results, f"Total {len(all_results)} URLs found across {pages} pages")
                    retries += 1
                    continue
                except Exception as e:
                    if retries >= max_retries:
                        # print(f"Unexpected error: {str(e)}")
                        return return_msg(query, all_results, f"Total {len(all_results)} URLs found across {pages} pages")
                    retries += 1
                    continue

    # write results
    await append_to_file("data/dork_results.txt", all_results)
    return return_msg(query, all_results, f"Total {len(all_results)} URLs found across {pages} pages")
