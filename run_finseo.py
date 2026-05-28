from datetime import datetime
from jinja2 import Template
import pandas as pd
import requests


def run_business_logic():
    print("Шаг 1: Прямой запрос полного JSON с серверов Мосбиржи...")

    # Чистый URL к ISS MOEX, который отдает ВСЕ существующие колонки без обрезания
    url = "https://moex.com"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    with requests.Session() as session:
        try:
            response = session.get(url, headers=headers, timeout=20)
            if response.status_code != 200:
                print(f"Биржа вернула статус-код: {response.status_code}")
                return
            raw_data = response.json()
        except Exception as e:
            print(f"Сетевой сбой: {e}")
            return

    print("Шаг 2: Сборка таблиц из сырого JSON-ответа...")

    # Извлекаем статические данные облигаций (securities)
    sec_cols = raw_data["securities"]["columns"]
    sec_rows = raw_data["securities"]["data"]
    df_sec = pd.DataFrame(sec_rows, columns=sec_cols)

    # Извлекаем рыночные данные доходностей (marketdata)
    md_cols = raw_data["marketdata"]["columns"]
    md_rows = raw_data["marketdata"]["data"]
    df_md = pd.DataFrame(md_rows, columns=md_cols)

    print("Шаг 3: Объединение и инженерный расчет метрик...")

    # Пересекаем таблицы по ID облигации (SECID)
    df = pd.merge(df_sec, df_md, on="SECID")

    # Удаляем строки без цены (LAST) или без доходности (YIELD)
    df = df.dropna(subset=["LAST", "YIELD"])

    # Принудительно переводим финансовые столбцы в числа
    df["LAST"] = pd.to_numeric(df["LAST"], errors="coerce")
    df["YIELD"] = pd.to_numeric(df["YIELD"], errors="coerce")
    df["COUPONVALUE"] = pd.to_numeric(df["COUPONVALUE"], errors="coerce")
    df["COUPONPERIOD"] = pd.to_numeric(df["COUPONPERIOD"], errors="coerce")

    # Чистим строки от мусора, если после конвертации появились NaN
    df = df.dropna(subset=["LAST", "YIELD", "COUPONVALUE", "COUPONPERIOD"])

    # Исключаем деление на ноль, если у каких-то бумаг период купона равен 0
    df = df[df["COUPONPERIOD"] > 0]

    # Считаем годовой купонный доход в рублях
    df["Kuponov_v_god"] = (365 / df["COUPONPERIOD"]).round().astype(int)
    df["Kupon_god"] = (df["COUPONVALUE"] * df["Kuponov_v_god"]).round(2)

    # Округляем цену и доходность до сотых долей
    df["LAST"] = df["LAST"].round(2)
    df["YIELD"] = df["YIELD"].round(2)

    # Сортировка: ОФЗ с максимальной доходностью к погашению (YTM) идет на первое место!
    df = df.sort_values(by="YIELD", ascending=False)

    # Маппинг имен колонок под переменные шаблона template.html
    df = df.rename(
        columns={
            "SECID": "Код",
            "SHORTNAME": "Название",
            "LAST": "Цена",
            "YIELD": "Доходность",
            "Kupon_god": "Купон_год",
        }
    )

    # Формируем список данных
    bonds_list = df.to_dict(orient="records")
    print(f"Успешно обработано и подготовлено {len(bonds_list)} бумаг ОФЗ.")

    print("Шаг 4: Генерация index.html...")
    current_date = datetime.now().strftime("%d.%m.%Y в %H:%M")

    with open("template.html", "r", encoding="utf-8") as f:
        template_html = f.read()

    template = Template(template_html)
    rendered_html = template.render(
        bonds=bonds_list, current_date=current_date
    )

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(rendered_html)

    print("Успех! Робот полностью обновил сайт.")


if __name__ == "__main__":
    run_business_logic()
