import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv('cfg.env')
BASE_URL = os.getenv('BASE_URL')


async def fetch(session, url):
    async with session.get(url) as r:
        return await r.text()


async def main():
    fabrics_urls = set()

    async with aiohttp.ClientSession() as session:
        # 1) Получаем главную страницу
        html = await fetch(session, BASE_URL)
        soup = BeautifulSoup(html, 'lxml')

        # 2) Список регионов
        regions = [
            BASE_URL + a['href']
            for a in soup.select('div.blocklist a')
        ]

        # 3) Загружаем ВСЕ регионы параллельно
        regions_html = await asyncio.gather(*[fetch(session, u) for u in regions])

        region_pages = []
        for html in regions_html:
            s = BeautifulSoup(html, 'lxml')
            article = s.find('article', class_='content')
            urls = {
                BASE_URL + a['href']
                for a in article.find_all('a')
            }
            region_pages.extend(urls)

        # 4) Отбираем URL, которые требуют доп. загрузки
        simple = {u for u in region_pages if 'predpriyatiya' not in u and 'about' not in u}
        nested = [u for u in region_pages if 'predpriyatiya' in u]

        fabrics_urls.update(simple)

        # 5) Грузим страницы предприятий параллельно
        nested_html = await asyncio.gather(*[fetch(session, u) for u in nested])

        for html in nested_html:
            s = BeautifulSoup(html, 'lxml')
            article = s.find('article', class_='content')
            if not article:
                continue

            zavodi = [
                         BASE_URL + a['href']
                         for span in article.select('span')
                         for a in [span.find('a')]
                         if a
                     ][:-2]

            fabrics_urls.update(zavodi)

        # 6) Сохраняем
        with open('url.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(fabrics_urls))


asyncio.run(main())
