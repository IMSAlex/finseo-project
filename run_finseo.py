import requests
import pandas as pd
from jinja2 import Template
from datetime import datetime

def run_business_logic():
    print("Шаг 1: Запрос данных ОФЗ из открытого источника...")
    
    # Используем стабильное, открытое API для ОФЗ (альтернативный фид без капчи)
    url = "https://githubusercontent.com"
    
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            print("Зеркало временно недоступно.")
            return
        raw_bonds = response.json()
    except Exception as e:
        print(f"Ошибка получения данных: {e}")
        return

    print("Шаг 2: Фильтрация только ОФЗ...")
    # Превращаем в Pandas
    df = pd.DataFrame(raw_bonds)
    
    # Фильтруем только государственные облигации (ОФЗ)
    df = df[df['type'] == 'ofz']
    
    # Удаляем строки без доходности и цены
    df = df.dropna(subset=['yield', 'price'])
    
    # Сортируем по доходности к погашению (YTM) от максимума к минимуму
    df = df.sort_values(by='yield', ascending=False)
    
    # Форматируем поля для нашего template.html
    bonds_list = []
    for _, row in df.iterrows():
        bonds_list.append({
            'Код': row.get('secid', '-'),
            'Название': row.get('name', '-'),
            'Цена': round(row.get('price', 0), 2),
            'Доходность': round(row.get('yield', 0), 2),
            'Купон_год': round(row.get('coupon_value', 0) * (365 / row.get('coupon_period', 182)), 2)
        })
        
    print(f"Успешно обработано {len(bonds_list)} облигаций ОФЗ.")

    print("Шаг 3: Генерация index.html...")
    current_date = datetime.now().strftime("%d.%m.%Y в %H:%M")

    with open("template.html", "r", encoding="utf-8") as f:
        template_html = f.read()

    template = Template(template_html)
    rendered_html = template.render(bonds=bonds_list, current_date=current_date)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(rendered_html)
    print("Успех! Файл index.html успешно обновлен.")

if __name__ == "__main__":
    run_business_logic()
