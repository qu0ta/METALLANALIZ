import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
import sys
import os
import time
import re
from typing import List, Dict, Optional


class AsyncMetalParser:
    def __init__(self, max_concurrent: int = 1, delay: float = 3.0):
        self.max_concurrent = max_concurrent
        self.delay = delay
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        self.output_file = 'factories_data.json'

    async def fetch_page(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        async with self.semaphore:
            try:
                async with session.get(url, headers=self.headers, timeout=30, ssl=False) as response:
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
            soup = BeautifulSoup(html, 'lxml')
            title = soup.find('h1')
            factory_name = title.get_text(strip=True) if title else "Название не найдено"

            address = ""
            for p in soup.find_all('p'):
                text = p.get_text(strip=True)
                if 'Россия' in text and len(text) > 20:
                    address = text
                    break

            phones = []
            phone_pattern = r'\+7\s*\(\d{3,4}\)\s*\d{2,3}[\s-]*\d{2}[\s-]*\d{2,3}'
            for text in soup.stripped_strings:
                matches = re.findall(phone_pattern, text)
                phones.extend(matches)


            products = []


            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                desc = meta_desc.get('content', '').lower()


                patterns = {
                    'метизы': 'Метизы',
                    'гвозди': 'Гвозди',
                    'болты': 'Болты',
                    'шурупы': 'Шурупы',
                    'саморезы': 'Саморезы',
                    'сетк': 'Сетки металлические',
                    'пружин': 'Пружины',
                    'рессор': 'Рессоры',
                    'корпус': 'Корпуса',
                    'трактор': 'Детали тракторные',
                    'сельхоз': 'Детали сельхозмашин',
                    'кузнеч': 'Кузнечные изделия',
                    'поковк': 'Поковки',
                    'штамп': 'Штамповки',
                    'пресс': 'Прессовые изделия',
                    'конструкц': 'Конструкции',
                }

                for pattern, product_name in patterns.items():
                    if pattern in desc:
                        products.append(product_name)


            if not products:
                if 'метиз' in factory_name.lower():
                    products.append('Метизы')
                elif 'сетк' in factory_name.lower():
                    products.append('Сетки металлические')
                elif 'пружин' in factory_name.lower():
                    products.append('Пружины')
                elif 'рессор' in factory_name.lower():
                    products.append('Рессоры')
                elif 'корпус' in factory_name.lower():
                    products.append('Корпуса')
                elif 'трактор' in factory_name.lower():
                    products.append('Детали тракторные')
                elif 'сельмаш' in factory_name.lower():
                    products.append('Детали сельхозмашин')
                elif 'кузнеч' in factory_name.lower() or 'кпз' in factory_name.lower():
                    products.append('Кузнечные изделия')
                elif 'конструкц' in factory_name.lower():
                    products.append('Конструкции')
                else:
                    products.append('Обработка металла')


            products = list(set(products))

            return {
                'url': url,
                'name': factory_name,
                'address': address,
                'phones': list(set(phones)),
                'products': products,
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
            os.makedirs(os.path.dirname(self.output_file) or '.', exist_ok=True)
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ Файл создан: {os.path.abspath(self.output_file)} ({len(data)} записей)")
            # Выводим пример записи с продуктами для проверки
            if data:
                print(f"📌 Пример: {data[0]['name']} -> Продукты: {data[0].get('products', [])}")
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")


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

    parser = AsyncMetalParser(max_concurrent=16, delay=0.5)
    results = await parser.parse_all(factory_urls)
    parser.save_to_json(results)


if __name__ == "__main__":
    import time

    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    asyncio.run(main())