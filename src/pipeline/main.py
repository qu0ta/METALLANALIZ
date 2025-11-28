import sys
import asyncio
import os
import time


class PipelineOrchestrator:
    def __init__(self):
        self.results = {
            'parser': {
                'success': False,
                'file': '../factories_data.json',
                'records': 0
            },
            'price_generator': {
                'success': False,
                'file': '../factories_with_prices.json',
                'records': 0
            },
            'csv_converter': {
                'success': False,
                'file': '../data/metal_prices_history.csv',
                'records': 0
            },
        }
        self.start_time = None

    def check_dependencies(self) -> bool:
        required_files = [
            '../pipeline/parser.py',
            '../pipeline/price_generator.py',
            '../pipeline/json_to_csv.py'
        ]

        for file in required_files:
            if not os.path.exists(file):
                print(f"Не найден файл {file}")
                return False

        test_file = '../write_test.tmp'
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        except:
            return False

        return True

    async def run_parser(self) -> bool:
        sys.path.append('..')
        sys.path.append('../pipeline')
        from parser import main as parser_main

        await parser_main()

        if os.path.exists(self.results['parser']['file']):
            with open(self.results['parser']['file'], 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.results['parser']['records'] = len(data)
                self.results['parser']['success'] = True
                return True
        else:
            return False

    def run_price_generator(self) -> bool:
        sys.path.append('..')
        sys.path.append('../pipeline')
        from price_generator import PriceHistoryGenerator

        if not os.path.exists(self.results['parser']['file']):
            return False

        generator = PriceHistoryGenerator()
        generator.generate_all_prices()

        if os.path.exists(self.results['price_generator']['file']):
            with open(self.results['price_generator']['file'], 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.results['price_generator']['records'] = len(data)
                self.results['price_generator']['success'] = True
                return True
        else:
            return False

    def run_csv_converter(self) -> bool:
        sys.path.append('..')
        sys.path.append('../pipeline')
        from json_to_csv import JsonToCsvConverter

        if not os.path.exists(self.results['price_generator']['file']):
            return False

        converter = JsonToCsvConverter()
        data = converter.load_json()
        converter.convert_to_csv(data)

        if os.path.exists(self.results['csv_converter']['file']):
            with open(self.results['csv_converter']['file'], 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                self.results['csv_converter']['records'] = len(rows)
                self.results['csv_converter']['success'] = True
                return True
        else:
            return False

    def print_final_report(self):
        total_time = time.time() - self.start_time

        print("\nСТАТУС ПАЙПЛАЙНА:")
        for step, result in self.results.items():
            status = "УСПЕШНО" if result['success'] else "ОШИБКА"
            print(f"  {step.upper():<20} {status} | {result['records']} записей -> {result['file']}")

        print(f"\nВремя выполнения: {total_time:.2f} секунд")

        final_file = self.results['csv_converter']['file']
        if os.path.exists(final_file):
            size = os.path.getsize(final_file)
            print(f"Финальный файл: {final_file} ({size} байт)")
            print(f"Абсолютный путь: {os.path.abspath(final_file)}")
        else:
            print("Финальный файл не создан!")

    async def run_full_pipeline(self):
        self.start_time = time.time()
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

        if not self.check_dependencies():
            sys.exit(1)

        if not await self.run_parser():
            sys.exit(1)

        if not self.run_price_generator():
            sys.exit(1)

        if not self.run_csv_converter():
            sys.exit(1)

        self.print_final_report()


def main():
    orchestrator = PipelineOrchestrator()
    asyncio.run(orchestrator.run_full_pipeline())


if __name__ == "__main__":
    main()