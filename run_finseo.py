from datetime import datetime
import apimoex
from jinja2 import Template
import pandas as pd
import requests


def run_business_logic():
    print("Шаг 1: Запрос точных данных через apimoex...")

    with requests.Session() as session:
        try:
            print("Скачиваем справочник облигаций...")
            sec_data = apimoex.get_board_securities(
                session, board="TQOB", market="bonds", engine="stock"
            )
            df_sec = pd.DataFrame(sec_data)

            print("Скачиваем результаты торгов с явным указанием колонок...")
            # ЯВНО указываем columns, чтобы apimoex не вырезал цену и доходность!
            md_data = apimoex.get_board_securities(
                session,
                board="TQOB",
                market="bonds",
                engine="stock",
                table="marketdata",
                columns=("SECID", "LAST", "YIELD"),
            )
            df_md = pd.DataFrame(md_data)
        except Exception as e:
            print(f"Ошибка сети при работе с API: {e}")
            return

    if df_sec.empty or df_md.empty:
        print("Ошибка: Биржа вернула пустые массивы.")
        return

    print("Шаг 2: Обработка, объединение и фильтрация...")

    # Проверим, что нужные колонки на месте
    if "SECID" not in df_sec.columns or "SECID" not in df_md.columns:
        print("Ошибка структуры данных: отсутствует ключ SECID.")
        return

    # Объединяем статику и динамику
    df = pd.merge(df_sec, df_md, on="SECID")

    # Удаляем пустые строки, по которым сегодня не было сделок
    df = df.dropna(subset=["LAST", "YIELD"])

    # Приводим к числовым типам
    df["LAST"] = pd.to_numeric(df["LAST"], errors="coerce")
    df["YIELD"] = pd.to_numeric(df["YIELD"], errors="coerce")
    df["COUPONVALUE"] = pd.to_numeric(df["COUPONVALUE"], errors="coerce")
    df["COUPONPERIOD"] = pd.to_numeric(df["COUPONPERIOD"], errors="coerce")

    # Зачищаем NaN после изменения типов
    df = df.dropna(subset=["LAST", "YIELD", "COUPONVALUE", "COUPONPERIOD"])

    # Считаем годовой купон
    df["Kuponov_v_god"] = (365 / df["COUPONPERIOD"]).round().astype(int)
    df["Kupon_god"] = (df["COUPONVALUE"] * df["Kuponov_v_god"]).round(2)

    # Округляем
    df["LAST"] = df["LAST"].round(2)
    df["YIELD"] = df["YIELD"].round(2)

    # Сортируем: максимальная доходность к погашению (YTM) строго наверх!
    df = df.sort_values(by="YIELD", ascending=False)

    # Переименовываем под переменные в template.html
    df = df.rename(
        columns={
            "SECID": "Код",
            "SHORTNAME": "Название",
            "LAST": "Цена",
            "YIELD": "Доходность",
            "Kupon_god": "Купон_год",
        }
    )

    bonds_list = df.to_dict(orient="records")
    print(f"Успешно обработано {len(bonds_list)} ОФЗ.")

    print("Шаг 3: Магия сборки index.html...")
    current_date = datetime.now().strftime("%d.%m.%Y в %H:%M")

    try:
        with open("template.html", "r", encoding="utf-8") as f:
            template_html = f.read()
    except FileNotFoundError:
        print("Ошибка: Рядом не найден template.html!")
        return

    template = Template(template_html)
    rendered_html = template.render(
        bonds=bonds_list, current_date=current_date
    )

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(rendered_html)
    print("Успех! Файл index.html обновлен числовыми данными.")


if __name__ == "__main__":
    run_business_logic()
