#!/usr/bin/env python3
"""
Конвертирует out2-vacancies.json в SQLite БД (одна таблица vacancies).

"""

import json
import sqlite3
import sys
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
    total_responses_count   INTEGER
);

CREATE INDEX IF NOT EXISTS idx_vacancies_company ON vacancies(company_name);
CREATE INDEX IF NOT EXISTS idx_vacancies_pub_ts  ON vacancies(publication_timestamp);
"""

INSERT_SQL = """
INSERT OR REPLACE INTO vacancies (
    vacancy_id, name, company_name, company_site_url,
    publication_timestamp, publication_datetime, address,
    snippet_req, snippet_resp, snippet_cond, snippet_skill, snippet_desc,
    total_responses_count
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def flatten(vacancy: dict) -> tuple:
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

    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executescript(DDL)
            conn.executemany(INSERT_SQL, (flatten(v) for v in vacancies))
        cur = conn.execute("SELECT COUNT(*) FROM vacancies")
        print(f"Записано в БД: {cur.fetchone()[0]} строк -> {db_path}")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
