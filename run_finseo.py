from datetime import datetime
import apimoex
from jinja2 import Template
import pandas as pd
import requests


def run_business_logic():
    print("Шаг 1: Запрос данных через apimoex...")

    with requests.Session() as session:
        try:
            # Скачиваем статику
            sec_data = apimoex.get_board_securities(
                session, board="TQOB", market="bonds", engine="stock"
            )
            df_sec = pd.DataFrame(sec_data)

            # Скачиваем динамику рынка (цена и доходность)
            md_data = apimoex.get_board_securities(
                session,
                board="TQOB",
                market="bonds",
                engine="stock",
                table="marketdata",
            )
            df_md = pd.DataFrame(md_data)
        except Exception as e:
            print(f"Ошибка сети: {e}")
            return

    if df_sec.empty or df_md.empty:
        print("Ошибка: Пустые данные.")
        return

    print("Шаг 2: Обработка и фильтрация...")
    df = pd.merge(df_sec, df_md, on="SECID")
    df = df.dropna(subset=["LAST", "YIELD"])

    df["LAST"] = pd.to_numeric(df["LAST"], errors="coerce")
    df["YIELD"] = pd.to_numeric(df["YIELD"], errors="coerce")
    df["COUPONVALUE"] = pd.to_numeric(df["COUPONVALUE"], errors="coerce")
    df["COUPONPERIOD"] = pd.to_numeric(df["COUPONPERIOD"], errors="coerce")
    df = df.dropna(subset=["LAST", "YIELD", "COUPONVALUE", "COUPONPERIOD"])

    df["Kuponov_v_god"] = (365 / df["COUPONPERIOD"]).round().astype(int)
    df["Kupon_god"] = (df["COUPONVALUE"] * df["Kuponov_v_god"]).round(2)
    df["LAST"] = df["LAST"].round(2)
    df["YIELD"] = df["YIELD"].round(2)

    df = df.sort_values(by="YIELD", ascending=False)
    df = df.rename(
        columns={
            "SECID": "Код",
            "SHORTNAME": "Название",
            "LAST": "Цена",
            "YIELD": "Доходность",
            "Kupon_god": "Купон_god",
        }
    )

    bonds_list = df.to_dict(orient="records")
    print(f"Обработано {len(bonds_list)} ОФЗ.")

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
    print("Успех! Локальный index.html готов.")


if __name__ == "__main__":
    run_business_logic()