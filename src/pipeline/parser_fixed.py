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
    def __init__(self, max_concurrent: int = 5, delay: float = 1.0):
        self.max_concurrent = max_concurrent
        self.delay = delay
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        self.output_file = 'factories_data.json'

    async def fetch_page(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        async with self.semaphore:
            try:
                print(f"🔍 Загружаю: {url}")
                async with session.get(url, headers=self.headers, timeout=30, ssl=False) as response:
                    if response.status == 200:
                        html = await response.text()
                        print(f"✅ Успешно: {url}")
                        return html
                    else:
                        print(f"❌ Ошибка {response.status}: {url}")
                        return None
            except Exception as e:
                print(f"🚨 Исключение: {url} - {e}")
                return None
            finally:
                await asyncio.sleep(self.delay)

    def parse_factory_page(self, html: str, url: str) -> Optional[Dict]:
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Ищем название в заголовке
            title = soup.find('h1')
            if not title:
                title = soup.find('title')
            
            factory_name = title.get_text(strip=True) if title else f"Завод {url.split('/')[-1]}"
            
            # Улучшенный поиск продуктов
            products = self._extract_products(soup, factory_name, url)
            
            # Базовая информация
            address = self._extract_address(soup)
            phones = self._extract_phones(soup)
            
            return {
                'url': url,
                'name': factory_name,
                'address': address,
                'phones': phones,
                'products': products,
                'status': 'success'
            }
        except Exception as e:
            print(f"⚠️ Ошибка парсинга {url}: {e}")
            return {
                'url': url,
                'name': f"Завод {url.split('/')[-1]}",
                'address': '',
                'phones': [],
                'products': ['Металлопродукция'],
                'status': 'error'
            }

    def _extract_products(self, soup: BeautifulSoup, factory_name: str, url: str) -> List[str]:
        products = []
        
        # Ключевые слова для определения продукции
        product_keywords = {
            'метиз': 'Метизы',
            'гвозд': 'Гвозди',
            'болт': 'Болты', 
            'шуруп': 'Шурупы',
            'саморез': 'Саморезы',
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
            'конструкц': 'Металлоконструкции',
            'прокат': 'Металлопрокат',
            'труб': 'Трубы',
            'кабел': 'Кабельная продукция',
            'инструмент': 'Инструменты',
            'арматур': 'Арматура',
            'лист': 'Листовой металл',
            'профил': 'Профильный металл',
            'провод': 'Провода',
            'цветн': 'Цветные металлы',
            'алюмин': 'Алюминиевые изделия',
            'мед': 'Медные изделия',
            'стал': 'Стальные изделия'
        }
        
        # Ищем в тексте страницы
        page_text = soup.get_text().lower()
        
        for keyword, product_name in product_keywords.items():
            if keyword in page_text or keyword in factory_name.lower():
                products.append(product_name)
        
        # Если ничего не нашли, определяем по URL
        if not products:
            url_lower = url.lower()
            if 'trub' in url_lower:
                products.append('Трубы')
            elif 'kabel' in url_lower:
                products.append('Кабельная продукция')
            elif 'instrument' in url_lower:
                products.append('Инструменты')
            elif 'prokat' in url_lower:
                products.append('Металлопрокат')
            elif 'pruzhin' in url_lower:
                products.append('Пружины')
            elif 'konstrukts' in url_lower:
                products.append('Металлоконструкции')
            else:
                products.append('Металлоизделия')
        
        return list(set(products))[:3]  # Максимум 3 продукта

    def _extract_address(self, soup: BeautifulSoup) -> str:
        # Ищем адрес в различных тегах
        for tag in soup.find_all(['p', 'div', 'span']):
            text = tag.get_text(strip=True)
            if any(keyword in text.lower() for keyword in ['россия', 'ул.', 'улица', 'г.', 'город']):
                if len(text) > 10 and len(text) < 200:
                    return text
        return "Адрес не указан"

    def _extract_phones(self, soup: BeautifulSoup) -> List[str]:
        phones = []
        phone_pattern = r'\+7\s*\(\d{3}\)\s*\d{3}[\s-]*\d{2}[\s-]*\d{2}'
        
        for text in soup.stripped_strings:
            matches = re.findall(phone_pattern, text)
            phones.extend(matches)
            
        return list(set(phones))[:2]  # Максимум 2 телефона

    async def process_url(self, session: aiohttp.ClientSession, url: str) -> Optional[Dict]:
        html = await self.fetch_page(session, url)
        if html:
            return self.parse_factory_page(html, url)
        return None

    async def parse_all(self, urls: List[str]) -> List[Dict]:
        print(f"🎯 Начинаю парсинг {len(urls)} компаний...")
        
        async with aiohttp.ClientSession() as session:
            tasks = [self.process_url(session, url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            valid_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"❌ Ошибка в задаче {i}: {result}")
                    continue
                elif result is not None:
                    valid_results.append(result)
                else:
                    # Создаем запись даже для неудачных URL
                    valid_results.append({
                        'url': urls[i],
                        'name': f"Завод {urls[i].split('/')[-1]}",
                        'address': 'Не удалось загрузить данные',
                        'phones': [],
                        'products': ['Металлопродукция'],
                        'status': 'failed'
                    })

            return valid_results

    def save_to_json(self, data: List[Dict]):
        try:
            os.makedirs(os.path.dirname(self.output_file) or '.', exist_ok=True)
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ Файл создан: {os.path.abspath(self.output_file)} ({len(data)} записей)")
            
            # Статистика
            success_count = sum(1 for item in data if item.get('status') == 'success')
            print(f"📊 Статистика: {success_count} успешных, {len(data) - success_count} с ошибками")
            
            if data:
                example = data[0]
                print(f"📌 Пример: {example['name']} -> Продукты: {example.get('products', [])}")
                
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
        "https://ibprom.ru/zavod-korpusov",
        "https://ibprom.ru/chelyabinskiy-zavod-litoy-ostat",
        "https://ibprom.ru/kamensk-uralskiy-zavod-po-obrabotke-tsvetnyh-metallov",
        "https://ibprom.ru/kirovskiy-zavod-po-obrabotke-tsvetnyh-metallov", 
        "https://ibprom.ru/krasnoyarskiy-zavod-tsvetnyh-metallov",
        "https://ibprom.ru/litsey-tsvetnyh-metallov",
        "https://ibprom.ru/balashikhinskiy-metalloobrabatyvayuschiy-zavod",
        "https://ibprom.ru/vladimirskiy-zavod-metalloizdeliy",
        "https://ibprom.ru/voronezhskiy-metalloobrabatyvayuschiy-zavod",
        "https://ibprom.ru/ekaterinburgskiy-metalloobrabatyvayuschiy-zavod",
        "https://ibprom.ru/izhevskiy-metalloobrabatyvayuschiy-zavod",
        "https://ibprom.ru/kazan-metalloobrabatyvayuschiy-zavod"
    ]

    parser = AsyncMetalParser(max_concurrent=5, delay=1.0)
    results = await parser.parse_all(factory_urls)
    parser.save_to_json(results)


if __name__ == "__main__":
    asyncio.run(main())