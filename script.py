import json
import time
import requests
import random


BASE_URL = "https://novosibirsk.hh.ru/shards/vacancy/search"

PARAMS = {
    "area": 4,
    "work_format": "ON_SITE",
    "enable_snippets": "true",
    "order_by": "publication_time",
    "search_field": [
        "name",
        "company_name",
        "description",
    ],
    "professional_role": [
        "83", "121", "12", "13", "20", "25", "41", "55", "98", "103", 
        "139", "156", "160", "165", "73", "96", "164", "104", "112", 
        "113", "148", "114", "124", "126", "116", "120", "84", "187", 
        "88", "110", "159", "39", "67", "81", "10", "150", "155"
    ],
    "items_on_page": 100,
}

OUTPUT_FILE = "vacancies.json"


def main():
    results = []
    page = 0

    session = requests.Session()

    # При необходимости можно добавить User-Agent
    session.headers.update({
        "User-Agent": "Mozilla/5.0"
    })

    while True:
        params = {
            **PARAMS,
            "page": page,
        }

        print(f"Получаю страницу {page}...")

        response = session.get(
            BASE_URL,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        # Сохраняем результат целиком
        results.append({
            "page": page,
            "result": data,
        })

        # Смотрим, есть ли вакансии в ответе.
        # В зависимости от структуры HH здесь может понадобиться
        # изменить название поля.
        if page == 19:
            break

        page += 1

        # Небольшая пауза между запросами
        time.sleep(random.randint(3, 10))

    # Записываем всё одним JSON-массивом
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=4,
        )

    print(f"\nГотово!")
    print(f"Страниц сохранено: {len(results)}")
    print(f"Файл: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
