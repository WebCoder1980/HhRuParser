import json
import time
import requests
import random
import sqlite3
from datetime import datetime, timezone
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


def insert_vacancy_into_db(conn: sqlite3.Connection, vacancy: dict, saved_at: str) -> bool:
    """Вставляет вакансию в БД. Возвращает True если вставлена, False если пропущена."""
    company = vacancy.get("company") or {}
    pub = vacancy.get("publicationTime") or {}
    addr = vacancy.get("address") or {}
    snip = vacancy.get("snippet") or {}
    
    try:
        conn.execute("""
            INSERT OR IGNORE INTO vacancies (
                vacancy_id, name, company_name, company_site_url,
                publication_timestamp, publication_datetime, address,
                snippet_req, snippet_resp, snippet_cond, snippet_skill, snippet_desc,
                total_responses_count, saved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vacancy.get("vacancyId"),
            vacancy.get("name"),
            company.get("name"),
            company.get("companySiteUrl"),
            pub.get("@timestamp"),
            pub.get("$"),
            addr.get("displayName"),
            snip.get("req"),
            snip.get("resp"),
            snip.get("cond"),
            snip.get("skill"),
            snip.get("desc"),
            vacancy.get("totalResponsesCount"),
            saved_at,
        ))
        return True
    except sqlite3.IntegrityError:
        return False


def extract_vacancy_ids_from_response(data: dict) -> set:
    """Извлекает vacancy_id из ответа HH API.
    
    Структура ответа HH API:
    data["result"]["vacancySearchResult"]["vacancies"]
    """
    ids = set()
    
    # Основная структура HH API
    try:
        vacancies = data["result"]["vacancySearchResult"]["vacancies"]
        if isinstance(vacancies, list):
            for v in vacancies:
                if isinstance(v, dict) and "vacancyId" in v:
                    ids.add(v["vacancyId"])
            return ids
    except (KeyError, TypeError):
        pass
    
    # Fallback: рекурсивный поиск vacancyId во всех вложенных структурах
    def search_ids(obj):
        if isinstance(obj, dict):
            if "vacancyId" in obj:
                ids.add(obj["vacancyId"])
            for v in obj.values():
                search_ids(v)
        elif isinstance(obj, list):
            for item in obj:
                search_ids(item)
    
    search_ids(data)
    return ids


NEW_VACANCIES_OUTPUT_FILE = "new-vacancies.json"


def extract_vacancies_from_response(data: dict) -> list:
    """Извлекает список вакансий из ответа HH API."""
    vacancies = []
    try:
        vacancies = data["result"]["vacancySearchResult"]["vacancies"]
        if isinstance(vacancies, list):
            return vacancies
    except (KeyError, TypeError):
        pass
    return []


def main():
    results = []
    new_vacancies = []
    page = 0
    total_new = 0
    total_saved = 0

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
    print(f"Загружено {len(existing_ids)} vacancy_id из БД")
    
    saved_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

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
            
            # Извлекаем вакансии и их ID из текущей страницы
            page_vacancies = extract_vacancies_from_response(data)
            page_ids = set()
            page_new_vacancies = []
            
            for v in page_vacancies:
                if isinstance(v, dict) and "vacancyId" in v:
                    vid = v["vacancyId"]
                    page_ids.add(vid)
                    if vid not in existing_ids:
                        page_new_vacancies.append(v)
            
            if page_ids:
                new_on_page = len(page_ids - existing_ids)
                print(f"  Вакансий на странице: {len(page_ids)}, новых: {new_on_page}, из них в БД: {len(page_ids & existing_ids)}")
                
                # Сохраняем новые вакансии в БД
                if page_new_vacancies:
                    for v in page_new_vacancies:
                        if insert_vacancy_into_db(conn, v, saved_at):
                            total_new += 1
                            existing_ids.add(v["vacancyId"])
                        total_saved += 1
                    conn.commit()
                    print(f"  → Добавлено в БД: {len(page_new_vacancies)}")
                
                # Проверяем, есть ли все вакансии этой страницы уже в БД
                if not page_new_vacancies:
                    print(f"\nВсе {len(page_ids)} вакансий со страницы {page} уже есть в БД. Остановка.")
                    break
            else:
                # Если не смогли извлечь ID, проверяем found=0 или другую структуру
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

    # Сохраняем новые вакансии в отдельный JSON
    if new_vacancies:
        with open(NEW_VACANCIES_OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(
                new_vacancies,
                f,
                ensure_ascii=False,
                indent=4,
            )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=4,
        )

    print(f"\nГотово!")
    print(f"Страниц обработано: {len(results)}")
    print(f"Новых вакансий добавлено в БД: {total_new}")
    print(f"Файл: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
