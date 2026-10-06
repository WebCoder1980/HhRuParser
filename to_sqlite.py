import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DDL = """
CREATE TABLE IF NOT EXISTS vacancies (
    vacancy_id              INTEGER PRIMARY KEY,
    name                    TEXT,
    company_name            TEXT,
    company_site_url        TEXT,
    publication_timestamp   INTEGER,
    publication_datetime    TEXT,
    address                 TEXT,
    snippet_req             TEXT,
    snippet_resp            TEXT,
    snippet_cond            TEXT,
    snippet_skill           TEXT,
    snippet_desc            TEXT,
    total_responses_count   INTEGER,
    saved_at                TEXT
);

CREATE INDEX IF NOT EXISTS idx_vacancies_company ON vacancies(company_name);
CREATE INDEX IF NOT EXISTS idx_vacancies_pub_ts  ON vacancies(publication_timestamp);
"""

INSERT_SQL = """
INSERT OR IGNORE INTO vacancies (
    vacancy_id, name, company_name, company_site_url,
    publication_timestamp, publication_datetime, address,
    snippet_req, snippet_resp, snippet_cond, snippet_skill, snippet_desc,
    total_responses_count, saved_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def flatten(vacancy: dict, saved_at: str) -> tuple:
    """Преобразует объект вакансии в кортеж значений для INSERT."""
    company = vacancy.get("company") or {}
    pub = vacancy.get("publicationTime") or {}
    addr = vacancy.get("address") or {}
    snip = vacancy.get("snippet") or {}

    return (
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
    )


def load_vacancies(json_path: Path) -> list:
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Ожидался JSON-массив вакансий в корне файла")
    return data


def main() -> int:
    json_path = Path("out2-vacancies.json")
    db_path = Path("out3-vacancies.db")

    if not json_path.is_file():
        print(f"Файл не найден: {json_path}")
        return 1

    vacancies = load_vacancies(json_path)
    print(f"Прочитано вакансий: {len(vacancies)}")

    saved_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executescript(DDL)
            
            inserted = 0
            skipped = 0
            for v in vacancies:
                try:
                    conn.execute(INSERT_SQL, flatten(v, saved_at))
                    inserted += 1
                except sqlite3.IntegrityError:
                    skipped += 1
            
            conn.commit()
            
            cur = conn.execute("SELECT COUNT(*) FROM vacancies")
            total_in_db = cur.fetchone()[0]
            print(f"Добавлено новых: {inserted}")
            print(f"Пропущено (дубликаты): {skipped}")
            print(f"Всего записей в БД: {total_in_db} -> {db_path}")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
