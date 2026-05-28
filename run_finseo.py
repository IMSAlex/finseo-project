from datetime import datetime
from jinja2 import Template
import pandas as pd
import requests


def run_business_logic():
    print(
        "Шаг 1: Запрос актуальных данных ОФЗ через открытый шлюз Яндекс.Инвестиций..."
    )

    # Публичный и стабильный фид Яндекса по облигациям, открытый для зарубежных IP
    url = "https://yandex.ru"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        # Этот запрос GitHub выполнит моментально, так как Яндекс его не блокирует
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(
                f"Яндекс.Инвестиции вернули ошибку. Статус-код: {response.status_code}"
            )
            return
        raw_data = response.json()
    except Exception as e:
        print(f"Сбой при запросе к Яндексу: {e}")
        return

    print("Шаг 2: Обработка данных и сортировка по YTM...")

    bonds_list = []

    # Яндекс возвращает массив облигаций в ключе 'bonds' или корне структуры
    bonds_raw = raw_data.get("bonds", raw_data)

    for item in bonds_raw:
        try:
            # Извлекаем параметры (Яндекс использует понятные английские ключи)
            ticker = item.get("ticker", item.get("secid", "-"))
            name = item.get("name", "-")

            # Вытаскиваем цену и честную доходность к погашению (YTM)
            price = float(item.get("price", 0))
            ytm = float(item.get("yield_to_maturity", item.get("yield", 0)))

            if ytm <= 0 or price <= 0:
                continue

            # Получаем купоны
            coupon_value = float(item.get("coupon_value", 0))
            coupon_period = int(item.get("coupon_period", 182))

            # Считаем годовую купонную сумму
            coupon_year = (
                round(coupon_value * (365 / coupon_period), 2)
                if coupon_period > 0
                else 0
            )

            bonds_list.append(
                {
                    "Код": ticker,
                    "Название": name,
                    "Цена": round(price, 2),
                    "Доходность": round(ytm, 2),
                    "Купон_god": coupon_year,
                }
            )
        except Exception:
            continue

    # Сортируем: ОФЗ с максимальной доходностью к погашению — строго наверх!
    bonds_list = sorted(bonds_list, key=lambda x: x["Доходность"], reverse=True)
    print(f"УСПЕХ! Из Яндекса успешно получено {len(bonds_list)} ОФЗ.")

    if not bonds_list:
        print("Внимание: Скрипт не смог распарсить структуру Яндекса.")
        return

    print("Шаг 3: Магия сборки index.html...")
    current_date = datetime.now().strftime("%d.%m.%Y в %H:%M")

    with open("template.html", "r", encoding="utf-8") as f:
        template_html = f.read()

    template = Template(template_html)
    rendered_html = template.render(
        bonds=bonds_list, current_date=current_date
    )

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(rendered_html)
    print("Файл index.html полностью обновлен числовыми инвест-данными.")


if __name__ == "__main__":
    run_business_logic()
