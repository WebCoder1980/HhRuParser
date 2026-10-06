import json
import time
import requests
import random
import sqlite3
from pathlib import Path


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


DB_PATH = Path("out3-vacancies.db")


def get_existing_vacancy_ids(conn: sqlite3.Connection) -> set:
    """Возвращает множество всех vacancy_id из БД."""
    cur = conn.execute("SELECT vacancy_id FROM vacancies")
    return {row[0] for row in cur.fetchall()}


def extract_vacancy_ids_from_response(data: dict) -> set:
    """Извлекает vacancy_id из ответа API."""
    ids = set()
    # Структура ответа: data может содержать вакансии в разных полях
    # Основные вакансии находятся в корне ответа или в items
    vacancies = []
    
    # Проверяем разные возможные структуры
    if "found" in data:
        total = data["found"]
    else:
        total = 0
    
    # Vacancies могут быть в разных местах в зависимости от структуры ответа HH API
    for key in ["items", "found", "hits"]:
        if key in data and isinstance(data[key], list):
            vacancies.extend(data[key])
            break
    else:
        # Если это список вакансий напрямую
        if isinstance(data, list):
            vacancies = data
    
    for v in vacancies:
        if isinstance(v, dict) and "vacancyId" in v:
            ids.add(v["vacancyId"])
        elif isinstance(v, dict) and "id" in v:
            ids.add(v["id"])
    
    # Также проверяем вложенные структуры
    if not ids and isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        if "vacancyId" in item:
                            ids.add(item["vacancyId"])
                        elif "id" in item:
                            ids.add(item["id"])
    
    return ids


def main():
    results = []
    page = 0

    session = requests.Session()

    session.headers.update({
        "User-Agent": "Mozilla/5.0"
    })
    
    # Подключаемся к БД для проверки существующих вакансий
    if not DB_PATH.exists():
        print(f"БД не найдена: {DB_PATH}")
        print("Сначала выполните to_sqlite.py для создания БД.")
        return 1
    
    conn = sqlite3.connect(str(DB_PATH))
    existing_ids = get_existing_vacancy_ids(conn)
    print(f"Загружено {len(existing_ids)} existing vacancy_id из БД")

    try:
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

            results.append({
                "page": page,
                "result": data,
            })
            
            # Извлекаем vacancy_id из текущей страницы
            page_ids = extract_vacancy_ids_from_response(data)
            
            if page_ids:
                # Проверяем, есть ли все вакансии этой страницы уже в БД
                all_existing = page_ids.issubset(existing_ids)
                print(f"  Вакансий на странице: {len(page_ids)}, из них в БД: {len(page_ids & existing_ids)}")
                
                if all_existing:
                    print(f"\nВсе {len(page_ids)} вакансий со страницы {page} уже есть в БД. Остановка.")
                    break
            else:
                # Если не смогли извлечь ID, проверяем found=0 или другую структуру
                # Если API возвращает пустой результат, останавливаемся
                found = data.get("found", 0)
                items = data.get("items", [])
                if found == 0 or (isinstance(items, list) and len(items) == 0):
                    print(f"\nНет вакансий на странице {page}. Остановка.")
                    break

            if page >= 19:
                print(f"\nДостигнут лимит страниц (19). Остановка.")
                break

            page += 1

            time.sleep(random.randint(3, 10))
    finally:
        conn.close()

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
