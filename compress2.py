import json

with open('out-vacancies.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

result = []
for v in data:
    company = v.get('company') or {}
    address = v.get('address') or {}
    result.append({
        'vacancyId': v.get('vacancyId'),
        'name': v.get('name'),
        'company': {
            'name': company.get('name'),
            'companySiteUrl': company.get('companySiteUrl'),
        },
        'publicationTime': v.get('publicationTime'),
        'address': {
            'displayName': address.get('displayName'),
        },
        'snippet': v.get('snippet'),
        'totalResponsesCount': v.get('totalResponsesCount'),
    })

with open('out2-vacancies.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f'Готово: {len(result)} вакансий')
