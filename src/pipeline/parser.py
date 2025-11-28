import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
import sys
import os
from typing import List, Dict, Optional


class AsyncMetalParser:
    def __init__(self, max_concurrent: int = 2, delay: float = 2.0):
        self.max_concurrent = max_concurrent
        self.delay = delay
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        self.output_file = '../factories_data.json'

    async def fetch_page(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        async with self.semaphore:
            try:
                async with session.get(url, headers=self.headers, timeout=30, ssl=True) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        return None
            except:
                return None
            finally:
                await asyncio.sleep(self.delay)

    def parse_factory_page(self, html: str, url: str) -> Optional[Dict]:
        try:
            soup = BeautifulSoup(html, 'html.parser')
            title = soup.find('h1')
            factory_name = title.get_text(strip=True) if title else "Название не найдено"

            address = ""
            for p in soup.find_all('p'):
                text = p.get_text(strip=True)
                if 'Россия' in text and len(text) > 20:
                    address = text
                    break

            phones = []
            for phone in soup.find_all('a', href=lambda x: x and x.startswith('tel:')):
                phone_text = phone.get_text(strip=True)
                if phone_text:
                    phones.append(phone_text)

            return {
                'url': url,
                'name': factory_name,
                'address': address,
                'phones': phones,
                'status': 'success'
            }
        except:
            return None

    async def process_url(self, session: aiohttp.ClientSession, url: str) -> Optional[Dict]:
        html = await self.fetch_page(session, url)
        if html:
            return self.parse_factory_page(html, url)
        return None

    async def parse_all(self, urls: List[str]) -> List[Dict]:
        async with aiohttp.ClientSession() as session:
            tasks = [self.process_url(session, url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            valid_results = []
            for result in results:
                if isinstance(result, Exception):
                    continue
                elif result is not None:
                    valid_results.append(result)

            return valid_results

    def save_to_json(self, data: List[Dict]):
        try:
            os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Файл создан: {os.path.abspath(self.output_file)}")
        except Exception as e:
            print(f"Ошибка сохранения: {e}")


async def main():
    factory_urls = [
        "https://ibprom.ru/volgogradskiy-zavod-traktornyh-deta",
        "https://ibprom.ru/belzan",
        "https://ibprom.ru/chelyabinskiy-kuznechno-pressovyy-z",
        "https://ibprom.ru/beloreckiy-zavod-pruzhin-i-ressor",
        "https://ibprom.ru/66-metalloobrabatyvayuschiy-zavod",
        "https://ibprom.ru/lepse",
        "https://ibprom.ru/zavod-selmash",
        "https://ibprom.ru/liskimontazhkonstruktsiya",
        "https://ibprom.ru/zavod-korpusov"
    ]

    parser = AsyncMetalParser(max_concurrent=2, delay=2.0)
    results = await parser.parse_all(factory_urls)
    parser.save_to_json(results)

    success_count = sum(1 for r in results if r.get('status') == 'success')

    print("\n" + "=" * 60)
    print(f"Всего заводов: {len(factory_urls)}")
    print(f"Успешно обработано: {success_count}")
    print(f"Время выполнения: {time.time() - time.time():.2f} секунд")
    print("=" * 60)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    asyncio.run(main())