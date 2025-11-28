import json
import csv
import sys
import os
from pathlib import Path
from typing import List, Dict


class JsonToCsvConverter:
    def __init__(self, json_file: str = '../factories_with_prices.json',
                 csv_file: str = '../data/metal_prices_history.csv'):
        self.input_file = json_file
        self.output_file = csv_file
        self.fieldnames = ['company', 'product', 'date', 'price']

    def load_json(self) -> List[Dict]:
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except FileNotFoundError:
            return []
        except:
            return []

    def extract_price_rows(self, factory: Dict) -> List[Dict]:
        rows = []
        company_name = factory.get('name', 'Unknown')
        price_data = factory.get('price_data', {})

        if not price_data:
            return rows

        for product_name, product_info in price_data.items():
            price_history = product_info.get('price_history', [])

            if not price_history:
                continue

            for month_data in price_history:
                weekly_data = month_data.get('weekly_data', [])

                for point in weekly_data:
                    row = {
                        'company': company_name,
                        'product': product_name,
                        'date': point.get('date', ''),
                        'price': point.get('price', 0)
                    }
                    rows.append(row)

        return rows

    def convert_to_csv(self, data: List[Dict]):
        if not data:
            return

        all_rows = []
        for factory in data:
            rows = self.extract_price_rows(factory)
            all_rows.extend(rows)

        if not all_rows:
            return

        try:
            os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

            with open(self.output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
                writer.writeheader()

                sorted_rows = sorted(all_rows, key=lambda x: x['date'])
                writer.writerows(sorted_rows)

            print(f"CSV файл создан: {self.output_file}")

        except Exception as e:
            print(f"Ошибка записи: {e}")

    def validate_csv(self) -> bool:
        try:
            with open(self.output_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                row_count = sum(1 for _ in reader)
            print(f"CSV валидация: {row_count} строк")
            return True
        except:
            return False


def main():
    converter = JsonToCsvConverter()
    data = converter.load_json()
    converter.convert_to_csv(data)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()