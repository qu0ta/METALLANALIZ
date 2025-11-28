import json
import random
from datetime import datetime, timedelta
import sys
import os
from typing import List, Dict


class PriceHistoryGenerator:
    def __init__(self, json_file: str = '../factories_data.json'):
        self.input_file = json_file
        self.output_file = '../factories_with_prices.json'
        self.data = self.load_json()

        self.base_prices = {
            'Метизы': {'unit': 'кг', 'price': 95},
            'Гвозди': {'unit': 'кг', 'price': 95},
            'Болты': {'unit': 'шт', 'price': 280},
            'Саморезы': {'unit': 'кг', 'price': 350},
            'Сетки металлические': {'unit': 'м²', 'price': 115},
            'Пружины': {'unit': 'шт', 'price': 75},
            'Рессоры': {'unit': 'комплект', 'price': 18000},
            'Детали тракторные': {'unit': 'шт', 'price': 2500},
            'Кузнечные изделия': {'unit': 'кг', 'price': 150},
            'Конструкции': {'unit': 'т', 'price': 65000},
            'Корпуса': {'unit': 'шт', 'price': 5000},
            'Обработка металла': {'unit': 'кг', 'price': 120}
        }

    def load_json(self) -> list:
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except FileNotFoundError:
            return []
        except:
            return []

    def generate_price_history(self, base_price: float, months: int = 12) -> list:
        history = []
        current_price = base_price
        start_date = datetime.now() - timedelta(days=365)

        for month in range(months):
            month_date = start_date + timedelta(days=30 * month)
            trend_factor = 1 + (month * 0.003)

            month_num = month_date.month
            if month_num in [3, 4, 5]:
                season_factor = 1.08
            elif month_num in [9, 10]:
                season_factor = 1.05
            elif month_num in [12, 1, 2]:
                season_factor = 0.95
            else:
                season_factor = 1.0

            vol_factor = random.uniform(0.85, 1.15)
            month_price = base_price * trend_factor * season_factor * vol_factor
            month_price = round(month_price, 2)

            weekly_prices = []
            for week in range(4):
                week_vol = random.uniform(0.95, 1.05)
                week_price = round(month_price * week_vol, 2)
                weekly_prices.append({
                    'date': (month_date + timedelta(days=7 * week)).strftime('%Y-%m-%d'),
                    'price': week_price
                })

            history.append({
                'month': month_date.strftime('%Y-%m'),
                'avg_price': month_price,
                'weekly_data': weekly_prices
            })

        return history

    def process_factory(self, factory: dict) -> dict:
        products = factory.get('products', ['Обработка металла'])
        price_data = {}

        for product_name in products:
            product_name = product_name.strip()
            base_info = self.base_prices.get(product_name)

            if not base_info:
                for key in self.base_prices.keys():
                    if key.lower() in product_name.lower() or product_name.lower() in key.lower():
                        base_info = self.base_prices[key]
                        break

            if not base_info:
                base_info = self.base_prices['Обработка металла']

            history = self.generate_price_history(base_info['price'])

            price_data[product_name] = {
                'unit': base_info['unit'],
                'base_price': base_info['price'],
                'price_history': history,
                'current_price': history[-1]['avg_price'],
                'price_change_12m': round(
                    ((history[-1]['avg_price'] - history[0]['avg_price']) / history[0]['avg_price']) * 100, 1
                )
            }

        factory['price_data'] = price_data
        return factory

    def generate_all_prices(self):
        if not self.data:
            return

        factories_with_prices = []
        for factory in self.data:
            processed_factory = self.process_factory(factory)
            factories_with_prices.append(processed_factory)

        try:
            os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(factories_with_prices, f, ensure_ascii=False, indent=2)

            total_products = sum(len(f.get('price_data', {})) for f in factories_with_prices)
            print(f"Обработано {total_products} продуктов по {len(factories_with_prices)} заводам")

        except Exception as e:
            print(f"Ошибка сохранения: {e}")


def main():
    generator = PriceHistoryGenerator()
    generator.generate_all_prices()


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
