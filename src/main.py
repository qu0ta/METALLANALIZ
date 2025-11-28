import sys
import asyncio
import os
import json
import csv

# Устанавливаем рабочую директорию на директорию скрипта
os.chdir(os.path.dirname(os.path.abspath(__file__)))

sys.path.append(os.path.join(os.path.dirname(__file__), 'pipeline'))


class PipelineOrchestrator:
    def __init__(self):
        self.start_time = time.time()

    async def run_full_pipeline(self):
        print("=" * 60)
        print("🚀 ЗАПУСК ПОЛНОГО ПАЙПЛАЙНА")
        print("=" * 60)

        # Шаг 1: Парсинг
        print("\n[ШАГ 1] Запуск парсера...")
        try:
            from parser import main as parser_main
            await parser_main()

            if os.path.exists('factories_data.json'):
                with open('factories_data.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"✅ Парсинг завершен: {len(data)} заводов")
            else:
                print("❌ factories_data.json не создан")
                return False
        except Exception as e:
            print(f"❌ Ошибка парсинга: {e}")
            return False

        # Шаг 2: Генерация цен
        print("\n[ШАГ 2] Генерация цен...")
        try:
            from price_generator import PriceHistoryGenerator
            generator = PriceHistoryGenerator()
            generator.generate_all_prices()

            if os.path.exists('factories_with_prices.json'):
                with open('factories_with_prices.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"✅ Генерация цен завершена: {len(data)} заводов")
            else:
                print("❌ factories_with_prices.json не создан")
                return False
        except Exception as e:
            print(f"❌ Ошибка генерации цен: {e}")
            return False

        # Шаг 3: Конвертация в CSV
        print("\n[ШАГ 3] Конвертация в CSV...")
        try:
            from json_to_csv import JsonToCsvConverter
            converter = JsonToCsvConverter()
            data = converter.load_json()
            converter.convert_to_csv(data)

            if os.path.exists('data/metal_prices_history.csv'):
                with open('data/metal_prices_history.csv', 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                print(f"✅ CSV создан: {len(rows)} ценовых точек")

                print("\nПервые 5 строк CSV:")
                for i, row in enumerate(rows[:5], 1):
                    print(f"{i}. {row}")
            else:
                print("❌ metal_prices_history.csv не создан")
                return False
        except Exception as e:
            print(f"❌ Ошибка конвертации: {e}")
            return False

        print("\n" + "=" * 60)
        print("✅ ПАЙПЛАЙН УСПЕШНО ЗАВЕРШЕН")
        print(f"⏱️ Время: {time.time() - self.start_time:.2f} секунд")
        print("=" * 60)
        return True


if __name__ == "__main__":
    import time

    orchestrator = PipelineOrchestrator()
    success = asyncio.run(orchestrator.run_full_pipeline())

    if not success:
        sys.exit(1)