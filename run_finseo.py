from datetime import datetime
from jinja2 import Template
import pandas as pd
import requests


def run_business_logic():
    print("Шаг 1: Запрос открытого финансового фида...")

    # Стабильный, открытый источник данных по облигациям РФ
    url = "https://rusetf.com"

    try:
        response = requests.get(url, timeout=20)
        if response.status_code != 200:
            print(f"Фид недоступен. Статус: {response.status_code}")
            return
        raw_data = response.json()
    except Exception as e:
        print(f"Сетевая ошибка: {e}")
        return

    print("Шаг 2: Фильтрация и расчет ОФЗ...")

    # Фид возвращает список словарей. Переводим в Pandas
    df = pd.DataFrame(raw_data)

    # Фильтруем только государственные облигации (ОФЗ)
    # Обычно в фидах они маркируются типом 'gov' или по слову в названии
    df["name_lower"] = df["name"].astype(str).str.lower()
    df_ofz = df[
        df["name_lower"].str.contains("офз", na=False)
        | (df["type"] == "gov")
    ].copy()

    # Дропаем строки, где нет ключевых параметров
    df_ofz = df_ofz.dropna(subset=["price", "yield_to_maturity"])

    bonds_list = []
    for _, row in df_ofz.iterrows():
        # Вытаскиваем значения, страхуясь от пустых ячеек
        ytm = float(row.get("yield_to_maturity", 0))
        price = float(row.get("price", 0))
        coupon_value = float(row.get("coupon_value", 0))
        coupon_period = int(row.get("coupon_period", 182))

        if ytm <= 0 or price <= 0:
            continue

        # Считаем годовой купон в рублях
        coupon_year = (
            round(coupon_value * (365 / coupon_period), 2)
            if coupon_period > 0
            else 0
        )

        bonds_list.append(
            {
                "Код": row.get("ticker", row.get("secid", "-")),
                "Название": row.get("name", "-"),
                "Цена": round(price, 2),
                "Доходность": round(ytm, 2),
                "Купон_god": coupon_year,
            }
        )

    # Сортируем: максимальная доходность YTM строго наверх
    bonds_list = sorted(bonds_list, key=lambda x: x["Доходность"], reverse=True)
    print(f"Успешно подготовлено {len(bonds_list)} ОФЗ для сайта.")

    if not bonds_list:
        print(
            "Внимание: список ОФЗ пуст. Проверьте структуру альтернативного источника."
        )
        return

    print("Шаг 3: Сборка index.html...")
    current_date = datetime.now().strftime("%d.%m.%Y в %H:%M")

    with open("template.html", "r", encoding="utf-8") as f:
        template_html = f.read()

    template = Template(template_html)
    rendered_html = template.render(
        bonds=bonds_list, current_date=current_date
    )

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(rendered_html)
    print("Успех! Файл index.html обновлен данными.")


if __name__ == "__main__":
    run_business_logic()
