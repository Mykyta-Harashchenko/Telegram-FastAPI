import requests
from bs4 import BeautifulSoup


def get_usd_exchange_rate() -> float:
    url = "https://api.privatbank.ua/p24api/pubinfo?json&exchange&coursid=5"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        for currency in data:
            if currency['ccy'] == 'USD':
                buy_rate = currency['buy']
                return float(buy_rate.replace(",", "."))
        raise ValueError("Курс USD не найден в ответе API")

    except Exception as e:
        print(f"Ошибка при получении курса USD: {e}")
        return 0.0