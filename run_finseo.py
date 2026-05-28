from datetime import datetime
from jinja2 import Template
import pandas as pd
import requests


def run_business_logic():
    print("Шаг 1: Запрос данных ОФЗ из зеркала...")

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

    # Превращаем в Pandas
    df = pd.DataFrame(raw_bonds)

    print("Шаг 2: Адаптивная фильтрация ОФЗ по ключевому слову...")

    # Приводим все текстовые колонки к нижнему регистру для безопасного поиска
    df["name_lower"] = df["name"].astype(str).str.lower()

    # Фильтруем: берем только те строки, где в названии есть "офз"
    df_ofz = df[df["name_lower"].str.contains("офз", na=False)].copy()

    # Заменяем возможные пропуски в цене и доходности на нули, чтобы не падать
    df_ofz["yield"] = pd.to_numeric(df_ofz["yield"], errors="coerce").fillna(0)
    df_ofz["price"] = pd.to_numeric(df_ofz["price"], errors="coerce").fillna(0)

    # Сортируем по доходности к погашению (YTM) от максимума к минимуму
    df_ofz = df_ofz.sort_values(by="yield", ascending=False)

    # Формируем список данных для нашего шаблона template.html
    bonds_list = []
    for _, row in df_ofz.iterrows():
        # Расчет купона за год: если параметров нет, ставим 0
        coupon_value = row.get("coupon_value", 0)
        coupon_period = row.get("coupon_period", 182)

        if coupon_period > 0 and coupon_value > 0:
            coupon_year = round(coupon_value * (365 / coupon_period), 2)
        else:
            coupon_year = 0

        bonds_list.append(
            {
                "Код": row.get("secid", "-"),
                "Название": row.get("name", "-"),
                "Цена": round(row.get("price", 0), 2),
                "Доходность": round(row.get("yield", 0), 2),
                "Купон_год": coupon_year,
            }
        )

    print(f"Успешно обработано {len(bonds_list)} облигаций ОФЗ.")

    print("Шаг 3: Генерация index.html...")
    current_date = datetime.now().strftime("%d.%m.%Y в %H:%M")

    with open("template.html", "r", encoding="utf-8") as f:
        template_html = f.read()

    template = Template(template_html)
    rendered_html = template.render(
        bonds=bonds_list, current_date=current_date
    )

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(rendered_html)
    print("Успех! Файл index.html заполнен данными.")


if __name__ == "__main__":
    run_business_logic()
