from typing import List, Dict

# Читаем файл один раз при импорте модуля (кэшируем в памяти)
try:
    with open('BS_ignore_list.txt', 'r', encoding='utf-8') as f:
        IGNORE_SITES = {line.strip() for line in f if line.strip()}
except FileNotFoundError:
    IGNORE_SITES = set()

def enrichment(data: List[Dict]) -> List[Dict]:
    """Обогащает данные, используя быстрый поиск по множеству."""
    for item in data:
        if item.get('hostname') in IGNORE_SITES:
            item['vendor'] = 'bulat'
    return data

if __name__ == "__main__":
    data = [{'hostname': 'NS2444', 'vendor': None}]
    print(enrichment(data))
