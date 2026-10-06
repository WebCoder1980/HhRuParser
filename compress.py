import json
from pathlib import Path

INPUT_FILE = "vacancies.json"
OUTPUT_FILE = "out-vacancies.json"


def extract_vacancies(input_path: str, output_path: str) -> None:
    input_file = Path(input_path)

    print(f"Читаю: {input_file} ({input_file.stat().st_size / 1024 / 1024:.2f} MB)")

    with input_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Если корень — список объектов (с page/result), собираем vacancies из всех
    if isinstance(data, list):
        vacancies = []
        for item in data:
            try:
                vacancies.extend(
                    item["result"]["vacancySearchResult"]["vacancies"]
                )
            except (KeyError, TypeError):
                continue
    else:
        vacancies = data["result"]["vacancySearchResult"]["vacancies"]

    print(f"Найдено вакансий: {len(vacancies)}")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(vacancies, f, ensure_ascii=False, indent=2)

    print(f"Сохранено: {output_path} "
          f"({Path(output_path).stat().st_size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    extract_vacancies(INPUT_FILE, OUTPUT_FILE)
