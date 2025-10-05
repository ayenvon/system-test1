from utils.helper import  read_file_generator
import asyncio
from config import PROXY
from controller.dorker import dorker


async def run_checks(queries, proxy, max_concurrent: int = 500):
    sem = asyncio.Semaphore(max_concurrent)

    async with asyncio.TaskGroup() as tg:
        for query in queries: 
            async def wrapped_checker(query=query):
                async with sem:
                    await asyncio.shield(dorker(query, proxy))
            tg.create_task(wrapped_checker())

    print("✅ All checks finished!")

# Example usage
if __name__ == "__main__":
    file_path = input("Input file path: ").strip()
    dork_key = list(read_file_generator(file_path))
    print(f"dork_keys: {len(dork_key)}")

    asyncio.run(run_checks(dork_key, PROXY, max_concurrent=500))
